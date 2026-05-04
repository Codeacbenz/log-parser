import csv
import json
import tempfile
import unittest
from pathlib import Path

from ingestion import iter_record_batches
from loader import save_to_csv
from transformation import OUTPUT_COLUMNS, handle_missing_values, transform_all
from validator import validate_all


REAL_DUMP_PATH = Path("crown_interactive_january_logs.json")
B2_FIELDS = [
    "amount",
    "confirmationTime",
    "customerAddress",
    "customerMeterNumber",
    "debtAmount",
    "initiationTime",
    "status",
    "units",
    "unitsType",
    "value",
    "vat",
]

SOAP_RESPONSE = (
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
    "<soap:Body>"
    '<ns2:getOrderDetailsV2Response xmlns:ns2="http://soap.convergenceondemand.net/TMP/">'
    "<response>"
    "<desc>Request successful</desc>"
    "<retn>0</retn>"
    "<orderDetails>"
    "<amount>1000.0</amount>"
    "<confirmationTime>2025-12-30T21:51:58+01:00</confirmationTime>"
    "<customerAddress>HSE 27 GOLD ZONE</customerAddress>"
    "<customerMeterNumber>0159007338464</customerMeterNumber>"
    "<debtAmount>0.0</debtAmount>"
    "<initiationTime>2025-12-30T21:51:57+01:00</initiationTime>"
    "<status>CONFIRMED</status>"
    "<tokenData>"
    "<stdToken>"
    "<amount>1000.0</amount>"
    "<units>14.7</units>"
    "<unitsType>kWh</unitsType>"
    "<value>28722156647658477929</value>"
    "</stdToken>"
    "</tokenData>"
    "<vat>69.77</vat>"
    "</orderDetails>"
    "</response>"
    "</ns2:getOrderDetailsV2Response>"
    "</soap:Body>"
    "</soap:Envelope>"
)


class PipelineSmokeTest(unittest.TestCase):
    def test_stream_transform_validate_and_write_csv(self):
        raw_records = [
            {
                "_id": {"$oid": "record-1"},
                "action": "requery",
                "success": True,
                "gateway": "CROWN INTERACTIVE",
                "ref": "4828940943932882000",
                "response": SOAP_RESPONSE,
                "service": "ABUJA",
                "time": 549,
                "created": {"$date": "2026-01-01T07:40:32.899Z"},
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "dump.json"
            output_path = Path(tmp_dir) / "output.csv"
            input_path.write_text(json.dumps(raw_records, indent=2), encoding="utf-8")

            batches = list(iter_record_batches(input_path, batch_size=1))
            rows = transform_all(batches[0])
            good_rows, bad_rows = validate_all(rows)
            save_to_csv(good_rows, output_path)

            self.assertEqual(len(batches), 1)
            self.assertEqual(list(rows[0].keys()), OUTPUT_COLUMNS)
            self.assertEqual(len(good_rows), 1)
            self.assertEqual(bad_rows, [])
            self.assertEqual(rows[0]["amount"], 1000.0)
            self.assertEqual(rows[0]["success"], True)
            self.assertEqual(rows[0]["created"], "2026-01-01T07:40:32.899000Z")
            self.assertEqual(rows[0]["confirmationTime"], "2025-12-30T20:51:58Z")
            self.assertEqual(rows[0]["value"], "28722156647658477929")

            with output_path.open(newline="", encoding="utf-8") as f:
                saved_rows = list(csv.DictReader(f))

            self.assertEqual(saved_rows[0]["id"], "record-1")
            self.assertEqual(saved_rows[0]["units"], "14.7")

    def test_real_dump_sample_contains_parsed_b2_fields(self):
        if not REAL_DUMP_PATH.exists():
            self.skipTest(f"{REAL_DUMP_PATH} is not available")

        rows = transform_all(next(iter_record_batches(REAL_DUMP_PATH, batch_size=20)))
        rows_with_b2_data = [
            row
            for row in rows
            if row.get("amount") is not None
        ]

        self.assertGreater(len(rows_with_b2_data), 0)
        self.assertEqual(rows_with_b2_data[0]["response"], "Request successful")
        self.assertIsInstance(rows_with_b2_data[0]["amount"], float)
        self.assertIsInstance(rows_with_b2_data[0]["success"], bool)
        self.assertEqual(rows_with_b2_data[0]["status"], "CONFIRMED")
        self.assertEqual(rows_with_b2_data[0]["unitsType"], "kWh")

    def test_handle_missing_values_normalizes_null_like_values(self):
        row = {
            "id": " record-1 ",
            "success": None,
            "amount": "",
            "status": "null",
            "unitsType": " N/A ",
        }

        cleaned = handle_missing_values(row)

        self.assertEqual(cleaned["id"], "record-1")
        self.assertEqual(cleaned["success"], False)
        self.assertIsNone(cleaned["amount"])
        self.assertEqual(cleaned["status"], "UNKNOWN")
        self.assertEqual(cleaned["unitsType"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

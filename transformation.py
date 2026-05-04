from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import config


OUTPUT_COLUMNS = [
    "id",
    "action",
    "success",
    "gateway",
    "ref",
    "service",
    "time",
    "created",
    "response",
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

NUMERIC_FIELDS = {"amount", "debtAmount", "units", "vat"}
TIMESTAMP_FIELDS = {"created", "confirmationTime", "initiationTime"}
TEXT_FIELDS = {
    "action",
    "gateway",
    "ref",
    "service",
    "response",
    "customerAddress",
    "customerMeterNumber",
    "status",
    "unitsType",
    "value",
}


def transform_all(records):
    clean_rows = []

    for record in records:
        try:
            row = {
                "id": _mongo_value(record.get("_id"), "$oid"),
                "action": _clean_string(record.get("action")),
                "success": _to_bool(record.get("success")),
                "gateway": _clean_string(record.get("gateway")),
                "ref": _clean_string(record.get("ref")),
                "service": _clean_string(record.get("service")),
                "time": _to_int(record.get("time")),
                "created": _to_timestamp(_mongo_value(record.get("created"), "$date")),
                "response": None,
                "amount": None,
                "confirmationTime": None,
                "customerAddress": None,
                "customerMeterNumber": None,
                "debtAmount": None,
                "initiationTime": None,
                "status": None,
                "units": None,
                "unitsType": None,
                "value": None,
                "vat": None,
            }

            row.update(_parse_response_xml(record.get("response")))

            for field in NUMERIC_FIELDS:
                row[field] = _to_float(row.get(field))

            for field in TIMESTAMP_FIELDS:
                row[field] = _to_timestamp(row.get(field))

            row = handle_missing_values(row)
            clean_rows.append({column: row.get(column) for column in OUTPUT_COLUMNS})
        except Exception as error:
            print(f"Skipping a bad record during transformation: {error}")

    return clean_rows


def handle_missing_values(row):
    """Normalize missing/null-like values into SQL-friendly values."""
    cleaned = {}

    for key, value in row.items():
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in {"", "null", "none", "nan", "n/a"}:
                value = None

        cleaned[key] = value

    for field in TEXT_FIELDS:
        if field in cleaned and cleaned[field] is None:
            cleaned[field] = config.MISSING_TEXT_VALUE

    if cleaned.get("success") is None:
        cleaned["success"] = False

    return cleaned


def _parse_response_xml(xml_text):
    parsed = {}
    if not xml_text:
        return parsed

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        parsed["response"] = f"XML_PARSE_ERROR: {error}"
        return parsed

    parsed["response"] = _text(root, "desc") or _text(root, "response")
    parsed["amount"] = _text(root, "amount", parent="orderDetails")
    parsed["confirmationTime"] = _text(root, "confirmationTime")
    parsed["customerAddress"] = _text(root, "customerAddress")
    parsed["customerMeterNumber"] = _text(root, "customerMeterNumber")
    parsed["debtAmount"] = _text(root, "debtAmount")
    parsed["initiationTime"] = _text(root, "initiationTime")
    parsed["status"] = _text(root, "status")
    parsed["units"] = _text(root, "units")
    parsed["unitsType"] = _text(root, "unitsType")
    parsed["value"] = _std_token_value(root)
    parsed["vat"] = _text(root, "vat")

    return parsed


def _text(root, tag_name, parent=None):
    for element in root.iter():
        if _local_name(element.tag) != tag_name:
            continue

        if parent and not _has_parent_named(root, element, parent):
            continue

        value = element.text.strip() if element.text else None
        return value or None

    return None


def _std_token_value(root):
    for std_token in root.iter():
        if _local_name(std_token.tag) != "stdToken":
            continue

        for child in std_token:
            if _local_name(child.tag) == "value":
                value = child.text.strip() if child.text else None
                return value or None

    return _text(root, "value")


def _has_parent_named(root, target, parent_name):
    for parent in root.iter():
        if _local_name(parent.tag) != parent_name:
            continue
        if any(child is target for child in parent.iter()):
            return True
    return False


def _local_name(tag):
    return tag.split("}", 1)[-1]


def _mongo_value(value, key):
    if isinstance(value, dict):
        return value.get(key)
    return value


def _clean_string(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _to_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_timestamp(value):
    if value is None or value == "":
        return None

    value = str(value).strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

# transformation.py
import re
import json
from xml.etree import ElementTree as ET

def transform_all(records):
    clean_rows = []
    for record in records:
        try:
            # 1. Start with the basic info
            row = {
                "id": record.get("_id"),
                "ref": record.get("ref"),
                "service": record.get("service"),
                "amount": record.get("amount"),
                "success": record.get("success") == "true" or record.get("success") is True
            }

            # 2. Parse the XML inside the 'response' field
            xml_text = record.get("response", "")
            if xml_text:
                # Remove "soap:" prefixes to make parsing easy for beginners
                xml_text = re.sub(r'<\/?\w+:', '<', xml_text) 
                try:
                    root = ET.fromstring(xml_text)
                    # Look for specific fields inside the XML
                    row["status"] = root.find(".//status").text if root.find(".//status") is not None else None
                    row["vat"] = root.find(".//vat").text if root.find(".//vat") is not None else 0
                except:
                    pass # If XML is broken, just keep moving

            # 3. Convert numbers
            if row["amount"]: row["amount"] = float(row["amount"])
            if row["vat"]: row["vat"] = float(row["vat"])

            clean_rows.append(row)
        except Exception as e:
            print(f"Skipping a bad record: {e}")
            
    return clean_rows
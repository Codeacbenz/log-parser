import json

import config


def validate_all(rows):
    good_rows = []
    bad_rows = []
    seen_ids = set()

    for row in rows:
        errors = _validate_row(row, seen_ids)

        if errors:
            bad_row = dict(row)
            bad_row["_errors"] = errors
            bad_rows.append(bad_row)
        else:
            seen_ids.add(row["id"])
            good_rows.append(row)

    return good_rows, bad_rows


def write_failed_records(rows, file_path=config.FAILED_RECORDS_FILE):
    if not rows:
        return

    with open(file_path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def reset_failed_records(file_path=config.FAILED_RECORDS_FILE):
    with open(file_path, "w", encoding="utf-8"):
        pass


def _validate_row(row, seen_ids):
    errors = []

    if not row.get("id"):
        errors.append("missing id")
    elif row["id"] in seen_ids:
        errors.append("duplicate id in batch")

    for field in ("amount", "debtAmount", "units", "vat"):
        value = row.get(field)
        if value is not None and not isinstance(value, (int, float)):
            errors.append(f"{field} is not numeric")
        elif value is not None and value < 0:
            errors.append(f"{field} is negative")

    return errors

def validate_all(rows):
    good_rows = []
    bad_rows = []

    for row in rows:
        # Simple rules: Must have an ID and Amount must be positive
        if not row.get("id"):
            bad_rows.append(row)
        elif row.get("amount") is not None and row.get("amount") < 0:
            bad_rows.append(row)
        else:
            good_rows.append(row)

    return good_rows, bad_rows
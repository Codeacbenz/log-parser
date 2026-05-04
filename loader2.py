import csv


def save_to_csv(rows, file_path, append=False):
    if not rows:
        print("No data to save!")
        return

    headers = rows[0].keys()
    mode = "a" if append else "w"

    with open(file_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not append:
            writer.writeheader()
        writer.writerows(rows)

    action = "Appended" if append else "Saved"
    print(f"{action} {len(rows):,} rows to {file_path}")

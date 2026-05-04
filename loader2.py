# loader.py
import csv

def save_to_csv(rows, file_path):
    if not rows:
        print("No data to save!")
        return

    # Get the column headers from the first row
    headers = rows[0].keys()

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"💾 Saved to {file_path}")
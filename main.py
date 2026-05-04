# main.py
import config
from ingestion import load_records
from transformation import transform_all
from validator import validate_all
from loader2 import save_to_csv

def run_pipeline():
    print("--- Starting Pipeline ---")

    # Step 1: Get Data
    raw_data = load_records(config.SOURCE_FILE)
    if not raw_data: return

    # Step 2: Clean Data
    clean_data = transform_all(raw_data)

    # Step 3: Check Data
    good_data, bad_data = validate_all(clean_data)
    print(f"Validation: {len(good_data)} passed, {len(bad_data)} failed.")

    # Step 4: Save Data
    save_to_csv(good_data, config.OUTPUT_FILE)

    print("--- Pipeline Finished ---")

if __name__ == "__main__":
    run_pipeline()
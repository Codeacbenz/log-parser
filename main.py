import config
from ingestion import iter_record_batches
from transformation import transform_all
from validator import reset_failed_records, validate_all, write_failed_records
from loader import load_to_bigquery, save_to_csv


def run_pipeline():
    print("--- Starting Pipeline ---")
    reset_failed_records()

    total_good = 0
    total_bad = 0
    wrote_output = False

    # Process the JSON dump in batches so large files do not need to fit in memory.
    for raw_batch in iter_record_batches(config.SOURCE_FILE, config.CHUNK_SIZE):
        clean_data = transform_all(raw_batch)
        good_data, bad_data = validate_all(clean_data)

        total_good += len(good_data)
        total_bad += len(bad_data)

        write_failed_records(bad_data)

        if good_data:
            if config.LOAD_TARGET == "bigquery":
                load_to_bigquery(good_data)
            else:
                save_to_csv(good_data, config.OUTPUT_FILE, append=wrote_output)
            wrote_output = True

    if not wrote_output:
        print("No valid records found.")
        return

    print(f"Validation: {total_good:,} passed, {total_bad:,} failed.")
    print("--- Pipeline Finished ---")


if __name__ == "__main__":
    run_pipeline()

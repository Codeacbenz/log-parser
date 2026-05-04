import config
from ingestion import iter_record_batches
from transformation import transform_all
from validator import reset_failed_records, validate_all, write_failed_records
from loader import finish_bigquery_load, load_bigquery_rows, save_to_csv, start_bigquery_load


def run_pipeline():
    print("--- Starting Pipeline ---")
    reset_failed_records()

    total_good = 0
    total_bad = 0
    wrote_output = False
    bigquery_client = None
    bigquery_table_ref = None

    if config.LOAD_TARGET == "bigquery":
        bigquery_client, bigquery_table_ref = start_bigquery_load()

    # Process the JSON dump in batches so large files do not need to fit in memory.
    for batch_number, raw_batch in enumerate(iter_record_batches(config.SOURCE_FILE, config.CHUNK_SIZE), start=1):
        clean_data = transform_all(raw_batch)
        good_data, bad_data = validate_all(clean_data)

        total_good += len(good_data)
        total_bad += len(bad_data)

        write_failed_records(bad_data)

        if good_data:
            if config.LOAD_TARGET == "bigquery":
                load_bigquery_rows(bigquery_client, bigquery_table_ref, good_data, batch_number)
            else:
                save_to_csv(good_data, config.OUTPUT_FILE, append=wrote_output)
            wrote_output = True

    if not wrote_output:
        print("No valid records found.")
        return

    if config.LOAD_TARGET == "bigquery":
        finish_bigquery_load(bigquery_client)

    print(f"Validation: {total_good:,} passed, {total_bad:,} failed.")
    print("--- Pipeline Finished ---")


if __name__ == "__main__":
    run_pipeline()

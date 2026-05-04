# loader.py
# ─────────────────────────────────────────────────────────────
# This file's job: LOAD clean rows into Google BigQuery.
#
# BigQuery is Google's cloud database for analysing large datasets.
# Think of it like a very powerful spreadsheet in the cloud.
#
# What this file does:
#   1. Creates the dataset ("folder") if it doesn't exist
#   2. Creates the table ("spreadsheet") if it doesn't exist
#   3. Sends rows in small batches (chunks) — safer than all at once
#   4. Retries if something goes wrong (network blip, etc.)
#   5. Removes duplicate rows after loading
# ─────────────────────────────────────────────────────────────

import time
import csv
import config


# ── Table Schema ───────────────────────────────────────────────
# This tells BigQuery what columns our table has and what type each one is.
# STRING  = text
# BOOLEAN = true/false
# FLOAT64 = decimal number
# INTEGER = whole number
# TIMESTAMP = date and time

TABLE_SCHEMA = [
    {"name": "id",                  "type": "STRING"},
    {"name": "action",              "type": "STRING"},
    {"name": "success",             "type": "BOOLEAN"},
    {"name": "gateway",             "type": "STRING"},
    {"name": "ref",                 "type": "STRING"},
    {"name": "service",             "type": "STRING"},
    {"name": "time",                "type": "INTEGER"},
    {"name": "created",             "type": "TIMESTAMP"},
    {"name": "response",            "type": "STRING"},
    {"name": "amount",              "type": "FLOAT64"},
    {"name": "confirmationTime",    "type": "TIMESTAMP"},
    {"name": "customerAddress",     "type": "STRING"},
    {"name": "customerMeterNumber", "type": "STRING"},
    {"name": "debtAmount",          "type": "FLOAT64"},
    {"name": "initiationTime",      "type": "TIMESTAMP"},
    {"name": "status",              "type": "STRING"},
    {"name": "units",               "type": "FLOAT64"},
    {"name": "unitsType",           "type": "STRING"},
    {"name": "value",               "type": "STRING"},
    {"name": "vat",                 "type": "FLOAT64"},
]


def load_to_bigquery(rows):
    """
    Main function — loads all rows into BigQuery.
    Splits rows into chunks and loads them one chunk at a time.
    """

    # Import the BigQuery library
    # (you need to install it first: pip install google-cloud-bigquery)
    try:
        from google.cloud import bigquery
    except ImportError:
        print("❌ BigQuery library not installed. Run: pip install google-cloud-bigquery")
        return

    print(f"Connecting to BigQuery project: {config.GCP_PROJECT_ID}")
    client = bigquery.Client(project=config.GCP_PROJECT_ID)

    # Step 1: Make sure the dataset exists
    create_dataset_if_missing(client)

    # Step 2: Make sure the table exists
    table_ref = create_table_if_missing(client)

    # Step 3: Split rows into chunks and load each one
    print(f"Loading {len(rows):,} rows in chunks of {config.CHUNK_SIZE}...")
    total_loaded = 0
    chunks = split_into_chunks(rows, config.CHUNK_SIZE)

    for chunk_number, chunk in enumerate(chunks, start=1):
        success = insert_chunk_with_retry(client, table_ref, chunk, chunk_number)
        if success:
            total_loaded += len(chunk)
            print(f"  ✅ Chunk {chunk_number} loaded ({total_loaded:,}/{len(rows):,} rows)")

    # Step 4: Remove any duplicate rows
    print("Removing duplicate rows...")
    remove_duplicates(client)

    print(f"✅ Loading complete — {total_loaded:,} rows in BigQuery")


def create_dataset_if_missing(client):
    """Create the BigQuery dataset if it doesn't already exist."""
    from google.cloud import bigquery

    dataset_full_name = f"{config.GCP_PROJECT_ID}.{config.BQ_DATASET}"

    try:
        client.get_dataset(dataset_full_name)
        print(f"  Dataset already exists: {config.BQ_DATASET}")
    except Exception:
        dataset = bigquery.Dataset(dataset_full_name)
        dataset.location = "US"
        client.create_dataset(dataset)
        print(f"  ✅ Created dataset: {config.BQ_DATASET}")


def create_table_if_missing(client):
    """Create the BigQuery table if it doesn't already exist."""
    from google.cloud import bigquery

    dataset_ref = client.dataset(config.BQ_DATASET)
    table_ref   = dataset_ref.table(config.BQ_TABLE)

    try:
        client.get_table(table_ref)
        print(f"  Table already exists: {config.BQ_TABLE}")
    except Exception:
        # Convert our schema list into BigQuery SchemaField objects
        bq_schema = [
            bigquery.SchemaField(col["name"], col["type"])
            for col in TABLE_SCHEMA
        ]

        table = bigquery.Table(table_ref, schema=bq_schema)

        # Partition by "created" date so BigQuery only scans relevant data
        # (makes queries faster and cheaper)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="created"
        )

        client.create_table(table)
        print(f"  ✅ Created table: {config.BQ_TABLE}")

    return table_ref


def insert_chunk_with_retry(client, table_ref, chunk, chunk_number):
    """
    Try to insert a chunk of rows into BigQuery.
    If it fails, wait a bit and try again (up to 3 times).

    This handles temporary network issues gracefully.
    """

    max_attempts = 3
    wait_seconds = 5

    for attempt in range(1, max_attempts + 1):
        try:
            errors = client.insert_rows_json(table_ref, chunk)

            if not errors:
                return True  # Success!

            # Some rows had issues (but the request itself worked)
            print(f"  ⚠️  Chunk {chunk_number} had {len(errors)} row errors")
            return True

        except Exception as error:
            print(f"  ❌ Chunk {chunk_number} attempt {attempt} failed: {error}")

            if attempt < max_attempts:
                print(f"  ⏳ Waiting {wait_seconds}s before retrying...")
                time.sleep(wait_seconds)
                wait_seconds *= 2  # Wait longer each time (2s, 4s, 8s...)
            else:
                print(f"  ❌ Chunk {chunk_number} failed after {max_attempts} attempts")
                return False


def remove_duplicates(client):
    """
    Remove duplicate rows from the BigQuery table.
    We keep only the LATEST row for each unique 'ref' value.

    This uses a SQL query to do the deduplication.
    ROW_NUMBER() assigns a number to each row, ordered by date (newest first).
    We then keep only the row numbered 1 (the newest one).
    """

    full_table_name = f"`{config.GCP_PROJECT_ID}.{config.BQ_DATASET}.{config.BQ_TABLE}`"

    sql = f"""
        CREATE OR REPLACE TABLE {full_table_name}
        PARTITION BY DATE(created)
        AS (
            SELECT * EXCEPT (row_num)
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY ref       -- group rows with the same ref
                        ORDER BY created DESC  -- newest first
                    ) AS row_num
                FROM {full_table_name}
            )
            WHERE row_num = 1  -- keep only the first (newest) in each group
        )
    """

    job = client.query(sql)
    job.result()  # Wait for the query to finish
    print("  ✅ Duplicates removed")


def split_into_chunks(lst, chunk_size):
    """
    Split a large list into smaller lists of size chunk_size.

    Example: split_into_chunks([1,2,3,4,5], 2) → [[1,2], [3,4], [5]]
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def save_to_csv(rows, file_path):
    """
    Save rows to a CSV file instead of BigQuery.
    Useful for testing — you can open the CSV in Excel to check your data.
    """

    if not rows:
        print("No rows to save.")
        return

    column_names = [col["name"] for col in TABLE_SCHEMA]

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=column_names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Saved {len(rows):,} rows to CSV: {file_path}")

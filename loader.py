import csv
import time

import config


TABLE_SCHEMA = [
    {"name": "id", "type": "STRING"},
    {"name": "action", "type": "STRING"},
    {"name": "success", "type": "BOOLEAN"},
    {"name": "gateway", "type": "STRING"},
    {"name": "ref", "type": "STRING"},
    {"name": "service", "type": "STRING"},
    {"name": "time", "type": "INTEGER"},
    {"name": "created", "type": "TIMESTAMP"},
    {"name": "response", "type": "STRING"},
    {"name": "amount", "type": "FLOAT64"},
    {"name": "confirmationTime", "type": "TIMESTAMP"},
    {"name": "customerAddress", "type": "STRING"},
    {"name": "customerMeterNumber", "type": "STRING"},
    {"name": "debtAmount", "type": "FLOAT64"},
    {"name": "initiationTime", "type": "TIMESTAMP"},
    {"name": "status", "type": "STRING"},
    {"name": "units", "type": "FLOAT64"},
    {"name": "unitsType", "type": "STRING"},
    {"name": "value", "type": "STRING"},
    {"name": "vat", "type": "FLOAT64"},
]

CLUSTERING_FIELDS = ["service", "status", "success", "gateway"]


def load_to_bigquery(rows):
    client, table_ref = start_bigquery_load()

    print(f"Loading {len(rows):,} rows in chunks of {config.CHUNK_SIZE}...")
    total_loaded = load_bigquery_rows(client, table_ref, rows)

    finish_bigquery_load(client)
    print(f"Loading complete - {total_loaded:,} rows in BigQuery")


def start_bigquery_load():
    try:
        from google.cloud import bigquery
    except ImportError:
        raise RuntimeError("BigQuery library not installed. Run: pip install google-cloud-bigquery")

    print(f"Connecting to BigQuery project: {config.GCP_PROJECT_ID}")
    client = bigquery.Client(project=config.GCP_PROJECT_ID)

    create_dataset_if_missing(client)
    table_ref = create_table_if_missing(client)
    return client, table_ref


def load_bigquery_rows(client, table_ref, rows, batch_label=None):
    total_loaded = 0
    label = f"batch {batch_label}, " if batch_label is not None else ""

    for chunk_number, chunk in enumerate(split_into_chunks(rows, config.CHUNK_SIZE), start=1):
        success = insert_chunk_with_retry(client, table_ref, chunk, chunk_number)
        if success:
            total_loaded += len(chunk)
            print(f"  {label}chunk {chunk_number} loaded ({total_loaded:,}/{len(rows):,} rows)")

    return total_loaded


def finish_bigquery_load(client):
    print("Removing duplicate rows...")
    remove_duplicates(client)


def create_dataset_if_missing(client):
    from google.cloud import bigquery
    from google.api_core.exceptions import NotFound

    dataset_full_name = f"{config.GCP_PROJECT_ID}.{config.BQ_DATASET}"

    try:
        client.get_dataset(dataset_full_name)
        print(f"  Dataset already exists: {config.BQ_DATASET}")
    except NotFound:
        dataset = bigquery.Dataset(dataset_full_name)
        dataset.location = "US"
        client.create_dataset(dataset)
        print(f"  Created dataset: {config.BQ_DATASET}")


def create_table_if_missing(client):
    from google.cloud import bigquery
    from google.api_core.exceptions import NotFound

    dataset_ref = client.dataset(config.BQ_DATASET)
    table_ref = dataset_ref.table(config.BQ_TABLE)
    bq_schema = _bigquery_schema(bigquery)

    try:
        table = client.get_table(table_ref)
        print(f"  Table already exists: {config.BQ_TABLE}")

        if not table.schema:
            if table.num_rows:
                raise RuntimeError(
                    f"Existing table {config.BQ_TABLE} has no schema and contains rows. "
                    "Use a new BQ_TABLE name or recreate the table with this pipeline schema."
                )

            print("  Existing empty table has no schema; recreating it with pipeline schema.")
            client.delete_table(table_ref)
            table = _build_table(table_ref, bq_schema, bigquery)
            client.create_table(table)
            print(f"  Recreated table: {config.BQ_TABLE}")

    except NotFound:
        table = _build_table(table_ref, bq_schema, bigquery)
        client.create_table(table)
        print(f"  Created table: {config.BQ_TABLE}")

    return table_ref


def insert_chunk_with_retry(client, table_ref, chunk, chunk_number):
    max_attempts = 3
    wait_seconds = 5

    for attempt in range(1, max_attempts + 1):
        try:
            row_ids = [row.get("id") for row in chunk]
            errors = client.insert_rows_json(table_ref, chunk, row_ids=row_ids)

            if not errors:
                return True

            print(f"  Chunk {chunk_number} had {len(errors)} row errors")
            for error in errors[:3]:
                print(f"    {error}")
            return False

        except Exception as error:
            print(f"  Chunk {chunk_number} attempt {attempt} failed: {error}")

            if attempt < max_attempts:
                print(f"  Waiting {wait_seconds}s before retrying...")
                time.sleep(wait_seconds)
                wait_seconds *= 2
            else:
                print(f"  Chunk {chunk_number} failed after {max_attempts} attempts")
                return False


def remove_duplicates(client):
    full_table_name = f"`{config.GCP_PROJECT_ID}.{config.BQ_DATASET}.{config.BQ_TABLE}`"

    sql = f"""
        CREATE OR REPLACE TABLE {full_table_name}
        PARTITION BY DATE(created)
        CLUSTER BY service, status, success, gateway
        AS (
            SELECT * EXCEPT (row_num)
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY id
                        ORDER BY created DESC
                    ) AS row_num
                FROM {full_table_name}
            )
            WHERE row_num = 1
        )
    """

    job = client.query(sql)
    job.result()
    print("  Duplicates removed")


def save_to_csv(rows, file_path, append=False):
    if not rows:
        print("No rows to save.")
        return

    column_names = [col["name"] for col in TABLE_SCHEMA]
    mode = "a" if append else "w"

    with open(file_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=column_names, extrasaction="ignore")
        if not append:
            writer.writeheader()
        writer.writerows(rows)

    action = "Appended" if append else "Saved"
    print(f"{action} {len(rows):,} rows to CSV: {file_path}")


def split_into_chunks(rows, chunk_size):
    for i in range(0, len(rows), chunk_size):
        yield rows[i:i + chunk_size]


def _bigquery_schema(bigquery):
    return [
        bigquery.SchemaField(column["name"], column["type"])
        for column in TABLE_SCHEMA
    ]


def _build_table(table_ref, bq_schema, bigquery):
    table = bigquery.Table(table_ref, schema=bq_schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="created",
    )
    table.clustering_fields = CLUSTERING_FIELDS
    return table

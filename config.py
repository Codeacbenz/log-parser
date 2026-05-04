# config.py
# ─────────────────────────────────────────────────────────────
# This file holds all the settings for our pipeline.
# Think of it like a "control panel" — change values here
# and everything else in the pipeline will use the new values.
# ─────────────────────────────────────────────────────────────


# Where is the JSON file we want to read?
SOURCE_FILE = "crown_interactive_january_logs.json"

# Where should we save the output CSV?
OUTPUT_FILE = "output.csv"


FAILED_RECORDS_FILE = "failed_records.jsonl"

# ── BigQuery Settings ──────────────────────────────────────────
# Fill these in when you're ready to load data into BigQuery.
# For now, you can leave them as placeholders.

GCP_PROJECT_ID = "your-gcp-project-id"   # e.g. "my-company-project"
BQ_DATASET    = "crown_logs"             # like a "folder" in BigQuery
BQ_TABLE      = "parsed_logs"           # like a "spreadsheet" inside the folder

# How many rows to send to BigQuery at a time?
# Smaller = safer but slower. 500 is a good default.
CHUNK_SIZE = 500

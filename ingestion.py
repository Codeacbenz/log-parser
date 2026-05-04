# ingestion.py
import json

def load_records(file_path):
    """
    Reads a large JSON file line-by-line. 
    This is much safer for 400MB+ files with potential typos.
    """
    records = []
    print(f"Reading {file_path} line-by-line...")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                # Clean the line (remove commas at the end, and brackets)
                clean_line = line.strip()
                
                # Skip lines that are just start [ or end ] brackets
                if clean_line == "[" or clean_line == "]" or not clean_line:
                    continue
                
                # Remove trailing comma if it exists (e.g., '},' -> '}')
                if clean_line.endswith(","):
                    clean_line = clean_line[:-1]
                
                try:
                    # Try to parse just this ONE record
                    record = json.loads(clean_line)
                    records.append(record)
                except json.JSONDecodeError:
                    # If this line is the "broken" one, skip it and keep going!
                    print(f"⚠️ Skipping broken data at line {i+1}")
                    continue
                    
                # Progress update every 500,000 lines so you know it's working
                if i % 500000 == 0 and i > 0:
                    print(f"  ...processed {i:,} lines")

        return records

    except Exception as e:
        print(f"❌ Critical error opening file: {e}")
        return []
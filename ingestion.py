# ingestion.py
import json

def load_records(file_path):
    records = []
    print(f"Reading {file_path} line-by-line...")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                clean_line = line.strip()
                
                if clean_line == "[" or clean_line == "]" or not clean_line:
                    continue
                
                if clean_line.endswith(","):
                    clean_line = clean_line[:-1]
                
                try:
                    # --- TRY TO LOAD THE JSON ---
                    record = json.loads(clean_line)
                    records.append(record)
                
                except json.JSONDecodeError:
                    # --- THIS IS WHERE YOU INPUT THE DEBUG CODE ---
                    # It only runs if the line above fails.
                    with open("debug_broken_lines.txt", "a") as f_bug:
                        f_bug.write(f"Line {i+1}: {line}\n")
                    
                    # We still use 'continue' to move to the next line 
                    # so the program doesn't stop.
                    continue
                    
                if i % 500000 == 0 and i > 0:
                    print(f"  ...processed {i:,} lines")

        return records

    except Exception as e:
        print(f"❌ Critical error opening file: {e}")
        return []
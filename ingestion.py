import json


def iter_records(file_path, read_size=1024 * 1024):
    """Yield records from a JSON array without loading the full dump into memory."""
    print(f"Reading {file_path} as a stream...")

    try:
        decoder = json.JSONDecoder()
        buffer = ""
        offset = 0
        record_count = 0

        with open(file_path, "r", encoding="utf-8") as f:
            while True:
                chunk = f.read(read_size)
                if not chunk and offset >= len(buffer):
                    break

                buffer += chunk

                while True:
                    offset = _skip_json_separators(buffer, offset)

                    if offset >= len(buffer):
                        buffer = ""
                        offset = 0
                        break

                    try:
                        record, next_offset = decoder.raw_decode(buffer, offset)
                    except json.JSONDecodeError:
                        if chunk:
                            buffer = buffer[offset:]
                            offset = 0
                            break

                        with open("debug_broken_lines.txt", "a", encoding="utf-8") as f_bug:
                            f_bug.write(buffer[offset:] + "\n")
                        return

                    yield record
                    record_count += 1
                    offset = next_offset

                    if record_count % 500000 == 0:
                        print(f"  ...processed {record_count:,} records")

    except Exception as e:
        print(f"Critical error opening file: {e}")


def _skip_json_separators(text, offset):
    while offset < len(text) and text[offset] in " \r\n\t[,]":
        offset += 1
    return offset


def iter_record_batches(file_path, batch_size=50000):
    batch = []

    for record in iter_records(file_path):
        batch.append(record)

        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def load_records(file_path):
    return list(iter_records(file_path))

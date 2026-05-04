Crown Interactive Log Parser Pipeline
A robust, 4-step Python data pipeline designed to process large-scale JSON transaction logs (up to 400MB+), transform nested data, and validate records for accuracy before saving them to a structured CSV format.


Overview
This project takes messy, large-scale logs from a JSON source and moves them through a "Quality Control" line. It is optimized for memory efficiency, using line-by-line streaming to handle millions of rows without crashing your computer.
The 4-Step Pipeline:
Ingest: Reads the raw JSON file line-by-line. If a line is corrupted, it skips it and logs the error rather than crashing.
Transform: Flattens the data. It extracts specific fields from top-level keys and parses SOAP XML responses to pull out values like status and VAT.
Validate: Performs quality checks (e.g., ensuring IDs exist and amounts are not negative).
Load: Saves the final "Clean" data into a .csv file for analysis in Excel or PowerBI.

 Project Structure
File	Role
main.py	----The "Conductor." Runs the whole process in order.
config.py	-----Settings file. Change your filenames and paths here.
ingestion.py	--Handles reading the massive 450MB+ JSON file efficiently.
transformation.py  ....Cleans the data and extracts info from the XML text.
validator.py	....Acts as the "Bouncer." Blocks bad or unrealistic data.
loader.py	.........Formats and saves the final data to the output file.
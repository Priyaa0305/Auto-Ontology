from pathlib import Path
import re
import sys
import pandas as pd
from database.connection import get_engine

def get_table_name(filename):
    """Convert a CSV filename into a valid PostgreSQL table name."""
    name = Path(filename).stem.lower()
    # Replace spaces and special characters with underscores
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # PostgreSQL table names should not start with a number
    if name and name[0].isdigit():
        name = "table_" + name
    return name

def load_csv_files(data_dir):
    data_dir = Path(data_dir).resolve()
    if not data_dir.exists() or not data_dir.is_dir():
        raise FileNotFoundError(f"Dataset folder not found: {data_dir}")
    csv_files = sorted(data_dir.glob("*.csv"))

    if not csv_files:
        print("No CSV files found.")
        return
    engine = get_engine()

    try:
        print(f"Found {len(csv_files)} CSV files.\n")
        for csv_file in csv_files:
            table_name = get_table_name(csv_file.name)
            print(f"Importing {csv_file.name}...")
            headers = pd.read_csv(csv_file, nrows=0).columns

            # Preserve identifier-like columns as strings
            string_columns = {
                column: "string"
                for column in headers
                if column.lower().endswith(("_id", "_prefix"))
            }

            total_rows = 0
            first_chunk = True
            chunks = pd.read_csv(csv_file, dtype=string_columns, chunksize=50000, low_memory=False)

            for chunk in chunks:
                chunk.to_sql(
                    name=table_name,
                    con=engine,
                    if_exists="replace" if first_chunk else "append",
                    index=False,
                    chunksize=1000,
                    method="multi"
                )

                total_rows += len(chunk)
                first_chunk = False

            print(f"Imported {total_rows:,} rows " f"into table '{table_name}'.\n")
        print("All CSV files imported successfully!")
    finally:
        engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m database.csv_loader <dataset_folder>")
        sys.exit(1)
    load_csv_files(sys.argv[1])

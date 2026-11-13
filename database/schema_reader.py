from sqlalchemy import inspect, text
from database.connection import get_engine

def get_database_schema(engine):
    """Read tables, columns, data types and sample records."""

    inspector = inspect(engine)
    table_names = inspector.get_table_names(schema="public")
    database_schema = {}
    with engine.connect() as connection:
        for table_name in table_names:
            print(f"Inspecting table: {table_name}")
            # Read column information
            columns = inspector.get_columns(table_name,schema="public")
            column_details = []
            for column in columns:
                column_details.append({
                    "column_name": column["name"],
                    "data_type": str(column["type"]),
                    "nullable": column["nullable"]
                })

            # Safely quote the table name
            quoted_table = (engine.dialect.identifier_preparer.quote(table_name))
            # Get total number of records
            row_count = connection.execute(text(f"SELECT COUNT(*) FROM public.{quoted_table}")).scalar()
            # Retrieve three sample records
            sample_result = connection.execute(text(f"SELECT * FROM public.{quoted_table} LIMIT 3"))
            sample_data = [dict(row)for row in sample_result.mappings().all()]

            database_schema[table_name] = {
                "table_name": table_name,
                "row_count": row_count,
                "columns": column_details,
                "sample_data": sample_data
            }
    return database_schema

def print_database_schema(database_schema):
    """Display the discovered database structure."""
    print("\n DATABASE SCHEMA\n")

    for table_name, details in database_schema.items():
        print(f"\nTABLE: {table_name}")
        print(f"TOTAL ROWS: {details['row_count']}")
        print("\nCOLUMNS:")

        for column in details["columns"]:
            print(
                f"  {column['column_name']} | "
                f"Type: {column['data_type']} | "
                f"Nullable: {column['nullable']}"
            )
        print("\nSAMPLE RECORDS:")
        for record in details["sample_data"]:
            print(record)
        print("-" * 60)

if __name__ == "__main__":
    engine = get_engine()
    try:
        schema = get_database_schema(engine)
        print_database_schema(schema)
        print("\nSchema inspection completed successfully!")
    finally:
        engine.dispose()

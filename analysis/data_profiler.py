from sqlalchemy import inspect, text
from database.connection import get_engine

def profile_database(engine):
    """
    Profile every column in every public database table.
    Collect:
    1. Total row count
    2. Null value count and percentage
    3. Distinct value count
    4. Sample values
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    profiles = {}
    with engine.connect() as connection:
        for table in tables:
            quoted_table = (engine.dialect.identifier_preparer.quote(table))
            total_rows = connection.execute(text(f"SELECT COUNT(*) FROM public.{quoted_table}")).scalar()

            profiles[table] = {"total_rows": total_rows,"columns": {}}
            columns = inspector.get_columns(table, schema="public")

            for column in columns:
                column_name = column["name"]
                quoted_column = (engine.dialect.identifier_preparer.quote(column_name))

                # Calculate null and distinct value counts
                stats = connection.execute(
                    text(
                        f"""
                        SELECT COUNT(*) FILTER (WHERE {quoted_column} IS NULL) AS null_count,
                        COUNT(DISTINCT {quoted_column}) AS distinct_count
                        FROM public.{quoted_table}
                        """
                    )).mappings().one()

                null_count = stats["null_count"]
                distinct_count = stats["distinct_count"]
                null_percentage = (null_count / total_rowsif total_rows > 0 else 0)

                # Collect up to five sample values
                samples = connection.execute(
                    text(
                        f"""
                        SELECT DISTINCT {quoted_column}::TEXT
                        FROM public.{quoted_table}
                        WHERE {quoted_column} IS NOT NULL
                        LIMIT 5
                        """
                        )).scalars().all()

                profiles[table]["columns"][column_name] = {
                    "data_type": str(column["type"]),
                    "null_count": null_count,
                    "null_percentage": round(null_percentage, 4),
                    "distinct_count": distinct_count,
                    "sample_values": samples
                }
    return profiles
    
if __name__ == "__main__":
    engine = get_engine()
    try:
        results = profile_database(engine)
        print("\n========== DATABASE PROFILING SUMMARY ==========")
        for table, table_info in results.items():
            print(f"\nTable: {table}")
            print(f"Total rows: {table_info['total_rows']:,}")
            for column, details in table_info["columns"].items():
                print(f"\n  Column: {column}")
                print(f"  Data type: {details['data_type']}")
                print(f"  Null percentage: {details['null_percentage']:.2%}")
                print(f"  Distinct values: {details['distinct_count']:,}")
                print(f"  Samples: {details['sample_values']}")
        print("\nDatabase profiling completed!")
    finally:
        engine.dispose()

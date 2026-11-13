from itertools import combinations
from sqlalchemy import inspect, text
from database.connection import get_engine

def is_identifier_column(column_name):
    """Check whether a column name looks like an identifier."""
    name = column_name.lower()

    return (name == "id" or name.endswith("_id") or name.endswith("_sequential"))


def detect_primary_keys(engine):
    """
    Infer likely primary keys using actual database values.
    Checks:
    1. No NULL values.
    2. Every value (or column combination) is unique.
    3. Column names provide additional semantic evidence.
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    detected_keys = {}

    with engine.connect() as connection:
        for table in tables:
            print(f"\nAnalyzing primary keys in: {table}")
            columns = inspector.get_columns(table, schema="public")
            column_names = [column["name"] for column in columns]
            quoted_table = (engine.dialect.identifier_preparer.quote(table))
            row_count = connection.execute(text(f"SELECT COUNT(*) FROM public.{quoted_table}")).scalar()
            candidates = []

            if row_count == 0:
                detected_keys[table] = candidates
                continue

            # Check every individual column
            for column in column_names:
                quoted_column = (engine.dialect.identifier_preparer.quote(column))

                result = connection.execute(
                    text(
                        f"""
                        SELECT COUNT(*) FILTER (WHERE {quoted_column} IS NULL) AS null_count,
                        COUNT(DISTINCT {quoted_column}) AS distinct_count
                        FROM public.{quoted_table}
                        """
                    )).mappings().one()

                null_count = result["null_count"]
                distinct_count = result["distinct_count"]

                # A primary key must be non-null and unique
                if null_count == 0 and distinct_count == row_count:
                    confidence = (0.99 if is_identifier_column(column) else 0.90)

                    candidates.append({
                        "columns": [column],
                        "type": "single_column",
                        "row_count": row_count,
                        "distinct_count": distinct_count,
                        "null_count": null_count,
                        "confidence": confidence,
                        "reason": (
                            "All values are unique and non-null."
                        )
                    })
            # Check combinations of identifier-like columns.
            # This helps discover composite keys.
            identifier_columns = [column for column in column_names if is_identifier_column(column)]

            for column_pair in combinations(identifier_columns, 2):
                col1, col2 = column_pair
                quoted_col1 = (engine.dialect.identifier_preparer.quote(col1))
                quoted_col2 = (engine.dialect.identifier_preparer.quote(col2))

                result = connection.execute(
                    text(
                        f"""
                        SELECT COUNT(DISTINCT ({quoted_col1}, {quoted_col2})) AS distinct_count,
                        COUNT(*) FILTER (WHERE {quoted_col1} IS NULL OR {quoted_col2} IS NULL) AS null_count
                        FROM public.{quoted_table}
                        """
                    )
                ).mappings().one()

                distinct_count = result["distinct_count"]
                null_count = result["null_count"]

                if null_count == 0 and distinct_count == row_count:
                    candidates.append({
                        "columns": [col1, col2],
                        "type": "composite",
                        "row_count": row_count,
                        "distinct_count": distinct_count,
                        "null_count": null_count,
                        "confidence": 0.95,
                        "reason": (
                            "The column combination is unique "
                            "and contains no NULL values."
                        )
                    })

            # Highest confidence candidates first
            candidates.sort(
                key=lambda item: item["confidence"],
                reverse=True
            )
            detected_keys[table] = candidates

            if candidates:
                for candidate in candidates:
                    print(
                        f"  Candidate: {candidate['columns']} | "
                        f"Type: {candidate['type']} | "
                        f"Confidence: {candidate['confidence']}"
                    )
            else:
                print("  No primary-key candidate found.")
    return detected_keys

if __name__ == "__main__":

    engine = get_engine()

    try:
        results = detect_primary_keys(engine)
        print("\n PRIMARY KEY DETECTION SUMMARY")

        for table, candidates in results.items():
            print(f"\nTable: {table}")
            if not candidates:
                print("  No candidate primary key detected.")
            else:
                for candidate in candidates:
                    print(
                        f"  {candidate['columns']} "
                        f"({candidate['type']}) - "
                        f"{candidate['confidence']:.0%}"
                    )
        print("\nPrimary-key detection completed!")
    finally:
        engine.dispose()

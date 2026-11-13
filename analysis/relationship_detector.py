from sqlalchemy import inspect, text
from database.connection import get_engine

def table_matches_column(parent_table, child_column):
    """
    Check whether the parent table name corresponds
    to the referenced column name using common naming conventions.
    """
    table_name = parent_table.lower()
    column_name = child_column.lower()

    # Remove the common foreign-key suffix
    if column_name.endswith("_id"):
        column_name = column_name[:-3]

    # Handle common plural forms
    if table_name.endswith("ies"):
        table_name = table_name[:-3] + "y"
    elif table_name.endswith("s"):
        table_name = table_name[:-1]

    return (
        table_name == column_name
        or parent_table.lower().startswith(child_column.lower())
    )

def detect_relationships(engine):
    """
    Discover potential foreign-key relationships by checking:
    1. Matching column names.
    2. Compatible database data types.
    3. Uniqueness of the referenced parent column.
    4. Actual value overlap between tables.
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")

    relationships = []
    with engine.connect() as connection:

        # Collect metadata for every table
        table_columns = {}
        for table in tables:
            columns = inspector.get_columns(table, schema="public")
            table_columns[table] = {
                column["name"]: str(column["type"]).upper()
                for column in columns
            }

        # Compare columns across different tables
        for child_table in tables:
            for child_column, child_type in table_columns[child_table].items():
                for parent_table in tables:
                    if child_table == parent_table:
                        continue
                    for parent_column, parent_type in table_columns[parent_table].items():

                        # Column names must match
                        if child_column.lower() != parent_column.lower():
                            continue

                        # Parent table name should correspond to the referenced column
                        if not table_matches_column(parent_table, child_column):
                            continue

                        # Basic type compatibility check
                        if child_type != parent_type:
                            continue

                        quoted_child_table = (engine.dialect.identifier_preparer.quote(child_table))
                        quoted_parent_table = (engine.dialect.identifier_preparer.quote(parent_table))
                        quoted_child_column = (engine.dialect.identifier_preparer.quote(child_column))
                        quoted_parent_column = (engine.dialect.identifier_preparer.quote(parent_column))

                        # Check whether the parent column is unique and non-null
                        parent_stats = connection.execute(
                            text(
                                f"""
                                SELECT
                                    COUNT(*) AS total_rows,
                                    COUNT(DISTINCT {quoted_parent_column}) AS distinct_values,
                                    COUNT(*) FILTER (WHERE {quoted_parent_column} IS NULL) AS null_values
                                FROM public.{quoted_parent_table}
                                """
                            )).mappings().one()

                        parent_is_unique = (parent_stats["total_rows"] > 0 and parent_stats["null_values"] == 0
                                and parent_stats["total_rows"]== parent_stats["distinct_values"])

                        # Count distinct child values
                        child_distinct = connection.execute(
                            text(
                                f"""
                                SELECT COUNT(DISTINCT {quoted_child_column})
                                FROM public.{quoted_child_table}
                                """
                            )
                        ).scalar()

                        if not child_distinct:
                            continue

                        # Find how many child values exist in the parent
                        matching_values = connection.execute(
                            text(
                                f"""
                                SELECT COUNT(DISTINCT child.{quoted_child_column})
                                FROM public.{quoted_child_table} AS child
                                INNER JOIN public.{quoted_parent_table} AS parent
                                ON child.{quoted_child_column}
                                   = parent.{quoted_parent_column}
                                """
                            )).scalar()

                        coverage = matching_values / child_distinct
                        # A unique parent column is required for a
                        # conventional many-to-one foreign-key candidate.
                        if not parent_is_unique:
                            continue

                        # Ignore weak matches
                        if coverage < 0.80:
                            continue

                        # Calculate a confidence score
                        confidence = (
                            0.50 * coverage
                            + 0.30
                            + 0.20
                        )
                        relationship = {
                            "from_table": child_table,
                            "from_column": child_column,
                            "to_table": parent_table,
                            "to_column": parent_column,
                            "matching_values": matching_values,
                            "child_distinct_values": child_distinct,
                            "coverage": round(coverage, 4),
                            "parent_is_unique": parent_is_unique,
                            "confidence": round(confidence, 4)
                        }

                        relationships.append(relationship)
                        print(
                            f"Potential relationship: "
                            f"{child_table}.{child_column} -> "
                            f"{parent_table}.{parent_column} | "
                            f"Coverage: {coverage:.2%} | "
                            f"Confidence: {confidence:.2%}"
                        )
    return relationships


if __name__ == "__main__":
    engine = get_engine()
    try:
        results = detect_relationships(engine)
        print("\n========== RELATIONSHIP SUMMARY ==========")
        for relationship in results:
            print(
                f"{relationship['from_table']}."
                f"{relationship['from_column']} -> "
                f"{relationship['to_table']}."
                f"{relationship['to_column']}"
            )
        print(f"\nTotal relationships discovered: {len(results)}")
    finally:
        engine.dispose()

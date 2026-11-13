def validate_ontology(ontology, database_schema):
    """
    Validate the generated ontology against the actual database schema.

    Checks:
    - Every entity refers to an existing database table.
    - Every attribute refers to an existing database column.
    - Primary-key candidates refer to existing columns.
    - Every relationship refers to existing tables and columns.
    - Confidence values are between 0 and 1.
    """

    errors = []
    warnings = []
    entities = ontology.get("entities", [])
    relationships = ontology.get("relationships", [])
    entity_tables = set()
    # Validate entities and attributes.
    for entity in entities:

        table_name = entity.get("table_name")
        if table_name not in database_schema:
            errors.append(
                f"Unknown database table in entity: {table_name}"
            )
            continue
        entity_tables.add(table_name)
        actual_columns = {column["column_name"] for column in database_schema[table_name]["columns"] }

        for attribute in entity.get("attributes", []):

            attribute_name = attribute.get("name")
            if attribute_name not in actual_columns:
                errors.append(f"Unknown attribute {table_name}.{attribute_name}")

        # Validate primary-key candidates.
        for candidate in entity.get("primary_key_candidates", []):
            for column in candidate.get("columns", []):

                if column not in actual_columns:
                    errors.append(
                        f"Unknown primary-key candidate: "
                        f"{table_name}.{column}"
                    )

            confidence = candidate.get("confidence")
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not 0 <= confidence <= 1
            ):
                errors.append(
                    f"Invalid primary-key confidence in {table_name}"
                )

    # Validate relationships.
    for relationship in relationships:
        source = relationship.get("from", {})
        target = relationship.get("to", {})
        source_table = source.get("table")
        source_column = source.get("column")
        target_table = target.get("table")
        target_column = target.get("column")

        if source_table not in database_schema:
            errors.append(f"Unknown relationship source table: {source_table}")
            continue
        if target_table not in database_schema:
            errors.append(
                f"Unknown relationship target table: {target_table}"
            )
            continue

        source_columns = {
            column["column_name"]
            for column in database_schema[source_table]["columns"]
        }

        target_columns = {
            column["column_name"]
            for column in database_schema[target_table]["columns"]
        }

        if source_column not in source_columns:
            errors.append(
                f"Unknown relationship source column: "
                f"{source_table}.{source_column}"
            )

        if target_column not in target_columns:
            errors.append(
                f"Unknown relationship target column: "
                f"{target_table}.{target_column}"
            )

        confidence = relationship.get("confidence")

        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            errors.append(
                f"Invalid relationship confidence: "
                f"{source_table}.{source_column}"
            )

        if relationship.get("validation_status") == "needs_review":
            warnings.append(
                f"Relationship needs review: "
                f"{source_table}.{source_column} -> "
                f"{target_table}.{target_column}"
            )

    # Check for duplicate entity table mappings.
    if len(entity_tables) != len(entities):
        warnings.append(
            "Some entities may refer to the same database table."
        )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "entity_count": len(entities),
        "relationship_count": len(relationships)
    }
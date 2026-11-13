import re
from datetime import datetime, timezone
from database.schema_reader import get_database_schema
from analysis.data_profiler import profile_database
from analysis.primary_key_detector import detect_primary_keys
from analysis.relationship_detector import detect_relationships
from ai.entity_generator import generate_entity_metadata
from ai.relationship_validator import validate_relationship
from ontology.auto_ontology_integration import get_nvidia_semantic_graph
import json
from ai.nvidia_client import generate_text

def normalize_name(name):
    """Normalize names for dataset-independent entity matching."""

    words = re.findall(r"[a-z0-9]+", name.lower())
    normalized_words = []

    for word in words:
        if word.endswith("ies") and len(word) > 3:
            word = word[:-3] + "y"
        elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            word = word[:-1]
        normalized_words.append(word)
    return "".join(normalized_words)

def map_nvidia_entities(table_names, nvidia_nodes):
    """
    Dynamically match NVIDIA semantic entities to database tables.

    First tries normalized name matching.
    Uses NVIDIA LLM to match remaining entities and tables.
    Validates every AI-generated mapping against actual names.
    """

    matched = {}
    used_nodes = set()
    unmatched_tables = []

    # First: match names directly after normalization.
    for table_name in table_names:
        normalized_table = normalize_name(table_name)
        matching_nodes = [
            node for node in nvidia_nodes
            if node.get("name")
            and normalize_name(node["name"]) == normalized_table
            and node["name"] not in used_nodes
        ]

        if matching_nodes:
            node = matching_nodes[0]
            matched[table_name] = node
            used_nodes.add(node["name"])
        else:
            unmatched_tables.append(table_name)

    # Second: use NVIDIA LLM for names that cannot be matched directly.
    available_nodes = [
        {
            "name": node.get("name"),
            "description": node.get("description", "")
        }
        for node in nvidia_nodes
        if node.get("name") not in used_nodes
    ]

    if unmatched_tables and available_nodes:
        prompt = f"""
        Match database tables to semantic entities.
        Actual database table names:
        {json.dumps(unmatched_tables)}

        Available NVIDIA semantic entities:
        {json.dumps(available_nodes)}

        Match entities based on their meaning and business context,
        not just their spelling.
        Only create a mapping when the meaning is reasonably clear.
        Do not invent table names or entity names.
        Do not map multiple tables to the same entity.
        Return ONLY valid JSON in this format:

        {{
            "mappings": [
                {{
                    "table_name": "actual_table_name",
                    "entity_name": "actual_NVIDIA_entity_name"
                }}
            ]
        }}

        If a match is uncertain, leave it out.
        """
        try:
            response = generate_text(
                prompt,
                system_prompt=(
                    "You are an expert in semantic database "
                    "entity matching and ontology engineering."
                )
            )

            match = re.search(r"\{.*\}", response, re.DOTALL)

            if not match:
                raise ValueError("No valid JSON mapping returned.")
            result = json.loads(match.group())

            valid_node_names = {
                node.get("name"): node
                for node in nvidia_nodes
                if node.get("name")
            }

            for mapping in result.get("mappings", []):
                table_name = mapping.get("table_name")
                entity_name = mapping.get("entity_name")

                if (
                    table_name in unmatched_tables
                    and entity_name in valid_node_names
                    and entity_name not in used_nodes
                ):
                    matched[table_name] = valid_node_names[entity_name]
                    used_nodes.add(entity_name)

        except Exception as error:
            print("NVIDIA semantic matching unavailable. " f"Using direct matches only: {error}")
    return matched

def build_ontology(engine):
    """
    Combine database analysis, NVIDIA Auto Ontology entities,
    and NVIDIA LLM semantic descriptions into one ontology.
    """

    print("\nSTEP 1: Reading database schema...")
    database_schema = get_database_schema(engine)

    print("\nSTEP 2: Profiling database columns...")
    profiles = profile_database(engine)

    print("\nSTEP 3: Detecting primary-key candidates...")
    primary_keys = detect_primary_keys(engine)

    print("\nSTEP 4: Detecting database relationships...")
    relationships = detect_relationships(engine)

    print("\nSTEP 5: Retrieving NVIDIA Auto Ontology graph...")
    nvidia_graph = get_nvidia_semantic_graph()
    nvidia_nodes = nvidia_graph["nodes"]
    nvidia_entities = map_nvidia_entities(
    list(database_schema.keys()),
    nvidia_nodes
    )

    print(f"Retrieved {len(nvidia_nodes)} NVIDIA semantic entities.")
    entities = []
    warnings = []

    print("\nSTEP 6: Generating entity descriptions and attributes...")

    for table_name, table_info in database_schema.items():
        print(f"\nGenerating ontology entity for: {table_name}")
        columns = [
            {
                "name": column["column_name"],
                "data_type": column["data_type"],
                "nullable": column["nullable"]
            }
            for column in table_info["columns"]
        ]

        sample_rows = table_info["sample_data"]
        column_profiles = profiles.get(table_name, {}).get("columns", {})

        # Retrieve the matching entity generated by NVIDIA Auto Ontology.
        nvidia_entity = nvidia_entities.get(table_name)

        try:
            ai_metadata = generate_entity_metadata(
                table_name=table_name,
                columns=columns,
                sample_rows=sample_rows,
                column_profiles=column_profiles
            )

            ai_attributes = ai_metadata.get("attributes", [])

            # Keep only attributes that actually exist in the database.
            actual_column_names = {
                column["name"] for column in columns
            }

            attributes = [
                attribute
                for attribute in ai_attributes
                if attribute.get("name") in actual_column_names
            ]

            # Add a fallback meaning if the LLM omitted a real column.
            described_columns = {attribute["name"] for attribute in attributes}

            for column in columns:
                if column["name"] not in described_columns:
                    attributes.append({
                        "name": column["name"],
                        "meaning": (
                            f"Database column of type "
                            f"{column['data_type']}."
                        )
                    })

            entity_description = ai_metadata.get(
                "description",
                f"Entity representing records in the {table_name} table."
            )

            ai_entity_name = ai_metadata.get("entity_name", table_name)

        except Exception as error:
            warnings.append(f"Entity generation failed for {table_name}: {error}")

            entity_description = (f"Entity representing records in the {table_name} table.")
            ai_entity_name = table_name

            attributes = [
                {
                    "name": column["name"],
                    "meaning": (
                        f"Database column of type {column['data_type']}."
                    )
                }
                for column in columns
            ]

        # Prefer the semantic entity name created by NVIDIA Auto Ontology.
        entity_name = (
            nvidia_entity.get("name")
            if nvidia_entity
            else ai_entity_name
        )

        entities.append({
            "name": entity_name,
            "table_name": table_name,
            "description": entity_description,
            "row_count": table_info["row_count"],
            "attributes": attributes,
            "primary_key_candidates": primary_keys.get(
                table_name, []
            ),
            "nvidia_auto_ontology": {
                "entity_id": (
                    nvidia_entity.get("id")
                    if nvidia_entity else None
                ),
                "entity_name": (
                    nvidia_entity.get("name")
                    if nvidia_entity else None
                ),
                "description": (
                    nvidia_entity.get("description")
                    if nvidia_entity else None
                ),
                "matched": nvidia_entity is not None
            }
        })

    print("\nSTEP 7: Validating relationships using NVIDIA LLM...")
    validated_relationships = []

    for relationship in relationships:
        child_table = relationship["from_table"]
        child_column = relationship["from_column"]
        parent_table = relationship["to_table"]
        parent_column = relationship["to_column"]
        evidence = {
            "matching_values": relationship["matching_values"],
            "child_distinct_values": relationship[
                "child_distinct_values"
            ],
            "coverage": relationship["coverage"],
            "parent_is_unique": relationship["parent_is_unique"],
            "data_based_confidence": relationship["confidence"]
        }

        print(f"Validating {child_table}.{child_column} -> " f"{parent_table}.{parent_column}")
        try:
            ai_result = validate_relationship(
                child_table=child_table,
                child_column=child_column,
                parent_table=parent_table,
                parent_column=parent_column,
                evidence=evidence
            )

            ai_valid = ai_result["is_valid"]
            ai_confidence = ai_result["confidence"]

            # Do not let the LLM increase confidence beyond the
            # confidence supported by the actual database evidence.
            final_confidence = min(
                relationship["confidence"],
                ai_confidence
            )

            if not ai_valid:
                final_confidence *= 0.5

            relationship_name = ai_result["relationship_name"]
            description = ai_result["description"]
            reasoning = ai_result["reasoning"]
            validation_status = (
                "semantically_validated"
                if ai_valid else "needs_review"
            )

        except Exception as error:
            warnings.append(
                f"Relationship validation failed for "
                f"{child_table}.{child_column}: {error}"
            )

            relationship_name = "references"
            description = (
                f"{child_table}.{child_column} may reference "
                f"{parent_table}.{parent_column}."
            )
            reasoning = (
                "The database relationship was detected using "
                "column names, data types, parent uniqueness, "
                "and matching values. LLM validation was unavailable."
            )

            final_confidence = relationship["confidence"]
            validation_status = "data_detected_ai_not_available"

        validated_relationships.append({
            "from": {
                "table": child_table,
                "column": child_column
            },
            "to": {
                "table": parent_table,
                "column": parent_column
            },
            "relationship_name": relationship_name,
            "description": description,
            "reasoning": reasoning,
            "confidence": round(final_confidence, 4),
            "validation_status": validation_status,
            "evidence": evidence
        })

    ontology = {
        "metadata": {
            "database": engine.url.database,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "generation_method": (
                "PostgreSQL schema analysis + NVIDIA Auto Ontology "
                "+ NVIDIA hosted LLM"
            ),
            "entity_count": len(entities),
            "relationship_count": len(validated_relationships),
            "nvidia_entity_count": len(nvidia_nodes),
            "warnings": warnings
        },
        "entities": entities,
        "relationships": validated_relationships,
        "nvidia_semantic_graph": {
            "node_count": len(nvidia_nodes),
            "link_count": len(nvidia_graph["links"])
        }
    }
    print("\nOntology construction completed.")
    return ontology


if __name__ == "__main__":
    from database.connection import get_engine
    engine = get_engine()
    try:
        result = build_ontology(engine)
        print("\nEntities:", len(result["entities"]))
        print("Relationships:", len(result["relationships"]))

    finally:
        engine.dispose()
import json
import re
from pathlib import Path
import yaml
from database.connection import get_engine
from database.schema_reader import get_database_schema
from ontology.ontology_builder import build_ontology
from ontology.ontology_validator import validate_ontology


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"



def export_ontology(ontology, database_schema, database_name):
    """Validate and export ontology files for the selected database."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    safe_database_name = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        database_name
    )

    print("\nSTEP 1: Validating generated ontology...")

    validation = validate_ontology(
        ontology,
        database_schema
    )

    print("\nValidation results:")
    print(json.dumps(validation, indent=4))

    validation_path = (
        OUTPUT_DIR / f"{safe_database_name}_validation_report.json"
    )

    with open(validation_path, "w", encoding="utf-8") as file:
        json.dump(validation, file, indent=4, ensure_ascii=False)

    if not validation["is_valid"]:
        raise ValueError(
            f"Ontology validation failed for {database_name}. "
            f"Check {validation_path} for details."
        )

    json_path = OUTPUT_DIR / f"{safe_database_name}_ontology.json"
    yaml_path = OUTPUT_DIR / f"{safe_database_name}_ontology.yaml"

    print("\nSTEP 2: Exporting JSON ontology...")

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(
            ontology,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    print("\nSTEP 3: Exporting YAML ontology...")

    with open(yaml_path, "w", encoding="utf-8") as file:
        yaml.safe_dump(
            ontology,
            file,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False
        )

    print("\nOntology exported successfully!")
    print(f"JSON: {json_path}")
    print(f"YAML: {yaml_path}")
    print(f"Validation report: {validation_path}")



def main():
    print("=" * 60)
    print("AUTOMATED DATABASE ONTOLOGY GENERATOR")
    print("=" * 60)

    engine = get_engine()
    try:
        database_name = engine.url.database
        print(f"\nConnected database: {database_name}")
        print("\nBuilding ontology...")
        ontology = build_ontology(engine)
        print("\nReading schema for final validation...")
        database_schema = get_database_schema(engine)
        export_ontology(ontology,database_schema,database_name)

        print("\n" + "=" * 60)
        print("PROJECT EXECUTION COMPLETED")
        print("=" * 60)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
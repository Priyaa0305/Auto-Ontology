
import os
import re
import json
import subprocess
import sys
from pathlib import Path
import streamlit as st
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ----------------------------------------
# CONFIGURATION
# ----------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"

load_dotenv(PROJECT_DIR / ".env")

st.set_page_config(
    page_title="Auto Ontology Generator",
    page_icon="📄",
    layout="wide"
)
if "show_ontology" not in st.session_state:
    st.session_state.show_ontology = False


# ----------------------------------------
# DATABASE SELECTION
# ----------------------------------------

def get_databases():

    try:
        url = URL.create(
            "postgresql+psycopg",
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database="postgres"
        )

        engine = create_engine(url)

        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT datname
                FROM pg_database
                WHERE datistemplate = false
                  AND datallowconn = true
                ORDER BY datname
            """))

            databases = [row[0] for row in result]

        engine.dispose()
        return databases

    except Exception:
        return []


def safe_database_name(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


# ----------------------------------------
# ONTOLOGY FILES
# ----------------------------------------

def get_ontology_paths(database):

    name = safe_database_name(database)

    return (
        OUTPUT_DIR / f"{name}_ontology.json",
        OUTPUT_DIR / f"{name}_ontology.yaml"
    )


def load_ontology(database):

    json_path, yaml_path = get_ontology_paths(selected_database)

    if json_path.exists():
        with open(json_path, encoding="utf-8") as file:
            return json.load(file), json_path

    if yaml_path.exists():
        with open(yaml_path, encoding="utf-8") as file:
            return yaml.safe_load(file), yaml_path

    return None, None


# ----------------------------------------
# PAGE HEADER
# ----------------------------------------

st.title("Auto Ontology Generator")

st.write(
    "Automatically understand PostgreSQL databases "
    "and generate business ontologies using NVIDIA AI."
)

st.divider()


# ----------------------------------------
# DATABASE SELECTION
# ----------------------------------------

st.subheader("1. Select PostgreSQL Database")

databases = get_databases()

if databases:

    default_database = os.getenv("DB_NAME", "")

    if default_database in databases:
        default_index = databases.index(default_database)
    else:
        default_index = 0

    selected_database = st.selectbox(
        "Available databases",
        databases,
        index=default_index
    )

else:

    st.warning(
        "Could not retrieve the database list. "
        "Enter the database name manually."
    )

    selected_database = st.text_input(
        "PostgreSQL database name",
        value=os.getenv("DB_NAME", "")
    )


# ----------------------------------------
# GENERATE ONTOLOGY
# ----------------------------------------

st.subheader("2. Generate Ontology")

if st.button("Generate Ontology", type="primary"):
    if not selected_database.strip():
        st.error("Please select or enter a database name.")

    else:
        environment = os.environ.copy()
        environment["DB_NAME"] = selected_database

        with st.spinner(
            f"Generating ontology for {selected_database}..."
        ):
            try:
                result = subprocess.run(
                    [sys.executable, "main.py"],
                    cwd=PROJECT_DIR,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=900
                )

                if result.returncode == 0:
                    st.success("Ontology generated successfully!")

                    with st.expander("Generation logs"):
                        st.code(result.stdout)
                else:
                    st.error("Ontology generation failed.")
                    with st.expander("Error details"):
                        st.code(result.stdout + "\n" + result.stderr)
            except subprocess.TimeoutExpired:
                st.error("Generation timed out.")
            except Exception as error:
                st.error(str(error))

# DISPLAY ONTOLOGY
st.divider()
st.subheader("3. View Generated Ontology")

if selected_database.strip():
    ontology, source_path = load_ontology(selected_database)

    if ontology is None:

        st.info(
            "No existing ontology found for this database. "
            "Click Generate Ontology to create one."
        )

    else:

        st.success(f"Ontology loaded: {source_path.name}")

        metadata = ontology.get("metadata", {})

        entities = ontology.get("entities", [])
        relationships = ontology.get("relationships", [])

        if isinstance(entities, dict):
            entities = list(entities.values())

        if isinstance(relationships, dict):
            relationships = list(relationships.values())

        attribute_count = sum(
            len(entity.get("attributes", []))
            for entity in entities
        )

        col1, col2, col3 = st.columns(3)

        col1.metric("Entities", len(entities))
        col2.metric("Relationships", len(relationships))
        col3.metric("Attributes", attribute_count)

        st.divider()

        json_path, yaml_path = get_ontology_paths(
            selected_database
        )

        json_data = json.dumps(
            ontology,
            indent=4,
            ensure_ascii=False
        )

        yaml_data = yaml.safe_dump(
            ontology,
            sort_keys=False,
            allow_unicode=True
        )

        json_tab, yaml_tab = st.tabs(
            ["JSON Ontology", "YAML Ontology"]
        )

        with json_tab:

            st.json(ontology)

            st.download_button(
                "⬇ Download JSON",
                data=json_data,
                file_name=json_path.name,
                mime="application/json"
            )

        with yaml_tab:

            st.code(yaml_data, language="yaml")

            st.download_button(
                "⬇ Download YAML",
                data=yaml_data,
                file_name=yaml_path.name,
                mime="text/yaml"
            )

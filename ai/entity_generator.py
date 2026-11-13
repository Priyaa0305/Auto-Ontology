import json
from ai.nvidia_client import generate_text


def extract_json(response, table_name):
    """Extract the first valid JSON object from the model response."""

    if not isinstance(response, str) or not response.strip():
        raise ValueError(f"NVIDIA returned an empty response for table: {table_name}")

    decoder = json.JSONDecoder()
    for index, character in enumerate(response):
        if character == "{":
            try:
                result, _ = decoder.raw_decode(response[index:])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue

    raise ValueError(
        f"No valid JSON object found for table: {table_name}. "
        f"Response received: {response[:300]}"
    )

def generate_entity_metadata(
    table_name,
    columns,
    sample_rows=None,
    column_profiles=None
):
    """
    Generate semantic entity information for a database table
    using NVIDIA's hosted LLM.
    """

    actual_columns = [
        column["name"] if isinstance(column, dict) else str(column)
        for column in columns
    ]

    prompt = f"""
Analyze this database table and generate ontology metadata.
Table name: {table_name}
Actual columns:
{json.dumps(columns, default=str)}

Sample rows:
{json.dumps(sample_rows or [], default=str)}

Column profiles:
{json.dumps(column_profiles or {}, default=str)}
Return ONLY one valid JSON object in this exact format:
{{
    "entity_name": "Meaningful entity name",
    "description": "Clear description based on the supplied data",
    "attributes": [
        {{
            "name": "actual_column_name",
            "meaning": "Explanation of this column"
        }}
    ]
}}

Rules:
1. Use only the supplied column names.
2. Include every supplied column exactly once.
3. Do not invent attributes, relationships, or facts.
4. Base descriptions on the actual table name, columns, samples,
   and profiles.
5. Explain each column in simple, meaningful language.
6. Do not assume a column's meaning from its name alone if the
   supplied data does not support that interpretation.
7. Return valid JSON only. Do not use Markdown or code fences.
"""

    response = generate_text(
        prompt,
        system_prompt=(
            "You are an expert in database semantics and ontology "
            "engineering. Produce accurate metadata grounded only "
            "in the supplied database evidence."
        )
    )

    result = extract_json(response, table_name)
    # Validate the main fields.
    if not isinstance(result.get("entity_name"), str) or not result["entity_name"].strip():
        raise ValueError(f"Missing entity name for table: {table_name}")

    if not isinstance(result.get("description"), str) or not result["description"].strip():
        raise ValueError(f"Missing description for table: {table_name}")

    attributes = result.get("attributes")

    if not isinstance(attributes, list):
        raise ValueError(f"Invalid attributes list for table: {table_name}")

    # Validate that the model uses only real database columns.
    returned_names = []

    for attribute in attributes:
        if not isinstance(attribute, dict):
            raise ValueError(f"Invalid attribute format in table: {table_name}")

        name = attribute.get("name")
        meaning = attribute.get("meaning")

        if name not in actual_columns:
            raise ValueError(
                f"Unknown attribute returned for {table_name}: {name}"
            )

        if not isinstance(meaning, str) or not meaning.strip():
            raise ValueError(
                f"Missing meaning for attribute {name} in {table_name}"
            )

        if name in returned_names:
            raise ValueError(
                f"Duplicate attribute returned for {table_name}: {name}"
            )

        returned_names.append(name)

    # Check whether the model covered every actual column.
    missing_columns = set(actual_columns) - set(returned_names)
    if missing_columns:
        raise ValueError(
            f"NVIDIA did not explain these columns in {table_name}: "
            + ", ".join(sorted(missing_columns))
        )
    return result

import json
import re
from ai.nvidia_client import generate_text

def validate_relationship(child_table,child_column,parent_table,parent_column,evidence):
    """
    Use NVIDIA's LLM to semantically assess a candidate relationship.
    Database evidence is supplied to prevent unsupported assumptions.
    """

    prompt = f"""
    You are an expert database ontology engineer.
    Assess this proposed database relationship:
    Child table: {child_table}
    Child column: {child_column}
    Parent table: {parent_table}
    Parent column: {parent_column}
    Database evidence:
    {json.dumps(evidence, default=str)}
    Determine whether the relationship is semantically reasonable.

    Consider:
    1. Whether the column names suggest the same business concept.
    2. Whether the data types are compatible.
    3. Whether the parent column is unique.
    4. Whether the child values match values in the parent.
    5. Whether the relationship makes sense in the business context.

    Return ONLY valid JSON:
    {{
        "is_valid": true,
        "relationship_name": "belongs_to",
        "description": "Explanation of the relationship",
        "reasoning": "Why this relationship is reasonable or not",
        "confidence": 0.95
    }}

    Do not invent database evidence.
    Confidence must be between 0 and 1.
    """
    response = generate_text(
        prompt,
        system_prompt="You specialize in semantic relationship validation for relational databases."
    )
    match = re.search(r"\{.*\}", response, re.DOTALL)

    if not match:
        raise ValueError("NVIDIA did not return a valid JSON object.")
    try:
        result = json.loads(match.group())
    except json.JSONDecodeError as error:
        raise ValueError("NVIDIA returned invalid JSON.") from error

    # Validate the response structure.
    if not isinstance(result.get("is_valid"), bool):
        raise ValueError("Invalid relationship validation result.")

    confidence = result.get("confidence")
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("Invalid confidence score.")

    required_fields = ["relationship_name","description","reasoning"]

    for field in required_fields:
        if not isinstance(result.get(field), str) or not result[field].strip():
            raise ValueError(f"Missing or invalid field: {field}")
    return result

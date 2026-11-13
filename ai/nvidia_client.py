import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "nvidia/nemotron-3.5-lightning-30b-a3b"


def generate_text(prompt, system_prompt="You are an expert data and ontology engineer."):
    api_key = (
        os.getenv("NVIDIA_API_KEY")
        or os.getenv("DEFAULT_MODELS_API_KEY")
    )

    if not api_key:
        raise ValueError("NVIDIA API key is missing from the .env file.")
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "max_tokens": 6000,
        "chat_template_kwargs": {
            "enable_thinking": False
        }
    }
    request = Request(
        NVIDIA_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        choices = result.get("choices", [])

        if not choices:
            raise RuntimeError("NVIDIA returned no choices.")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content")

        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "NVIDIA returned no final text. "
                f"Finish reason: {choice.get('finish_reason')}. "
                f"Reasoning tokens: "
                f"{result.get('usage', {}).get('completion_tokens_details', {}).get('reasoning_tokens')}"
            )

        return content.strip()
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"NVIDIA API error ({error.code}): {details}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to NVIDIA API: {error.reason}"
        ) from error

# app/llm/core.py
import os
import json
import re
from typing import Tuple
from openai import OpenAI

GROQ_MODEL = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")

def get_client() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")
    # Groq is API-compatible with OpenAI chat completions
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

def chat_json(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """Return the model text (expected to be JSON)."""
    client = get_client()
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    content = resp.choices[0].message.content or ""
    return content

def extract_json_block(text: str) -> str:
    """
    Be tolerant: some models wrap JSON in prose or code fences.
    Extract the first {...} block.
    """
    # strip code fences
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE)
    # find first { ... } span
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= 0 and end > start:
        return text[start:end+1]
    return text  # hope it's plain JSON already

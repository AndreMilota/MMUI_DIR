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

def chat(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """Simple chat completion - returns the model's text response."""
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

def _repair_json_strings(text: str) -> str:
    """
    Replace literal control characters (newline, carriage return, tab) inside
    JSON string values with their escaped equivalents.

    Some models write multi-line SQL directly inside a JSON string field, e.g.:
        "sql": "SELECT ...
                FROM files ..."
    Literal newlines inside JSON strings are invalid (RFC 8259 §7). This
    function fixes them by scanning character-by-character and escaping
    control characters only while inside a string value.
    """
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string and ch == '\n':
            result.append('\\n')
        elif in_string and ch == '\r':
            result.append('\\r')
        elif in_string and ch == '\t':
            result.append('\\t')
        else:
            result.append(ch)
    return ''.join(result)


def extract_json_block(text: str) -> str:
    """
    Be tolerant: some models wrap JSON in prose or code fences, or include
    literal newlines inside JSON string values (invalid per RFC 8259).
    Extract the first {...} block and repair control characters in strings.
    """
    # Strip code fences
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE)
    # Find first { ... } span
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= 0 and end > start:
        block = text[start:end+1]
    else:
        block = text  # hope it's plain JSON already
    # Repair literal control characters inside string values
    return _repair_json_strings(block)

# test_groq.py (safe print using output_text)
import os
from openai import OpenAI

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise SystemExit("GROQ_API_KEY is not set.")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key,
)

response = client.responses.create(
    model="llama-3.3-70b-versatile",
    input="Please reply with a short greeting for a file-management agent."
)

# Preferred: convenience field that joins all text parts
text = getattr(response, "output_text", None)

# Fallback: if for some reason output_text is missing, show the whole object
if not text:
    print("Full response object (no output_text available):")
    print(response)
    raise SystemExit("Response did not include text content.")

print(text)

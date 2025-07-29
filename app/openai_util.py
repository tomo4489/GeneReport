import os
import openai
from .config import load_openai_config


MODEL = "gpt-4-1106-preview"

def parse_text_to_fields(text: str, fields: list[str]) -> dict:
    """Call OpenAI to parse text into fields"""
    cfg = load_openai_config()
    openai.api_key = cfg.get("key") or os.getenv("OPENAI_API_KEY")
    endpoint = cfg.get("endpoint") or os.getenv("OPENAI_ENDPOINT")
    if endpoint:
        openai.api_base = endpoint
    if not openai.api_key:
        raise RuntimeError("OpenAI API key not set")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    prompt = "Please extract the following fields from the text and return JSON: " + \
             ", ".join(fields) + "\nText:" + text
    messages = [
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(model=MODEL, messages=messages)
    content = response.choices[0].message.content
    try:
        import json
        return json.loads(content)
    except Exception:
        return {}

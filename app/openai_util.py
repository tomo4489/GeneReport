import os
import openai
from .config import load_openai_config

MODEL = "gpt-4-1106-preview"


def _setup_openai():
    cfg = load_openai_config()
    openai.api_key = cfg.get("key") or os.getenv("OPENAI_API_KEY")
    endpoint = cfg.get("endpoint") or os.getenv("OPENAI_ENDPOINT")
    if endpoint:
        openai.api_base = endpoint
    if not openai.api_key:
        raise RuntimeError("OpenAI API key not set")


def parse_text_to_fields(text: str, fields: list[str]) -> dict:
    """Call OpenAI to parse text into fields"""
    _setup_openai()
    field_lines = ",\n".join([f'    "{f}": {{{f}}}' for f in fields])
    example_lines = ",\n".join([f'    "{f}": "サンプル"' for f in fields])
    prompt = (
        f"{text}\nを下記の通りにレポート形式に直してください。Jsonで出力し、コロンは半角「:」を使用し、絶対に変更しないでください。指定された順序を維持してください。\n\n---\n{{\n{field_lines}\n}}\n---\n\n**記載例**\n{{\n{example_lines}\n}}"
    )
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(model=MODEL, messages=messages)
    content = response.choices[0].message.content
    try:
        import json
        return json.loads(content)
    except Exception:
        return {}


def chat_reply(message: str) -> str:
    _setup_openai()
    response = openai.ChatCompletion.create(model=MODEL, messages=[{"role": "user", "content": message}])
    return response.choices[0].message.content

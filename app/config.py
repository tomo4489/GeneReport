import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f)


def load_openai_config():
    cfg = load_config()
    return cfg.get('openai', {})


def save_openai_config(data: dict):
    cfg = load_config()
    cfg['openai'] = data
    save_config(cfg)

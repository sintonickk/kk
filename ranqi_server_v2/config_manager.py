import json
import sys
from pathlib import Path

def _base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def get_config_path(filename: str = 'config.json') -> Path:
    base = _base_dir()
    p = base / 'config' / filename
    return p

def load_config(filename: str = 'config.json') -> dict:
    path = get_config_path(filename)
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)

import json
import sys
from pathlib import Path
from typing import Optional

def _frozen_base_dir() -> Optional[Path]:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return None

def get_config_path(filename: str = "config.json") -> Path:
    frozen_dir = _frozen_base_dir()
    if frozen_dir is not None:
        p1 = frozen_dir / filename
        if p1.exists():
            return p1
        p2 = frozen_dir / "config" / filename
        if p2.exists():
            return p2
    dev_dir = Path(__file__).resolve().parent / "config"
    p3 = dev_dir / filename
    if p3.exists():
        return p3
    return p3

def load_config(filename: str = "config.json") -> dict:
    path = get_config_path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


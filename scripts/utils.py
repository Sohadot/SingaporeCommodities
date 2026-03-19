import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str):
    path = ROOT / relative_path
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_text(relative_path: str, content: str):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_dir(relative_path: str):
    path = ROOT / relative_path
    path.mkdir(parents=True, exist_ok=True)

from pathlib import Path
import markdown

from utils import ROOT


def load_markdown(relative_path: str) -> str:
    path = ROOT / relative_path
    raw = path.read_text(encoding="utf-8")
    return markdown.markdown(
        raw,
        extensions=["extra", "sane_lists"]
    )

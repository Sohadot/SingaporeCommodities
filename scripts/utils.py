"""
Shared utilities for the sovereign build system.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union


class BuildError(Exception):
    """Build-specific exception."""


class Logger:
    """Minimal structured logger."""

    def info(self, message: str) -> None:
        print(f"[INFO] {message}", file=sys.stdout)

    def success(self, message: str) -> None:
        print(f"[SUCCESS] {message}", file=sys.stdout)

    def warning(self, message: str) -> None:
        print(f"[WARNING] {message}", file=sys.stdout)

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}", file=sys.stderr)

    def debug(self, message: str) -> None:
        if os.getenv("DEBUG"):
            print(f"[DEBUG] {message}", file=sys.stdout)


def ensure_dir(path: Union[str, Path]) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def read_file(path: Union[str, Path]) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_file(path: Union[str, Path], content: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def read_json(path: Union[str, Path]) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=indent, ensure_ascii=False)


def calculate_checksum(path: Union[str, Path], algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def format_date(date: Optional[datetime] = None, fmt: str = "%Y-%m-%d") -> str:
    if date is None:
        date = datetime.now(timezone.utc)
    return date.strftime(fmt)


def format_datetime_iso(date: Optional[datetime] = None) -> str:
    if date is None:
        date = datetime.now(timezone.utc)
    return date.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def format_rfc2822(date: Optional[datetime] = None) -> str:
    if date is None:
        date = datetime.now(timezone.utc)
    return date.strftime("%a, %d %b %Y %H:%M:%S +0000")


def get_file_size(path: Union[str, Path]) -> int:
    return Path(path).stat().st_size


def is_preview_environment(environment: str) -> bool:
    return environment != "production"


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)


def truncate_text(text: str, length: int, suffix: str = "...") -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= length:
        return cleaned
    return cleaned[: max(0, length - len(suffix))].rstrip() + suffix

"""
Asset copying and recording.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List

from .utils import Logger, calculate_checksum, ensure_dir, get_file_size


class AssetCopier:
    """Copy static assets into dist/ and record metadata."""

    def __init__(self, assets_dir: Path, static_dir: Path, dist_dir: Path, logger: Logger) -> None:
        self.assets_dir = Path(assets_dir)
        self.static_dir = Path(static_dir)
        self.dist_dir = Path(dist_dir)
        self.logger = logger
        self.copied_assets: List[Dict[str, Any]] = []

    def copy_all(self) -> List[Dict[str, Any]]:
        self.copied_assets = []

        if self.assets_dir.exists():
            self._copy_directory(self.assets_dir, self.dist_dir / "assets")
        else:
            self.logger.warning(f"Assets directory missing: {self.assets_dir}")

        if self.static_dir.exists():
            for item in self.static_dir.iterdir():
                destination = self.dist_dir / item.name
                if item.is_dir():
                    self._copy_directory(item, destination)
                else:
                    self._copy_file(item, destination)
        else:
            self.logger.warning(f"Static directory missing: {self.static_dir}")

        self.logger.info(f"Copied {len(self.copied_assets)} assets")
        return self.copied_assets

    def _copy_directory(self, source: Path, destination: Path) -> None:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)

        for file_path in destination.rglob("*"):
            if file_path.is_file():
                self._record_asset(file_path)

    def _copy_file(self, source: Path, destination: Path) -> None:
        ensure_dir(destination.parent)
        shutil.copy2(source, destination)
        self._record_asset(destination)

    def _record_asset(self, full_path: Path) -> None:
        rel = full_path.relative_to(self.dist_dir)
        self.copied_assets.append(
            {
                "path": str(rel).replace("\\", "/"),
                "size": get_file_size(full_path),
                "checksum": calculate_checksum(full_path),
            }
        )

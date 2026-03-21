#!/usr/bin/env python3
"""
Validate dist/ output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

try:
    from .utils import Logger, read_file, read_json
except ImportError:  # pragma: no cover
    from scripts.utils import Logger, read_file, read_json


class DistValidator:
    """Validate build output integrity."""

    REQUIRED_FILES: List[str] = [
        "index.html",
        "404.html",
        "500.html",
        "robots.txt",
        "sitemap.xml",
        "rss.xml",
        "build-manifest.json",
        "_headers",
    ]

    REQUIRED_ASSETS: List[str] = [
        "assets/css/main.css",
        "assets/js/main.js",
        "assets/images/logo.svg",
        "assets/images/favicon.svg",
    ]

    def __init__(self, dist_dir: Path | str, logger: Logger) -> None:
        self.dist_dir = Path(dist_dir)
        self.logger = logger
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, strict: bool = False) -> bool:
        if not self.dist_dir.exists():
            self.errors.append(f"Dist directory missing: {self.dist_dir}")
            return False

        self._validate_required_files()
        self._validate_required_assets()
        self._validate_html_files()
        self._validate_manifest()
        self._validate_robots()
        self._validate_sitemap()

        for error in self.errors:
            self.logger.error(error)
        for warning in self.warnings:
            self.logger.warning(warning)

        if strict:
            return len(self.errors) == 0 and len(self.warnings) == 0
        return len(self.errors) == 0

    def _validate_required_files(self) -> None:
        for rel_path in self.REQUIRED_FILES:
            full_path = self.dist_dir / rel_path
            if not full_path.exists():
                self.errors.append(f"Required file missing: {rel_path}")

    def _validate_required_assets(self) -> None:
        for rel_path in self.REQUIRED_ASSETS:
            full_path = self.dist_dir / rel_path
            if not full_path.exists():
                self.errors.append(f"Required asset missing: {rel_path}")

    def _validate_html_files(self) -> None:
        html_files = sorted(self.dist_dir.rglob("*.html"))
        if not html_files:
            self.errors.append("No HTML files were generated")
            return

        for html_file in html_files:
            content = read_file(html_file)

            if "<!DOCTYPE html>" not in content:
                self.errors.append(f"Missing DOCTYPE: {html_file}")
            if "<html" not in content or "</html>" not in content:
                self.errors.append(f"Malformed html root: {html_file}")
            if "<head" not in content or "</head>" not in content:
                self.errors.append(f"Missing head section: {html_file}")
            if "<body" not in content or "</body>" not in content:
                self.errors.append(f"Missing body section: {html_file}")
            if len(content.strip()) < 300:
                self.errors.append(f"HTML file too small: {html_file}")

    def _validate_manifest(self) -> None:
        manifest_path = self.dist_dir / "build-manifest.json"
        if not manifest_path.exists():
            return

        try:
            manifest = read_json(manifest_path)
        except json.JSONDecodeError:
            self.errors.append("Invalid JSON in build-manifest.json")
            return

        for key in ("version", "environment", "timestamp", "build", "pages", "assets"):
            if key not in manifest:
                self.errors.append(f"Manifest missing key: {key}")

    def _validate_robots(self) -> None:
        path = self.dist_dir / "robots.txt"
        if not path.exists():
            return

        content = read_file(path)
        if "User-agent:" not in content:
            self.errors.append("robots.txt missing User-agent")
        if "Disallow: /" not in content and "Sitemap:" not in content:
            self.errors.append("robots.txt missing production or preview directive")

    def _validate_sitemap(self) -> None:
        path = self.dist_dir / "sitemap.xml"
        if not path.exists():
            return

        content = read_file(path)
        if "<urlset" not in content:
            self.errors.append("sitemap.xml missing urlset")
        if "<loc>" not in content:
            self.errors.append("sitemap.xml missing loc entries")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate dist output")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings")
    parser.add_argument("--dist", default="dist", help="Dist directory path")
    args = parser.parse_args()

    logger = Logger()
    validator = DistValidator(args.dist, logger)
    valid = validator.validate(strict=args.strict)
    raise SystemExit(0 if valid else 1)


if __name__ == "__main__":
    main()

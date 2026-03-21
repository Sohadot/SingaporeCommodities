"""
Robots.txt generator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .utils import Logger, write_file


class RobotsGenerator:
    """Generate robots.txt based on environment."""

    def __init__(
        self,
        dist_dir: Path,
        site_data: Dict[str, Any],
        is_production: bool,
        logger: Logger,
    ) -> None:
        self.dist_dir = Path(dist_dir)
        self.site_data = site_data
        self.is_production = is_production
        self.logger = logger
        self.base_url = site_data["url"].rstrip("/")

    def generate(self) -> None:
        self.logger.info("Generating robots.txt")
        content = self._production_content() if self.is_production else self._preview_content()
        write_file(self.dist_dir / "robots.txt", content)

    def _production_content(self) -> str:
        return "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                "Disallow: /api/",
                "Disallow: /admin/",
                "Disallow: /private/",
                "",
                f"Sitemap: {self.base_url}/sitemap.xml",
                "",
            ]
        )

    def _preview_content(self) -> str:
        return "\n".join(
            [
                "User-agent: *",
                "Disallow: /",
                "",
                "# Preview environment: no indexing",
                "",
            ]
        )

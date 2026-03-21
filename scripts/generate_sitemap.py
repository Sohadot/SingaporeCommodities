"""
Sitemap.xml generator.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from .utils import Logger, format_datetime_iso, write_file


class SitemapGenerator:
    """Generate XML sitemap."""

    def __init__(self, dist_dir: Path, site_data: Dict[str, Any], logger: Logger) -> None:
        self.dist_dir = Path(dist_dir)
        self.site_data = site_data
        self.logger = logger
        self.base_url = site_data["url"].rstrip("/")

    def generate(self, pages: List[Dict[str, Any]]) -> None:
        self.logger.info("Generating sitemap.xml")

        urlset = Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        now = datetime.now(timezone.utc)

        for page in pages:
            url_element = SubElement(urlset, "url")

            loc = SubElement(url_element, "loc")
            loc.text = self._resolve_full_url_from_path(page["path"], page["slug"])

            lastmod = SubElement(url_element, "lastmod")
            lastmod.text = format_datetime_iso(now)

            changefreq = SubElement(url_element, "changefreq")
            changefreq.text = "daily" if page["slug"] == "index" else "weekly"

            priority = SubElement(url_element, "priority")
            priority.text = "1.00" if page["slug"] == "index" else "0.80"

        rough = tostring(urlset, encoding="unicode")
        pretty = minidom.parseString(rough).toprettyxml(indent="  ")
        final_xml = "\n".join(line for line in pretty.splitlines() if line.strip())

        write_file(self.dist_dir / "sitemap.xml", final_xml)

    def _resolve_full_url_from_path(self, page_path: str, slug: str) -> str:
        if slug == "index":
            return f"{self.base_url}/"

        normalized = page_path.replace("\\", "/")
        if normalized.startswith("dist/"):
            normalized = normalized[len("dist/"):]
        if normalized.endswith("/index.html"):
            normalized = normalized[: -len("index.html")]
        elif normalized.endswith("index.html"):
            normalized = normalized[: -len("index.html")]
        normalized = normalized.strip("/")

        return f"{self.base_url}/{normalized}/" if normalized else f"{self.base_url}/"

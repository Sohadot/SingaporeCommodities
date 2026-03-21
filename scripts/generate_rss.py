"""
RSS feed generator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from .utils import Logger, format_rfc2822, write_file


class RSSGenerator:
    """Generate RSS 2.0 feed."""

    def __init__(self, dist_dir: Path, site_data: Dict[str, Any], logger: Logger) -> None:
        self.dist_dir = Path(dist_dir)
        self.site_data = site_data
        self.logger = logger
        self.base_url = site_data["url"].rstrip("/")

    def generate(self, pages: List[Dict[str, Any]]) -> None:
        self.logger.info("Generating rss.xml")

        rss = Element("rss")
        rss.set("version", "2.0")
        rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

        channel = SubElement(rss, "channel")

        title = SubElement(channel, "title")
        title.text = self.site_data["name"]

        link = SubElement(channel, "link")
        link.text = f"{self.base_url}/"

        description = SubElement(channel, "description")
        description.text = self.site_data["description"]

        language = SubElement(channel, "language")
        language.text = self.site_data.get("language", "en")

        last_build_date = SubElement(channel, "lastBuildDate")
        last_build_date.text = format_rfc2822()

        atom_link = SubElement(channel, "{http://www.w3.org/2005/Atom}link")
        atom_link.set("href", f"{self.base_url}/rss.xml")
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")

        for page in pages:
            slug = page["slug"]
            if slug == "index":
                continue

            item = SubElement(channel, "item")

            item_title = SubElement(item, "title")
            item_title.text = page["title"]

            item_link = SubElement(item, "link")
            item_link.text = f"{self.base_url}/{slug}/" if not page["path"].startswith("dist/articles/") and not page["path"].startswith("dist/chronicles/") and not page["path"].startswith("dist/guide/") and not page["path"].startswith("dist/tools/") else self._resolve_full_url_from_path(page["path"])

            item_guid = SubElement(item, "guid")
            item_guid.set("isPermaLink", "true")
            item_guid.text = item_link.text

            pub_date = SubElement(item, "pubDate")
            pub_date.text = format_rfc2822()

        rough = tostring(rss, encoding="unicode")
        pretty = minidom.parseString(rough).toprettyxml(indent="  ")
        final_xml = "\n".join(line for line in pretty.splitlines() if line.strip())

        write_file(self.dist_dir / "rss.xml", final_xml)

    def _resolve_full_url_from_path(self, page_path: str) -> str:
        normalized = page_path.replace("\\", "/")
        if normalized.startswith("dist/"):
            normalized = normalized[len("dist/"):]
        if normalized.endswith("/index.html"):
            normalized = normalized[: -len("index.html")]
        elif normalized.endswith("index.html"):
            normalized = normalized[: -len("index.html")]
        normalized = normalized.strip("/")
        return f"{self.base_url}/{normalized}/" if normalized else f"{self.base_url}/"

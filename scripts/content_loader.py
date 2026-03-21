"""
Strategic content loading and normalization layer.

This loader treats content/ as the editorial source of truth and converts
all markdown content into a unified node contract that can be rendered
consistently by the sovereign publishing system.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .utils import BuildError, Logger, read_json, truncate_text

try:
    import markdown as md_lib
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The 'markdown' package is required for content loading. "
        "Add it to requirements.txt as: markdown"
    ) from exc


class ContentLoader:
    """Load structured data and normalize editorial markdown collections."""

    REQUIRED_SITE_FIELDS = ("name", "url", "description")

    COLLECTIONS = {
        "pages": {
            "dir": "pages",
            "content_type": "page",
            "schema_type": "WebPage",
            "route_prefix": "",
        },
        "articles": {
            "dir": "articles",
            "content_type": "article",
            "schema_type": "Article",
            "route_prefix": "/articles",
        },
        "chronicles": {
            "dir": "chronicles",
            "content_type": "chronicle",
            "schema_type": "Article",
            "route_prefix": "/chronicles",
        },
        "guides": {
            "dir": "guides",
            "content_type": "guide",
            "schema_type": "Article",
            "route_prefix": "/guide",
        },
        "tools": {
            "dir": "tools",
            "content_type": "tool",
            "schema_type": "WebPage",
            "route_prefix": "/tools",
        },
    }

    def __init__(self, data_dir: Path, logger: Logger) -> None:
        self.data_dir = Path(data_dir)
        self.logger = logger
        self.root_dir = self.data_dir.parent
        self.content_dir = self.root_dir / "content"

        self.markdown = md_lib.Markdown(
            extensions=[
                "extra",
                "tables",
                "fenced_code",
                "toc",
                "sane_lists",
            ]
        )

    # ---------------------------------------------------------------------
    # Core structured data
    # ---------------------------------------------------------------------

    def load_site_data(self) -> Dict[str, Any]:
        site_file = self.data_dir / "site.json"
        if not site_file.exists():
            raise BuildError(f"Required file missing: {site_file}")

        try:
            data = read_json(site_file)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Invalid JSON in {site_file}: {exc}") from exc

        for field in self.REQUIRED_SITE_FIELDS:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                raise BuildError(f"Required site field missing or invalid: {field}")

        data.setdefault("language", "en")
        data.setdefault("charset", "UTF-8")
        data.setdefault("author", "")
        data.setdefault("logo", "")
        data.setdefault("favicon", "")
        data.setdefault("theme_color", "#05070D")
        data.setdefault("social_links", [])
        data.setdefault("contact", {})
        data.setdefault("version", "1.0.0")
        data.setdefault("analytics_id", None)

        if not isinstance(data["social_links"], list):
            raise BuildError("site.json field 'social_links' must be a list")
        if not isinstance(data["contact"], dict):
            raise BuildError("site.json field 'contact' must be an object")

        return data

    def load_navigation(self) -> Dict[str, List[Dict[str, Any]]]:
        nav_file = self.data_dir / "navigation.json"
        if not nav_file.exists():
            raise BuildError(f"Required file missing: {nav_file}")

        try:
            data = read_json(nav_file)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Invalid JSON in {nav_file}: {exc}") from exc

        if not isinstance(data, dict):
            raise BuildError("navigation.json must be a JSON object")

        main = data.get("main", [])
        footer = data.get("footer", [])

        if not isinstance(main, list) or not isinstance(footer, list):
            raise BuildError("navigation.json 'main' and 'footer' must be arrays")

        return {
            "main": self._validate_nav_items(main, "main"),
            "footer": self._validate_nav_items(footer, "footer"),
        }

    def _validate_nav_items(self, items: List[Dict[str, Any]], bucket: str) -> List[Dict[str, Any]]:
        validated: List[Dict[str, Any]] = []

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise BuildError(f"navigation.json {bucket}[{index}] must be an object")

            title = item.get("title")
            url = item.get("url")

            if not isinstance(title, str) or not title.strip():
                raise BuildError(f"navigation.json {bucket}[{index}] missing valid title")
            if not isinstance(url, str) or not url.strip():
                raise BuildError(f"navigation.json {bucket}[{index}] missing valid url")

            validated.append(
                {
                    "title": title.strip(),
                    "url": url.strip(),
                    "position": int(item.get("position", index + 1)),
                    "external": bool(item.get("external", False)),
                }
            )

        return validated

    # ---------------------------------------------------------------------
    # Unified editorial content map
    # ---------------------------------------------------------------------

    def load_content_map(self) -> Dict[str, Any]:
        """
        Load all markdown content and normalize it into a unified editorial map.

        Returns:
            {
              "home": {...},
              "collections": {
                  "pages": [...],
                  "articles": [...],
                  "chronicles": [...],
                  "guides": [...],
                  "tools": [...]
              }
            }
        """
        if not self.content_dir.exists():
            raise BuildError(f"Content directory missing: {self.content_dir}")

        collections: Dict[str, List[Dict[str, Any]]] = {
            "pages": [],
            "articles": [],
            "chronicles": [],
            "guides": [],
            "tools": [],
        }

        seen_paths: set[str] = set()

        for key, spec in self.COLLECTIONS.items():
            section_dir = self.content_dir / spec["dir"]
            if not section_dir.exists():
                self.logger.warning(f"Content section missing: {section_dir}")
                continue

            nodes = self._load_markdown_collection(
                section_dir=section_dir,
                section_key=key,
                content_type=spec["content_type"],
                schema_type=spec["schema_type"],
                route_prefix=spec["route_prefix"],
                seen_paths=seen_paths,
            )
            collections[key] = nodes

        home_node = self._extract_home_node(collections["pages"])

        if home_node is None:
            home_node = self._build_synthetic_home_node()

        collections["pages"] = [node for node in collections["pages"] if node["slug"] != "home"]

        return {
            "home": home_node,
            "collections": collections,
        }

    def _extract_home_node(self, pages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for node in pages:
            if node["slug"] == "home":
                return {
                    **node,
                    "is_home": True,
                    "is_index": True,
                    "url_path": "/",
                }
        return None

    def _build_synthetic_home_node(self) -> Dict[str, Any]:
        self.logger.warning("content/pages/home.md not found; generating synthetic home node")

        return {
            "slug": "index",
            "url_path": "/",
            "title": "Singapore Commodities",
            "description": "Strategic commodity intelligence platform.",
            "content_type": "page",
            "template": "home.html",
            "source_path": "synthetic:home",
            "is_home": True,
            "is_index": True,
            "section": "pages",
            "order": 0,
            "date": None,
            "updated_at": None,
            "tags": [],
            "schema_type": "WebPage",
            "content": {
                "eyebrow": "Strategic Platform",
                "headline": "Singapore Commodities",
                "intro": "A sovereign-grade interface for commodity systems, infrastructure, and strategic interpretation.",
                "highlights": [],
                "sections": [],
                "summary": "",
                "body": "",
            },
        }

    def _load_markdown_collection(
        self,
        section_dir: Path,
        section_key: str,
        content_type: str,
        schema_type: str,
        route_prefix: str,
        seen_paths: set[str],
    ) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []

        markdown_files = sorted(section_dir.rglob("*.md"))
        if not markdown_files:
            return nodes

        for path in markdown_files:
            node = self._build_node_from_markdown(
                path=path,
                section_key=section_key,
                content_type=content_type,
                schema_type=schema_type,
                route_prefix=route_prefix,
            )

            if node["url_path"] in seen_paths:
                raise BuildError(f"Duplicate route detected: {node['url_path']}")
            seen_paths.add(node["url_path"])

            nodes.append(node)

        nodes.sort(key=lambda item: (item.get("order", 0), item["title"].lower()))
        return nodes

    def _build_node_from_markdown(
        self,
        path: Path,
        section_key: str,
        content_type: str,
        schema_type: str,
        route_prefix: str,
    ) -> Dict[str, Any]:
        raw = path.read_text(encoding="utf-8")
        frontmatter, markdown_body = self._split_frontmatter(raw)

        slug = self._resolve_slug(path, frontmatter, section_key)
        title = self._resolve_title(frontmatter, markdown_body, slug)
        description = self._resolve_description(frontmatter, markdown_body, title)

        html_body = self._render_markdown(markdown_body)

        content_payload = self._normalize_content_payload(
            content_type=content_type,
            title=title,
            description=description,
            markdown_body=markdown_body,
            html_body=html_body,
            frontmatter=frontmatter,
        )

        url_path = self._resolve_url_path(section_key, slug, route_prefix)

        node: Dict[str, Any] = {
            "slug": slug,
            "url_path": url_path,
            "title": title,
            "description": description,
            "content_type": content_type,
            "template": "home.html" if section_key == "pages" and slug == "home" else "page.html",
            "source_path": str(path.relative_to(self.root_dir)).replace("\\", "/"),
            "is_home": section_key == "pages" and slug == "home",
            "is_index": section_key == "pages" and slug == "home",
            "section": section_key,
            "order": int(frontmatter.get("order", 0) or 0),
            "date": frontmatter.get("date"),
            "updated_at": frontmatter.get("updated_at"),
            "tags": frontmatter.get("tags", []) if isinstance(frontmatter.get("tags"), list) else [],
            "schema_type": frontmatter.get("schema_type", schema_type),
            "content": content_payload,
        }

        # Future-ready fields for tools and strategic assets
        if content_type == "tool":
            node["tool_type"] = frontmatter.get("tool_type", "reference")
            node["update_mode"] = frontmatter.get("update_mode", "manual")
            node["data_sources"] = frontmatter.get("data_sources", [])
            node["market_scope"] = frontmatter.get("market_scope", [])
            node["geostrategic_scope"] = frontmatter.get("geostrategic_scope", [])

        return node

    # ---------------------------------------------------------------------
    # Parsing and normalization helpers
    # ---------------------------------------------------------------------

    def _split_frontmatter(self, raw: str) -> Tuple[Dict[str, Any], str]:
        if not raw.startswith("---\n"):
            return {}, raw

        parts = raw.split("---", 2)
        if len(parts) < 3:
            return {}, raw

        _, fm_raw, body = parts
        try:
            frontmatter = yaml.safe_load(fm_raw.strip()) or {}
        except yaml.YAMLError as exc:
            raise BuildError(f"Invalid YAML frontmatter: {exc}") from exc

        if not isinstance(frontmatter, dict):
            raise BuildError("Markdown frontmatter must be a YAML object")

        return frontmatter, body.lstrip("\n")

    def _resolve_slug(self, path: Path, frontmatter: Dict[str, Any], section_key: str) -> str:
        raw_slug = frontmatter.get("slug")
        if isinstance(raw_slug, str) and raw_slug.strip():
            slug = raw_slug.strip().strip("/")
        else:
            slug = path.stem.strip().strip("/")

        if not slug:
            raise BuildError(f"Invalid empty slug for content file: {path}")

        # Home page is special only inside pages/
        if section_key == "pages" and slug == "index":
            slug = "home"

        return slug

    def _resolve_title(self, frontmatter: Dict[str, Any], markdown_body: str, slug: str) -> str:
        if isinstance(frontmatter.get("title"), str) and frontmatter["title"].strip():
            return frontmatter["title"].strip()

        match = re.search(r"^\s*#\s+(.+?)\s*$", markdown_body, flags=re.MULTILINE)
        if match:
            return match.group(1).strip()

        return self._humanize_slug(slug)

    def _resolve_description(
        self,
        frontmatter: Dict[str, Any],
        markdown_body: str,
        title: str,
    ) -> str:
        if isinstance(frontmatter.get("description"), str) and frontmatter["description"].strip():
            return frontmatter["description"].strip()

        first_paragraph = self._extract_first_paragraph(markdown_body)
        if first_paragraph:
            return truncate_text(first_paragraph, 180)

        return truncate_text(title, 180)

    def _normalize_content_payload(
        self,
        content_type: str,
        title: str,
        description: str,
        markdown_body: str,
        html_body: str,
        frontmatter: Dict[str, Any],
    ) -> Dict[str, Any]:
        intro = frontmatter.get("intro")
        if not isinstance(intro, str) or not intro.strip():
            intro = self._extract_first_paragraph(markdown_body) or description

        headline = frontmatter.get("headline")
        if not isinstance(headline, str) or not headline.strip():
            headline = title

        eyebrow = frontmatter.get("eyebrow")
        if not isinstance(eyebrow, str) or not eyebrow.strip():
            eyebrow = self._default_eyebrow(content_type)

        highlights = frontmatter.get("highlights", [])
        if not isinstance(highlights, list):
            highlights = []

        normalized_highlights = [
            item.strip()
            for item in highlights
            if isinstance(item, str) and item.strip()
        ]

        sections = frontmatter.get("sections", [])
        normalized_sections: List[Dict[str, str]] = []
        if isinstance(sections, list):
            for section in sections:
                if (
                    isinstance(section, dict)
                    and isinstance(section.get("heading"), str)
                    and section["heading"].strip()
                    and isinstance(section.get("body"), str)
                    and section["body"].strip()
                ):
                    normalized_sections.append(
                        {
                            "heading": section["heading"].strip(),
                            "body": section["body"].strip(),
                        }
                    )

        summary = frontmatter.get("summary", "")
        if not isinstance(summary, str):
            summary = ""

        return {
            "eyebrow": eyebrow,
            "headline": headline,
            "intro": intro.strip(),
            "highlights": normalized_highlights,
            "sections": normalized_sections,
            "summary": summary.strip(),
            "body": html_body,
        }

    def _resolve_url_path(self, section_key: str, slug: str, route_prefix: str) -> str:
        if section_key == "pages":
            if slug == "home":
                return "/"
            return f"/{slug}/"

        return f"{route_prefix}/{slug}/"

    def _render_markdown(self, markdown_body: str) -> str:
        self.markdown.reset()
        return self.markdown.convert(markdown_body)

    def _extract_first_paragraph(self, markdown_body: str) -> str:
        cleaned = markdown_body.strip()
        if not cleaned:
            return ""

        paragraphs = re.split(r"\n\s*\n", cleaned)
        for paragraph in paragraphs:
            candidate = paragraph.strip()

            # Ignore markdown headings, list markers, code fences
            if not candidate:
                continue
            if candidate.startswith("#"):
                continue
            if candidate.startswith("```"):
                continue
            if re.match(r"^[-*]\s+", candidate):
                continue

            candidate = re.sub(r"(.*?)(.*?)", r"\1", candidate)
            candidate = re.sub(r"[`*_>#]", "", candidate)
            candidate = re.sub(r"\s+", " ", candidate).strip()

            if candidate:
                return candidate

        return ""

    def _humanize_slug(self, slug: str) -> str:
        return re.sub(r"[-_]+", " ", slug).strip().title()

    def _default_eyebrow(self, content_type: str) -> str:
        mapping = {
            "page": "Institutional Layer",
            "article": "Article",
            "chronicle": "Chronicle",
            "guide": "Guide",
            "tool": "Strategic Tool",
        }
        return mapping.get(content_type, "Page")

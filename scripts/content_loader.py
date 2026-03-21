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
        "Add it to requirements.txt as: markdown==3.7"
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
            "default_template": "page.html",
        },
        "articles": {
            "dir": "articles",
            "content_type": "article",
            "schema_type": "Article",
            "route_prefix": "/articles",
            "default_template": "article.html",
        },
        "chronicles": {
            "dir": "chronicles",
            "content_type": "chronicle",
            "schema_type": "Article",
            "route_prefix": "/chronicles",
            "default_template": "chronicle.html",
        },
        "cities": {
            "dir": "cities",
            "content_type": "city",
            "schema_type": "WebPage",
            "route_prefix": "/framework",
            "default_template": "city.html",
        },
        "guides": {
            "dir": "guides",
            "content_type": "guide",
            "schema_type": "Article",
            "route_prefix": "/guide",
            "default_template": "guide.html",
        },
        "tools": {
            "dir": "tools",
            "content_type": "tool",
            "schema_type": "WebPage",
            "route_prefix": "/tools",
            "default_template": "tool.html",
        },
    }

    # FIX 1: Extensions defined once as a class-level constant.
    # _render_markdown now creates a fresh Markdown instance per call,
    # which guarantees correct TOC state and avoids stale extension state
    # between documents (md_lib.Markdown.reset() does not fully reset
    # the toc extension in all library versions).
    _MARKDOWN_EXTENSIONS: List[str] = [
        "extra",
        "tables",
        "fenced_code",
        "toc",
        "sane_lists",
    ]

    def __init__(self, data_dir: Path, logger: Logger) -> None:
        self.data_dir = Path(data_dir)
        self.logger = logger
        self.root_dir = self.data_dir.parent
        self.content_dir = self.root_dir / "content"

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

    def _validate_nav_items(
        self, items: List[Dict[str, Any]], bucket: str
    ) -> List[Dict[str, Any]]:
        validated: List[Dict[str, Any]] = []

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise BuildError(
                    f"navigation.json {bucket}[{index}] must be an object"
                )

            title = item.get("title")
            url = item.get("url")

            if not isinstance(title, str) or not title.strip():
                raise BuildError(
                    f"navigation.json {bucket}[{index}] missing valid title"
                )
            if not isinstance(url, str) or not url.strip():
                raise BuildError(
                    f"navigation.json {bucket}[{index}] missing valid url"
                )

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
                  "cities": [...],
                  "guides": [...],
                  "tools": [...]
              }
            }

        Note on subdirectory behaviour:
            _load_markdown_collection uses rglob("*.md"), which descends into
            subdirectories. This is intentional — nested organisation is supported.
            Any file you do not want published must be excluded by prefixing its
            name with an underscore (e.g. _draft.md), which is filtered out below.
        """
        if not self.content_dir.exists():
            raise BuildError(f"Content directory missing: {self.content_dir}")

        collections: Dict[str, List[Dict[str, Any]]] = {
            "pages": [],
            "articles": [],
            "chronicles": [],
            "cities": [],
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
                default_template=spec["default_template"],
                seen_paths=seen_paths,
            )
            collections[key] = nodes

        home_node = self._extract_home_node(collections["pages"])

        if home_node is None:
            home_node = self._build_synthetic_home_node()

        collections["pages"] = [
            node for node in collections["pages"] if node["slug"] != "home"
        ]

        return {
            "home": home_node,
            "collections": collections,
        }

    def _extract_home_node(
        self, pages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for node in pages:
            if node["slug"] == "home":
                return {
                    **node,
                    "is_home": True,
                    "is_index": True,
                    "url_path": "/",
                    "template": "home.html",
                }
        return None

    def _build_synthetic_home_node(self) -> Dict[str, Any]:
        self.logger.warning(
            "content/pages/home.md not found; generating synthetic home node"
        )

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
                "intro": (
                    "A sovereign-grade interface for commodity systems, "
                    "infrastructure, and strategic interpretation."
                ),
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
        default_template: str,
        seen_paths: set[str],
    ) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []

        # FIX 2: Files whose name starts with underscore are treated as drafts
        # and excluded from the build. rglob descends into all subdirectories
        # intentionally — see load_content_map docstring.
        markdown_files = sorted(
            f for f in section_dir.rglob("*.md")
            if not f.name.startswith("_")
        )

        if not markdown_files:
            return nodes

        for path in markdown_files:
            node = self._build_node_from_markdown(
                path=path,
                section_key=section_key,
                content_type=content_type,
                schema_type=schema_type,
                route_prefix=route_prefix,
                default_template=default_template,
            )

            if node["url_path"] in seen_paths:
                raise BuildError(
                    f"Duplicate route detected: {node['url_path']} "
                    f"(source: {node['source_path']})"
                )
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
        default_template: str,
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
            path=path,
        )

        url_path = self._resolve_url_path(section_key, slug, route_prefix)
        template_name = self._resolve_template(
            frontmatter, default_template, section_key, slug
        )

        node: Dict[str, Any] = {
            "slug": slug,
            "url_path": url_path,
            "title": title,
            "description": description,
            "content_type": content_type,
            "template": template_name,
            "source_path": str(path.relative_to(self.root_dir)).replace("\\", "/"),
            "is_home": section_key == "pages" and slug == "home",
            "is_index": section_key == "pages" and slug == "home",
            "section": section_key,
            "order": int(frontmatter.get("order", 0) or 0),
            "date": frontmatter.get("date"),
            "updated_at": frontmatter.get("updated_at"),
            "tags": (
                frontmatter.get("tags", [])
                if isinstance(frontmatter.get("tags"), list)
                else []
            ),
            "schema_type": frontmatter.get("schema_type", schema_type),
            "content": content_payload,
        }

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

    def _resolve_slug(
        self, path: Path, frontmatter: Dict[str, Any], section_key: str
    ) -> str:
        raw_slug = frontmatter.get("slug")
        if isinstance(raw_slug, str) and raw_slug.strip():
            slug = raw_slug.strip().strip("/")
        else:
            slug = path.stem.strip().strip("/")

        if not slug:
            raise BuildError(f"Invalid empty slug for content file: {path}")

        # FIX 3: Nested slugs (e.g. "energy/crude-oil") are supported at the
        # slug resolution level. _resolve_url_path will incorporate them
        # correctly. Templates and routing are flat by design — if nested
        # routing is needed in the future, extend _resolve_url_path only.
        if section_key == "pages" and slug == "index":
            slug = "home"

        return slug

    def _resolve_title(
        self, frontmatter: Dict[str, Any], markdown_body: str, slug: str
    ) -> str:
        if (
            isinstance(frontmatter.get("title"), str)
            and frontmatter["title"].strip()
        ):
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
        if (
            isinstance(frontmatter.get("description"), str)
            and frontmatter["description"].strip()
        ):
            return frontmatter["description"].strip()

        first_paragraph = self._extract_first_paragraph(markdown_body)
        if first_paragraph:
            return truncate_text(first_paragraph, 180)

        return truncate_text(title, 180)

    def _resolve_template(
        self,
        frontmatter: Dict[str, Any],
        default_template: str,
        section_key: str,
        slug: str,
    ) -> str:
        if section_key == "pages" and slug == "home":
            return "home.html"

        candidate = frontmatter.get("template")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

        return default_template

    def _normalize_content_payload(
        self,
        content_type: str,
        title: str,
        description: str,
        markdown_body: str,
        html_body: str,
        frontmatter: Dict[str, Any],
        path: Path,
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
        if highlights and not isinstance(highlights, list):
            raise BuildError(f"'highlights' must be a list in {path}")

        normalized_highlights = [
            item.strip()
            for item in highlights
            if isinstance(item, str) and item.strip()
        ]

        sections = frontmatter.get("sections", [])
        if sections and not isinstance(sections, list):
            raise BuildError(f"'sections' must be a list in {path}")

        normalized_sections: List[Dict[str, str]] = []
        if isinstance(sections, list):
            for index, section in enumerate(sections):
                if not isinstance(section, dict):
                    raise BuildError(
                        f"Section {index} must be an object in {path}"
                    )

                heading = section.get("heading")
                body = section.get("body")

                if not isinstance(heading, str) or not heading.strip():
                    raise BuildError(
                        f"Section {index} missing heading in {path}"
                    )
                if not isinstance(body, str) or not body.strip():
                    raise BuildError(
                        f"Section {index} missing body in {path}"
                    )

                normalized_sections.append(
                    {
                        "heading": heading.strip(),
                        "body": body.strip(),
                    }
                )

        summary = frontmatter.get("summary", "")
        if summary and not isinstance(summary, str):
            raise BuildError(f"'summary' must be a string in {path}")

        return {
            "eyebrow": eyebrow,
            "headline": headline,
            "intro": intro.strip(),
            "highlights": normalized_highlights,
            "sections": normalized_sections,
            "summary": summary.strip() if isinstance(summary, str) else "",
            "body": html_body,
        }

    def _resolve_url_path(
        self, section_key: str, slug: str, route_prefix: str
    ) -> str:
        if section_key == "pages":
            if slug == "home":
                return "/"
            return f"/{slug}/"

        return f"{route_prefix}/{slug}/"

    def _render_markdown(self, markdown_body: str) -> str:
        # FIX 1: Fresh instance per call. Avoids stale TOC state and any
        # extension side-effects that md_lib.Markdown.reset() does not
        # fully clear across all supported library versions.
        processor = md_lib.Markdown(extensions=self._MARKDOWN_EXTENSIONS)
        return processor.convert(markdown_body)

    def _extract_first_paragraph(self, markdown_body: str) -> str:
        cleaned = markdown_body.strip()
        if not cleaned:
            return ""

        paragraphs = re.split(r"\n\s*\n", cleaned)
        for paragraph in paragraphs:
            candidate = paragraph.strip()

            if not candidate:
                continue
            if candidate.startswith("#"):
                continue
            if candidate.startswith("```"):
                continue
            if re.match(r"^[-*]\s+", candidate):
                continue

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
            "city": "Strategic Node",
            "guide": "Guide",
            "tool": "Strategic Tool",
        }
        return mapping.get(content_type, "Page")

"""
Data-driven page generator.

Generates sovereign reference pages directly from structured JSON data:
  - /glossary/{slug}/      from data/glossary.json
  - /commodities/{slug}/   from data/commodities.json
  - /nodes/{slug}/         from data/nodes.json

This module extends the static build without requiring individual markdown
files for programmatically generated reference content. Each generated page
is a full, canonical, SEO-optimized HTML document.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .utils import BuildError, Logger, read_json, write_file


class DataPageGenerator:
    """
    Generate reference pages from structured JSON data.

    Maintains the same node contract as the markdown content loader,
    ensuring generated pages are indistinguishable from editorial content
    in quality, structure, and SEO properties.
    """

    def __init__(
        self,
        data_dir: Path,
        templates_dir: Path,
        dist_dir: Path,
        logger: Logger,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.templates_dir = Path(templates_dir)
        self.dist_dir = Path(dist_dir)
        self.logger = logger

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.globals["now"] = datetime.utcnow

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def generate_all(
        self,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
    ) -> List[Dict[str, Any]]:
        """Generate all data-driven pages. Returns list of page metadata."""
        pages: List[Dict[str, Any]] = []

        pages.extend(self._generate_glossary_pages(site_data, navigation, environment))
        pages.extend(self._generate_commodity_pages(site_data, navigation, environment))
        pages.extend(self._generate_node_pages(site_data, navigation, environment))

        self.logger.info(f"Data-driven pages generated: {len(pages)}")
        return pages

    # ──────────────────────────────────────────────────────────────────────
    # Glossary term pages
    # ──────────────────────────────────────────────────────────────────────

    def _generate_glossary_pages(
        self,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
    ) -> List[Dict[str, Any]]:
        glossary_file = self.data_dir / "glossary.json"
        if not glossary_file.exists():
            self.logger.warning("data/glossary.json not found; skipping glossary generation")
            return []

        try:
            terms = read_json(glossary_file)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Invalid JSON in glossary.json: {exc}") from exc

        if not isinstance(terms, list):
            raise BuildError("glossary.json must be a JSON array")

        pages: List[Dict[str, Any]] = []
        for term in terms:
            if not isinstance(term, dict):
                continue
            slug = str(term.get("slug", "")).strip()
            if not slug:
                continue
            page = self._render_term_page(term, site_data, navigation, environment)
            if page:
                pages.append(page)

        self.logger.info(f"Glossary pages: {len(pages)}")
        return pages

    def _render_term_page(
        self,
        term: Dict[str, Any],
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
    ) -> Dict[str, Any] | None:
        slug = str(term.get("slug", "")).strip()
        name = str(term.get("term", slug)).strip()
        definition = str(term.get("definition", "")).strip()
        category = str(term.get("category", "general")).strip()
        tier = str(term.get("tier", "secondary")).strip()
        related = term.get("related_terms", [])
        related_nodes = term.get("related_nodes", [])
        visual_assets = term.get("visual_assets", [])
        platform_context = str(term.get("platform_context", "")).strip()

        url_path = f"/glossary/{slug}/"
        base = site_data["url"].rstrip("/")
        canonical = f"{base}{url_path}"

        description = definition[:180] + ("..." if len(definition) > 180 else "")

        schema = self._build_term_schema(name, definition, url_path, site_data)

        context = {
            "site": site_data,
            "navigation": navigation,
            "environment": environment,
            "is_production": environment == "production",
            "page": {
                "title": name,
                "description": description,
                "canonical": canonical,
                "slug": slug,
                "is_home": False,
                "url_path": url_path,
                "schema": schema,
                "content": {},
            },
            "term": {
                "slug": slug,
                "name": name,
                "definition": definition,
                "category": category,
                "tier": tier,
                "related_terms": related if isinstance(related, list) else [],
                "related_nodes": related_nodes if isinstance(related_nodes, list) else [],
                "visual_assets": visual_assets if isinstance(visual_assets, list) else [],
                "platform_context": platform_context,
            },
        }

        output_path = self.dist_dir / "glossary" / slug / "index.html"
        return self._render_to_path("term.html", output_path, context, slug, name, url_path)

    # ──────────────────────────────────────────────────────────────────────
    # Commodity profile pages
    # ──────────────────────────────────────────────────────────────────────

    def _generate_commodity_pages(
        self,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
    ) -> List[Dict[str, Any]]:
        comm_file = self.data_dir / "commodities.json"
        if not comm_file.exists():
            self.logger.warning("data/commodities.json not found; skipping commodity pages")
            return []

        try:
            commodities = read_json(comm_file)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Invalid JSON in commodities.json: {exc}") from exc

        if not isinstance(commodities, list):
            raise BuildError("commodities.json must be a JSON array")

        pages: List[Dict[str, Any]] = []
        for commodity in commodities:
            if not isinstance(commodity, dict):
                continue
            slug = str(commodity.get("slug", "")).strip()
            if not slug:
                continue
            page = self._render_commodity_page(commodity, site_data, navigation, environment)
            if page:
                pages.append(page)

        self.logger.info(f"Commodity pages: {len(pages)}")
        return pages

    def _render_commodity_page(
        self,
        commodity: Dict[str, Any],
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
    ) -> Dict[str, Any] | None:
        slug = str(commodity.get("slug", "")).strip()
        name = str(commodity.get("name", slug)).strip()
        short_name = str(commodity.get("short_name", name)).strip()
        category = str(commodity.get("category", "")).strip()
        narrative = str(commodity.get("narrative_angle", "")).strip()
        system_role = str(commodity.get("system_role", "")).strip()
        relevance = str(commodity.get("relevance_to_singapore", "")).strip()
        sg_function = str(commodity.get("singapore_function", "")).strip()
        key_markets = commodity.get("key_markets", [])
        unit = str(commodity.get("unit", "")).strip()

        url_path = f"/commodities/{slug}/"
        base = site_data["url"].rstrip("/")
        canonical = f"{base}{url_path}"

        description = (
            narrative[:180] + ("..." if len(narrative) > 180 else "")
            if narrative
            else f"Singapore's role in {name} markets: coordination, routing, and strategic intelligence."
        )

        schema = self._build_commodity_schema(name, description, url_path, site_data)

        context = {
            "site": site_data,
            "navigation": navigation,
            "environment": environment,
            "is_production": environment == "production",
            "page": {
                "title": f"{name} — Singapore's Strategic Role",
                "description": description,
                "canonical": canonical,
                "slug": slug,
                "is_home": False,
                "url_path": url_path,
                "schema": schema,
                "content": {},
            },
            "commodity": {
                "slug": slug,
                "name": name,
                "short_name": short_name,
                "category": category,
                "narrative": narrative,
                "system_role": system_role,
                "relevance": relevance,
                "singapore_function": sg_function,
                "key_markets": key_markets if isinstance(key_markets, list) else [],
                "unit": unit,
            },
        }

        output_path = self.dist_dir / "commodities" / slug / "index.html"
        return self._render_to_path(
            "commodity.html", output_path, context,
            slug, f"{name} — Singapore's Strategic Role", url_path
        )

    # ──────────────────────────────────────────────────────────────────────
    # Node profile pages
    # ──────────────────────────────────────────────────────────────────────

    def _generate_node_pages(
        self,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
    ) -> List[Dict[str, Any]]:
        nodes_file = self.data_dir / "nodes.json"
        if not nodes_file.exists():
            self.logger.warning("data/nodes.json not found; skipping node pages")
            return []

        try:
            nodes = read_json(nodes_file)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Invalid JSON in nodes.json: {exc}") from exc

        if not isinstance(nodes, list):
            raise BuildError("nodes.json must be a JSON array")

        pages: List[Dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            slug = str(node.get("slug", "")).strip()
            if not slug:
                continue
            page = self._render_node_page(node, site_data, navigation, environment)
            if page:
                pages.append(page)

        self.logger.info(f"Node profile pages: {len(pages)}")
        return pages

    def _render_node_page(
        self,
        node: Dict[str, Any],
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
    ) -> Dict[str, Any] | None:
        slug = str(node.get("slug", "")).strip()
        name = str(node.get("name", slug)).strip()
        layer = str(node.get("layer", "")).strip()
        tagline = str(node.get("tagline", "")).strip()
        narrative = str(node.get("narrative", "")).strip()
        primary_function = str(node.get("primary_function", "")).strip()
        region = str(node.get("region", "")).strip()
        power_scores = node.get("power_scores", {})
        key_commodities = node.get("key_commodities", [])
        key_institutions = node.get("key_institutions", [])
        key_benchmarks = node.get("key_benchmarks", [])
        related_terms = node.get("related_terms", [])
        related_nodes = node.get("related_nodes", [])
        visual_assets = node.get("visual_assets", [])

        url_path = f"/nodes/{slug}/"
        base = site_data["url"].rstrip("/")
        canonical = f"{base}{url_path}"

        description = (
            f"{name} is a {layer} node in the global commodity system. {narrative[:120]}..."
            if narrative
            else f"{name}: {primary_function}. Strategic commodity node analysis."
        )

        # Compute composite score
        if power_scores and isinstance(power_scores, dict):
            total = sum(v for v in power_scores.values() if isinstance(v, (int, float)))
            max_score = len(power_scores) * 10
            composite = round((total / max_score) * 100) if max_score > 0 else 0
        else:
            composite = 0

        schema = self._build_node_schema(name, description, url_path, site_data)

        context = {
            "site": site_data,
            "navigation": navigation,
            "environment": environment,
            "is_production": environment == "production",
            "page": {
                "title": f"{name} — {layer} Node",
                "description": description,
                "canonical": canonical,
                "slug": slug,
                "is_home": False,
                "url_path": url_path,
                "schema": schema,
                "content": {},
            },
            "node": {
                "slug": slug,
                "name": name,
                "layer": layer,
                "tagline": tagline,
                "narrative": narrative,
                "primary_function": primary_function,
                "region": region,
                "power_scores": power_scores,
                "composite_score": composite,
                "key_commodities": key_commodities if isinstance(key_commodities, list) else [],
                "key_institutions": key_institutions if isinstance(key_institutions, list) else [],
                "key_benchmarks": key_benchmarks if isinstance(key_benchmarks, list) else [],
                "related_terms": related_terms if isinstance(related_terms, list) else [],
                "related_nodes": related_nodes if isinstance(related_nodes, list) else [],
                "visual_assets": visual_assets if isinstance(visual_assets, list) else [],
            },
        }

        output_path = self.dist_dir / "nodes" / slug / "index.html"
        return self._render_to_path(
            "node_profile.html", output_path, context,
            slug, f"{name} — {layer} Node", url_path
        )

    # ──────────────────────────────────────────────────────────────────────
    # Schema helpers
    # ──────────────────────────────────────────────────────────────────────

    def _build_term_schema(
        self,
        name: str,
        definition: str,
        url_path: str,
        site_data: Dict[str, Any],
    ) -> str:
        base = site_data["url"].rstrip("/")
        schema = {
            "@context": "https://schema.org",
            "@type": "DefinedTerm",
            "name": name,
            "description": definition[:200],
            "url": f"{base}{url_path}",
            "inDefinedTermSet": {
                "@type": "DefinedTermSet",
                "name": f"{site_data['name']} Commodity Intelligence Glossary",
                "url": f"{base}/glossary/"
            }
        }
        return json.dumps(schema, indent=2, ensure_ascii=False)

    def _build_commodity_schema(
        self,
        name: str,
        description: str,
        url_path: str,
        site_data: Dict[str, Any],
    ) -> str:
        base = site_data["url"].rstrip("/")
        schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": f"{name} — Singapore's Strategic Role",
            "description": description,
            "url": f"{base}{url_path}",
            "isPartOf": {"@type": "WebSite", "url": base}
        }
        return json.dumps(schema, indent=2, ensure_ascii=False)

    def _build_node_schema(
        self,
        name: str,
        description: str,
        url_path: str,
        site_data: Dict[str, Any],
    ) -> str:
        base = site_data["url"].rstrip("/")
        schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": f"{name} — Commodity Node Profile",
            "description": description,
            "url": f"{base}{url_path}",
            "isPartOf": {"@type": "WebSite", "url": base}
        }
        return json.dumps(schema, indent=2, ensure_ascii=False)

    # ──────────────────────────────────────────────────────────────────────
    # Rendering helper
    # ──────────────────────────────────────────────────────────────────────

    def _render_to_path(
        self,
        template_name: str,
        output_path: Path,
        context: Dict[str, Any],
        slug: str,
        title: str,
        url_path: str,
    ) -> Dict[str, Any] | None:
        try:
            template = self.env.get_template(template_name)
        except Exception as exc:
            self.logger.warning(f"Template not found: {template_name} — skipping ({exc})")
            return None

        html = template.render(**context)
        write_file(output_path, html)
        self.logger.info(f"Data page: {template_name} → {output_path}")

        return {
            "slug": slug,
            "title": title,
            "path": str(output_path.relative_to(self.dist_dir)),
            "url_path": url_path,
            "template": template_name,
        }

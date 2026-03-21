"""
Page rendering engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .utils import BuildError, Logger, write_file


class PageRenderer:
    """Render HTML pages from Jinja templates."""

    def __init__(self, templates_dir: Path, dist_dir: Path, logger: Logger) -> None:
        self.templates_dir = Path(templates_dir)
        self.dist_dir = Path(dist_dir)
        self.logger = logger

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.env.globals["now"] = lambda: datetime.now(timezone.utc)
        self.env.filters["rstrip_slash"] = lambda value: value.rstrip("/") if isinstance(value, str) else value

    def render_all(
        self,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        content_map: Dict[str, Any],
        environment: str,
        schema_generator: Any,
    ) -> List[Dict[str, Any]]:
        generated_pages: List[Dict[str, Any]] = []

        home_node = content_map["home"]
        collections = content_map["collections"]

        generated_pages.append(
            self._render_node(
                node=home_node,
                output_path=self.dist_dir / "index.html",
                site_data=site_data,
                navigation=navigation,
                environment=environment,
                schema=schema_generator.generate_homepage(site_data),
            )
        )

        for collection_name in ("pages", "articles", "chronicles", "cities", "guides", "tools"):
            nodes = collections.get(collection_name, [])
            if not isinstance(nodes, list):
                raise BuildError(f"Invalid collection: {collection_name}")

            for node in nodes:
                output_path = self._resolve_output_path(node)
                generated_pages.append(
                    self._render_node(
                        node=node,
                        output_path=output_path,
                        site_data=site_data,
                        navigation=navigation,
                        environment=environment,
                        schema=self._generate_schema_for_node(
                            node=node,
                            site_data=site_data,
                            schema_generator=schema_generator,
                        ),
                    )
                )

        return generated_pages

    def render_error_pages(self, site_data: Dict[str, Any], environment: str) -> None:
        error_pages = [
            (404, "Page not found"),
            (500, "Internal server error"),
        ]

        for status_code, message in error_pages:
            context = {
                "site": site_data,
                "navigation": {"main": [], "footer": []},
                "environment": environment,
                "is_production": environment == "production",
                "page": {
                    "title": str(status_code),
                    "description": message,
                    "canonical": f"{site_data['url'].rstrip('/')}/{status_code}.html",
                    "slug": str(status_code),
                    "is_home": False,
                    "url_path": f"/{status_code}.html",
                    "schema": "",
                    "content": {},
                },
                "error": {
                    "code": status_code,
                    "title": message,
                    "message": message,
                },
            }

            self._render_template_to_path(
                template_name="error.html",
                output_path=self.dist_dir / f"{status_code}.html",
                context=context,
                metadata=False,
            )

    def _render_node(
        self,
        node: Dict[str, Any],
        output_path: Path,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
        schema: str,
    ) -> Dict[str, Any]:
        url_path = node["url_path"]
        canonical = f"{site_data['url'].rstrip('/')}{url_path}"

        context = {
            "site": site_data,
            "navigation": navigation,
            "environment": environment,
            "is_production": environment == "production",
            "page": {
                "title": node["title"],
                "description": node["description"],
                "canonical": canonical,
                "slug": "index" if node.get("is_home") else node["slug"],
                "is_home": bool(node.get("is_home", False)),
                "url_path": url_path,
                "schema": schema,
                "content": node.get("content", {}),
            },
        }

        return self._render_template_to_path(
            template_name=node.get("template", "page.html"),
            output_path=output_path,
            context=context,
        )

    def _resolve_output_path(self, node: Dict[str, Any]) -> Path:
        url_path = node["url_path"].strip("/")
        if not url_path:
            return self.dist_dir / "index.html"
        return self.dist_dir / url_path / "index.html"

    def _generate_schema_for_node(
        self,
        node: Dict[str, Any],
        site_data: Dict[str, Any],
        schema_generator: Any,
    ) -> str:
        return schema_generator.generate_webpage(node, site_data, node["slug"])

    def _render_template_to_path(
        self,
        template_name: str,
        output_path: Path,
        context: Dict[str, Any],
        metadata: bool = True,
    ) -> Dict[str, Any]:
        try:
            template = self.env.get_template(template_name)
        except Exception as exc:
            raise BuildError(f"Template not found or invalid: {template_name}") from exc

        html = template.render(**context)
        write_file(output_path, html)

        slug = context["page"]["slug"]
        title = context["page"]["title"]
        url_path = context["page"]["url_path"]

        self.logger.info(f"Rendered {template_name} -> {output_path.relative_to(self.dist_dir.parent)}")

        if not metadata:
            return {
                "slug": slug,
                "title": title,
                "path": str(output_path),
                "url_path": url_path,
            }

        return {
            "slug": slug,
            "title": title,
            "path": str(output_path.relative_to(self.dist_dir.parent)).replace("\\", "/"),
            "template": template_name,
            "url_path": url_path,
        }

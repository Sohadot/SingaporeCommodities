from datetime import datetime
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
        self.env.globals["now"] = datetime.utcnow

    def render_all(
        self,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        content_map: Dict[str, Any],
        environment: str,
        schema_generator: Any,
    ) -> List[Dict[str, Any]]:
        pages: List[Dict[str, Any]] = []

        home_node = content_map["home"]
        collections = content_map["collections"]

        home_schema = schema_generator.generate_homepage(site_data)
        home_output = self._resolve_output_path(home_node["url_path"])

        pages.append(
            self._render_node(
                node=home_node,
                output_path=home_output,
                site_data=site_data,
                navigation=navigation,
                environment=environment,
                schema=home_schema,
            )
        )

        for collection_name in ("pages", "articles", "chronicles", "cities", "guides", "tools"):
            for node in collections.get(collection_name, []):
                schema = schema_generator.generate_webpage(node, site_data, node["slug"])
                output_path = self._resolve_output_path(node["url_path"])

                pages.append(
                    self._render_node(
                        node=node,
                        output_path=output_path,
                        site_data=site_data,
                        navigation=navigation,
                        environment=environment,
                        schema=schema,
                    )
                )

        return pages

    def render_error_pages(
    self,
    site_data: Dict[str, Any],
    navigation: Dict[str, Any],
    environment: str
) -> None:
    errors = [
        {
            "code": 404,
            "title": "Page Not Found",
            "message": "The page you requested could not be found.",
        },
        {
            "code": 500,
            "title": "Internal Server Error",
            "message": "An internal server error occurred.",
        },
    ]

    for error in errors:
        context = {
            "site": site_data,
            "navigation": navigation,
            "environment": environment,
            "is_production": environment == "production",
            "page": {
                "title": f"{error['code']}",
                "description": error["message"],
                "canonical": f"{site_data['url'].rstrip('/')}/{error['code']}.html",
                "slug": str(error["code"]),
                "is_home": False,
                "url_path": f"/{error['code']}.html",
                "schema": "",
                "content": {},
            },
            "error": error,
        }

        self._render_template_to_path(
            template_name="error.html",
            output_path=self.dist_dir / f"{error['code']}.html",
            context=context,
        )

    def _resolve_output_path(self, url_path: str) -> Path:
        if url_path == "/":
            return self.dist_dir / "index.html"

        clean_path = url_path.strip("/")
        return self.dist_dir / clean_path / "index.html"

    def _render_node(
        self,
        node: Dict[str, Any],
        output_path: Path,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
        schema: str,
    ) -> Dict[str, Any]:
        required_fields = ("title", "description", "url_path", "template")
        for field in required_fields:
            if field not in node:
                raise BuildError(f"Node missing required field '{field}': {node.get('source_path')}")

        url_path = node["url_path"]

        if not isinstance(url_path, str) or not url_path.startswith("/"):
            raise BuildError(f"Invalid url_path: {url_path}")

        base = site_data["url"].rstrip("/")
        normalized_path = url_path if url_path == "/" else url_path.rstrip("/") + "/"
        canonical = f"{base}{normalized_path}"

        if not isinstance(schema, str):
            schema = ""

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
                "url_path": normalized_path,
                "schema": schema,
                "content": node.get("content", {}),
            },
        }

        template_name = node.get("template", "page.html")

        try:
            self.env.get_template(template_name)
        except Exception as exc:
            raise BuildError(f"Template not found: {template_name}") from exc

        return self._render_template_to_path(
            template_name=template_name,
            output_path=output_path,
            context=context,
        )

    def _render_template_to_path(
        self,
        template_name: str,
        output_path: Path,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        template = self.env.get_template(template_name)
        html = template.render(**context)
        write_file(output_path, html)

        self.logger.info(f"Rendered {template_name} -> {output_path}")

        return {
            "slug": context["page"]["slug"],
            "title": context["page"]["title"],
            "path": str(output_path.relative_to(self.dist_dir)),
            "url_path": context["page"]["url_path"],
            "template": template_name,
        }

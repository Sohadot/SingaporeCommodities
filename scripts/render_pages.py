class PageRenderer:
    """Render HTML pages from Jinja templates."""

    ...

    def _render_node(
        self,
        node: Dict[str, Any],
        output_path: Path,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        environment: str,
        schema: str,
    ) -> Dict[str, Any]:

        # --------------------------------------------------
        # HARDENING: node contract validation
        # --------------------------------------------------
        required_fields = ("title", "description", "url_path", "template")
        for field in required_fields:
            if field not in node:
                raise BuildError(f"Node missing required field '{field}': {node.get('source_path')}")

        url_path = node["url_path"]

        if not isinstance(url_path, str) or not url_path.startswith("/"):
            raise BuildError(f"Invalid url_path: {url_path}")

        # --------------------------------------------------
        # HARDENING: canonical normalization
        # --------------------------------------------------
        base = site_data["url"].rstrip("/")
        normalized_path = url_path if url_path == "/" else url_path.rstrip("/") + "/"
        canonical = f"{base}{normalized_path}"

        # --------------------------------------------------
        # HARDENING: schema safety
        # --------------------------------------------------
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

        # --------------------------------------------------
        # HARDENING: template existence check
        # --------------------------------------------------
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

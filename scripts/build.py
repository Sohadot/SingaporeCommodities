#!/usr/bin/env python3
"""
SingaporeCommodities.com build system.
Deterministic static build for Cloudflare Pages.

This version preserves the current architecture while hardening execution
against contract drift, missing institutional routes, and weak build summaries.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from scripts.content_loader import ContentLoader
from scripts.copy_assets import AssetCopier
from scripts.generate_robots import RobotsGenerator
from scripts.generate_rss import RSSGenerator
from scripts.generate_schema import SchemaGenerator
from scripts.generate_sitemap import SitemapGenerator
from scripts.render_pages import PageRenderer
from scripts.utils import BuildError, Logger, write_file
from scripts.validate_dist import DistValidator


class BuildSystem:
    """Main build orchestrator with strict contract enforcement."""

    REQUIRED_COLLECTIONS: tuple[str, ...] = (
        "pages",
        "articles",
        "chronicles",
        "cities",
        "guides",
        "tools",
    )

    def __init__(self, environment: str = "production", version: str = "1.0.0") -> None:
        self.environment = environment
        self.version = version
        self.is_production = environment == "production"

        # IMPORTANT:
        # __file__ = <project_root>/scripts/build.py
        # parent     = <project_root>/scripts
        # parent.parent = <project_root>
        self.root_dir = Path(__file__).resolve().parent.parent
        self.dist_dir = self.root_dir / "dist"
        self.assets_dir = self.root_dir / "assets"
        self.static_dir = self.root_dir / "static"
        self.data_dir = self.root_dir / "data"
        self.templates_dir = self.root_dir / "templates"
        self.config_dir = self.root_dir / "config"

        self.logger = Logger()
        self.content_loader = ContentLoader(self.data_dir, self.logger)
        self.renderer = PageRenderer(self.templates_dir, self.dist_dir, self.logger)
        self.schema_generator = SchemaGenerator()

        self.build_timestamp = datetime.now(timezone.utc)
        self.git_commit = self._get_git_value(["git", "rev-parse", "--short", "HEAD"])
        self.git_branch = self._get_git_value(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    # ------------------------------------------------------------------
    # Environment and filesystem helpers
    # ------------------------------------------------------------------

    def _get_git_value(self, command: List[str]) -> Optional[str]:
        try:
            result = subprocess.run(
                command,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            value = result.stdout.strip()
            return value if result.returncode == 0 and value else None
        except Exception:
            return None

    def clean(self) -> None:
        self.logger.info("Cleaning dist/")
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.dist_dir.mkdir(parents=True, exist_ok=True)

    def load_yaml_config(self, name: str) -> Dict[str, Any]:
        path = self.config_dir / name
        if not path.exists():
            self.logger.warning(f"Optional config file not found: {path}")
            return {}

        try:
            with path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            raise BuildError(f"Invalid YAML in config file {path}: {exc}") from exc

    def prepare_site_context(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        env_config = self.load_yaml_config("environments.yaml").get("environments", {})
        current_env = env_config.get(self.environment, {})

        prepared = dict(site_data)
        prepared["version"] = self.version
        prepared["environment"] = self.environment
        prepared["build_timestamp"] = self.build_timestamp.isoformat()
        prepared["debug"] = bool(current_env.get("debug", False))
        prepared["analytics_enabled"] = bool(current_env.get("analytics", False))
        prepared["indexing_enabled"] = bool(current_env.get("indexing", self.is_production))

        # Canonical doctrine:
        # site.json remains the canonical production domain.
        # Preview builds remain noindex via templates/robots, not via domain mutation.
        return prepared

    # ------------------------------------------------------------------
    # Build execution
    # ------------------------------------------------------------------

    def build(self) -> int:
        started_at = datetime.now(timezone.utc)

        try:
            self.logger.info(f"Starting build: env={self.environment} version={self.version}")

            self.clean()

            site_data = self.prepare_site_context(self.content_loader.load_site_data())
            navigation = self.content_loader.load_navigation()
            content_map = self.content_loader.load_content_map()

            contract_summary = self._validate_build_contract(
                site_data=site_data,
                navigation=navigation,
                content_map=content_map,
            )
            self._log_contract_summary(contract_summary)

            copier = AssetCopier(self.assets_dir, self.static_dir, self.dist_dir, self.logger)
            copied_assets = copier.copy_all()

            generated_pages = self.renderer.render_all(
                site_data=site_data,
                navigation=navigation,
                content_map=content_map,
                environment=self.environment,
                schema_generator=self.schema_generator,
            )
            self.renderer.render_error_pages(
                site_data=site_data,
                navigation=navigation,
                environment=self.environment,
            )

            self._validate_generated_pages_against_contract(
                generated_pages=generated_pages,
                navigation=navigation,
                contract_summary=contract_summary,
            )

            SitemapGenerator(self.dist_dir, site_data, self.logger).generate(generated_pages)
            RobotsGenerator(self.dist_dir, site_data, self.is_production, self.logger).generate()
            RSSGenerator(self.dist_dir, site_data, self.logger).generate(generated_pages)

            self._generate_manifest(
                pages=generated_pages,
                assets=copied_assets,
                started_at=started_at,
                contract_summary=contract_summary,
            )

            validator = DistValidator(self.dist_dir, self.logger)
            if not validator.validate(strict=True):
                raise BuildError("Build validation failed")

            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
            self.logger.success(f"Build completed successfully in {elapsed:.3f}s")
            return 0

        except BuildError as exc:
            self.logger.error(f"Build failed: {exc}")
            return 1
        except Exception as exc:
            import traceback

            self.logger.error(f"Unexpected error: {exc}")
            if not self.is_production:
                self.logger.error(traceback.format_exc())
            return 1

    # ------------------------------------------------------------------
    # Contract enforcement
    # ------------------------------------------------------------------

    def _validate_build_contract(
        self,
        site_data: Dict[str, Any],
        navigation: Dict[str, Any],
        content_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enforce the system doctrine before rendering begins.

        Ensures:
        - valid content_map structure
        - valid home node
        - official collections only
        - meaningful content presence
        - institutional route expectations from navigation
        """
        if not isinstance(content_map, dict):
            raise BuildError("content_map must be a dictionary")

        home = content_map.get("home")
        collections = content_map.get("collections")

        if not isinstance(home, dict):
            raise BuildError("content_map missing valid 'home' node")
        if not isinstance(collections, dict):
            raise BuildError("content_map missing valid 'collections' map")

        missing_collections = [
            name for name in self.REQUIRED_COLLECTIONS if name not in collections
        ]
        if missing_collections:
            raise BuildError(
                f"content_map missing required collections: {', '.join(missing_collections)}"
            )

        unexpected_collections = [
            name for name in collections.keys() if name not in self.REQUIRED_COLLECTIONS
        ]
        if unexpected_collections:
            raise BuildError(
                f"content_map contains unexpected collections: {', '.join(sorted(unexpected_collections))}"
            )

        if not home.get("title") or not home.get("description"):
            raise BuildError("home node missing required title/description")
        if home.get("url_path") != "/":
            raise BuildError("home node must resolve to '/'")
        if home.get("template") != "home.html":
            raise BuildError("home node must use template 'home.html'")

        collection_counts: Dict[str, int] = {}
        total_nodes = 1  # home
        for name in self.REQUIRED_COLLECTIONS:
            nodes = collections.get(name)
            if not isinstance(nodes, list):
                raise BuildError(f"Collection '{name}' must be a list")
            collection_counts[name] = len(nodes)
            total_nodes += len(nodes)

        if total_nodes <= 1:
            raise BuildError("No real content nodes detected beyond home")

        required_navigation_routes = self._extract_required_navigation_routes(navigation)
        home_is_synthetic = str(home.get("source_path", "")).startswith("synthetic:")

        return {
            "home": {
                "title": home.get("title", ""),
                "source_path": home.get("source_path"),
                "is_synthetic": home_is_synthetic,
            },
            "collection_counts": collection_counts,
            "total_nodes": total_nodes,
            "required_navigation_routes": sorted(required_navigation_routes),
            "site_url": site_data.get("url", ""),
        }

    def _extract_required_navigation_routes(
        self,
        navigation: Dict[str, List[Dict[str, Any]]],
    ) -> Set[str]:
        """
        Enforce institutional pages linked in navigation.

        We require every internal navigation target to be renderable.
        External links are ignored.
        """
        required_routes: Set[str] = {"/"}

        for bucket in ("main", "footer"):
            items = navigation.get(bucket, [])
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("external"):
                    continue

                raw_url = item.get("url")
                if not isinstance(raw_url, str) or not raw_url.strip():
                    continue

                url = raw_url.strip()
                if not url.startswith("/"):
                    continue

                normalized = url.rstrip("/") or "/"
                required_routes.add(normalized)

        return required_routes

    def _validate_generated_pages_against_contract(
        self,
        generated_pages: List[Dict[str, Any]],
        navigation: Dict[str, List[Dict[str, Any]]],
        contract_summary: Dict[str, Any],
    ) -> None:
        """
        Post-render contract validation.

        Ensures:
        - at least one generated page exists
        - home exists
        - navigation-linked institutional routes exist
        """
        if not generated_pages:
            raise BuildError("Renderer returned no generated pages")

        generated_routes: Set[str] = set()
        for page in generated_pages:
            path_value = page.get("url_path") or page.get("canonical_path") or ""
            if not isinstance(path_value, str) or not path_value.strip():
                slug = str(page.get("slug", "")).strip("/")
                normalized = "/" if slug in ("", "index") else f"/{slug}"
            else:
                normalized = path_value.rstrip("/") or "/"

            generated_routes.add(normalized)

        missing_routes = [
            route
            for route in contract_summary["required_navigation_routes"]
            if route not in generated_routes
        ]
        if missing_routes:
            raise BuildError(
                "Missing required institutionally-linked routes after render: "
                + ", ".join(missing_routes)
            )

    def _log_contract_summary(self, contract_summary: Dict[str, Any]) -> None:
        collection_counts = contract_summary["collection_counts"]
        counts_str = ", ".join(
            f"{name}={count}"
            for name, count in collection_counts.items()
        )
        self.logger.info(
            f"Content contract: total_nodes={contract_summary['total_nodes']} | {counts_str}"
        )

        if contract_summary["home"]["is_synthetic"]:
            self.logger.warning("Home node is synthetic; content/pages/home.md was not found")
        else:
            self.logger.info(
                f"Home node source: {contract_summary['home'].get('source_path', 'unknown')}"
            )

        self.logger.info(
            "Required institutional routes: "
            + ", ".join(contract_summary["required_navigation_routes"])
        )

    # ------------------------------------------------------------------
    # Manifest generation
    # ------------------------------------------------------------------

    def _generate_manifest(
        self,
        pages: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
        started_at: datetime,
        contract_summary: Dict[str, Any],
    ) -> None:
        manifest = {
            "version": self.version,
            "environment": self.environment,
            "timestamp": self.build_timestamp.isoformat(),
            "duration_seconds": round(
                (datetime.now(timezone.utc) - started_at).total_seconds(),
                6,
            ),
            "git": {
                "commit": self.git_commit,
                "branch": self.git_branch,
            },
            "build": {
                "pages_count": len(pages),
                "assets_count": len(assets),
                "total_asset_bytes": sum(asset.get("size", 0) for asset in assets),
            },
            "contract": {
                "total_nodes": contract_summary["total_nodes"],
                "collection_counts": contract_summary["collection_counts"],
                "required_navigation_routes": contract_summary["required_navigation_routes"],
                "home_is_synthetic": contract_summary["home"]["is_synthetic"],
                "site_url": contract_summary["site_url"],
            },
            "pages": [
                {
                    "slug": page["slug"],
                    "title": page["title"],
                    "path": page["path"],
                    "url_path": page.get("url_path"),
                }
                for page in pages
            ],
            "assets": assets,
        }

        write_file(
            self.dist_dir / "build-manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )

        info = "\n".join(
            [
                "Singapore Commodities Build Information",
                "======================================",
                f"Version: {self.version}",
                f"Environment: {self.environment}",
                f"Timestamp: {self.build_timestamp.isoformat()}",
                f"Git Commit: {self.git_commit or 'unknown'}",
                f"Git Branch: {self.git_branch or 'unknown'}",
                f"Pages: {len(pages)}",
                f"Assets: {len(assets)}",
                f"Home Synthetic: {contract_summary['home']['is_synthetic']}",
                "Collection Counts: "
                + ", ".join(
                    f"{name}={count}"
                    for name, count in contract_summary["collection_counts"].items()
                ),
                "Required Routes: "
                + ", ".join(contract_summary["required_navigation_routes"]),
                "",
            ]
        )
        write_file(self.dist_dir / "BUILD_INFO.txt", info)


def main() -> None:
    parser = argparse.ArgumentParser(description="SingaporeCommodities.com build")
    parser.add_argument(
        "--env",
        choices=["production", "preview", "development"],
        default="production",
        help="Build environment",
    )
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="Build version identifier",
    )
    args = parser.parse_args()

    system = BuildSystem(environment=args.env, version=args.version)
    raise SystemExit(system.build())


if __name__ == "__main__":
    main()

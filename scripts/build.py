#!/usr/bin/env python3
"""
SingaporeCommodities.com build system.

Deterministic sovereign-grade static build for Cloudflare Pages.
This build treats the repository as the source structure of the platform,
keeps content/ as the editorial source of truth, and writes the final
generated surface into dist/ only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Ensure local imports resolve consistently
sys.path.insert(0, str(Path(__file__).parent.resolve()))

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
    """Main deterministic build orchestrator."""

    def __init__(self, environment: str = "production", version: str = "1.0.0") -> None:
        self.environment = environment
        self.version = version
        self.is_production = environment == "production"

        self.root_dir = Path(__file__).parent.resolve()
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
    # Build lifecycle helpers
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
        """Remove previous build output and recreate dist/."""
        self.logger.info("Cleaning dist/")
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.dist_dir.mkdir(parents=True, exist_ok=True)

    def load_yaml_config(self, name: str) -> Dict[str, Any]:
        """Load optional YAML config from config/."""
        path = self.config_dir / name
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def prepare_site_context(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich site.json data with environment-aware values from config/environments.yaml.
        """
        env_config = self.load_yaml_config("environments.yaml").get("environments", {})
        current_env = env_config.get(self.environment, {})

        prepared = dict(site_data)
        prepared["version"] = self.version
        prepared["environment"] = self.environment
        prepared["build_timestamp"] = self.build_timestamp.isoformat()
        prepared["debug"] = bool(current_env.get("debug", False))
        prepared["analytics_enabled"] = bool(current_env.get("analytics", False))
        prepared["indexing_enabled"] = bool(current_env.get("indexing", self.is_production))

        return prepared

    # ------------------------------------------------------------------
    # Main build orchestration
    # ------------------------------------------------------------------

    def build(self) -> int:
        started_at = datetime.now(timezone.utc)

        try:
            self.logger.info(
                f"Starting build: env={self.environment} version={self.version}"
            )

            # 1. Clean output
            self.clean()

            # 2. Load structured site data
            site_data = self.prepare_site_context(self.content_loader.load_site_data())
            navigation = self.content_loader.load_navigation()

            # 3. Load editorial content map from content/
            content_map = self.content_loader.load_content_map()

            # 4. Copy source assets and static files into dist/
            copier = AssetCopier(self.assets_dir, self.static_dir, self.dist_dir, self.logger)
            copied_assets = copier.copy_all()

            # 5. Render all pages
            generated_pages = self.renderer.render_all(
                site_data=site_data,
                navigation=navigation,
                content_map=content_map,
                environment=self.environment,
                schema_generator=self.schema_generator,
            )

            # 6. Render error pages
            self.renderer.render_error_pages(site_data=site_data, environment=self.environment)

            # 7. Generate SEO and feed surfaces
            SitemapGenerator(self.dist_dir, site_data, self.logger).generate(generated_pages)
            RobotsGenerator(self.dist_dir, site_data, self.is_production, self.logger).generate()
            RSSGenerator(self.dist_dir, site_data, self.logger).generate(generated_pages)

            # 8. Generate build manifest
            self._generate_manifest(
                pages=generated_pages,
                assets=copied_assets,
                started_at=started_at,
            )

            # 9. Validate dist/ with strict discipline
            validator = DistValidator(self.dist_dir, self.logger)
            if not validator.validate(strict=True):
                raise BuildError("Build validation failed")

            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
            self.logger.success(f"Build completed successfully in {elapsed:.3f}s")
            self.logger.info(f"Generated pages: {len(generated_pages)}")
            self.logger.info(f"Copied assets: {len(copied_assets)}")
            return 0

        except BuildError as exc:
            self.logger.error(f"Build failed: {exc}")
            return 1
        except Exception as exc:
            self.logger.error(f"Unexpected error: {exc}")
            return 1

    # ------------------------------------------------------------------
    # Build manifest
    # ------------------------------------------------------------------

    def _generate_manifest(
        self,
        pages: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
        started_at: datetime,
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
            "pages": [
                {
                    "slug": page["slug"],
                    "title": page["title"],
                    "path": page["path"],
                    "template": page.get("template", ""),
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

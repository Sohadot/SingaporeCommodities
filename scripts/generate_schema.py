"""
Schema.org JSON-LD generation.
"""

from __future__ import annotations

import json
from typing import Any, Dict


class SchemaGenerator:
    """Generate structured data payloads."""

    def generate_organization(self, site_data: Dict[str, Any]) -> str:
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": site_data.get("name", ""),
            "url": site_data.get("url", ""),
            "description": site_data.get("description", ""),
            "logo": {
                "@type": "ImageObject",
                "url": f"{site_data.get('url', '').rstrip('/')}{site_data.get('logo', '')}",
            }
            if site_data.get("logo")
            else None,
            "sameAs": site_data.get("social_links", []),
            "contactPoint": {
                "@type": "ContactPoint",
                "email": site_data.get("contact", {}).get("email"),
                "telephone": site_data.get("contact", {}).get("phone"),
                "contactType": "customer service",
            }
            if site_data.get("contact", {}).get("email")
            else None,
        }
        return json.dumps({k: v for k, v in schema.items() if v is not None}, indent=2, ensure_ascii=False)

    def generate_homepage(self, site_data: Dict[str, Any]) -> str:
        payload = [
            json.loads(self.generate_organization(site_data)),
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": site_data.get("name", ""),
                "url": f"{site_data.get('url', '').rstrip('/')}/",
                "description": site_data.get("description", ""),
            },
        ]
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def generate_webpage(self, page_config: Dict[str, Any], site_data: Dict[str, Any], slug: str) -> str:
        base_url = site_data.get("url", "").rstrip("/")
        url = page_config.get("url_path")
        if isinstance(url, str) and url.strip():
            full_url = f"{base_url}{url}"
        else:
            full_url = f"{base_url}/{slug}/"

        schema_type = page_config.get("schema_type", "WebPage")

        schema = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": page_config.get("title", ""),
            "description": page_config.get("description", site_data.get("description", "")),
            "url": full_url,
            "isPartOf": {
                "@type": "WebSite",
                "name": site_data.get("name", ""),
                "url": f"{base_url}/",
            },
            "breadcrumb": {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": f"{base_url}/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": page_config.get("title", ""),
                        "item": full_url,
                    },
                ],
            },
        }
        return json.dumps(schema, indent=2, ensure_ascii=False)

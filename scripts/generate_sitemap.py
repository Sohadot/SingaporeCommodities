from pathlib import Path
from datetime import date

from utils import load_json, write_text, ROOT


def main():
    site = load_json("data/site.json")
    public_dir = ROOT / "public"
    urls = []

    for file in public_dir.rglob("index.html"):
        relative = file.relative_to(public_dir)
        url_path = "/" + str(relative).replace("index.html", "")
        url_path = url_path.replace("\\", "/")
        urls.append(url_path)

    urls = sorted(set(urls))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for path in urls:
        xml.append("  <url>")
        xml.append(f"    <loc>{site['base_url']}{path}</loc>")
        xml.append(f"    <lastmod>{date.today().isoformat()}</lastmod>")
        xml.append("  </url>")

    xml.append("</urlset>")

    write_text("public/sitemap.xml", "\n".join(xml))
    print("Sitemap generated.")


if __name__ == "__main__":
    main()

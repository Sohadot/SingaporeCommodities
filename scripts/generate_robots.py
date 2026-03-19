from utils import load_json, write_text


def main():
    site = load_json("data/site.json")

    robots = f"""User-agent: *
Allow: /

Sitemap: {site['base_url']}/sitemap.xml
"""

    write_text("public/robots.txt", robots)
    print("robots.txt generated.")


if __name__ == "__main__":
    main()

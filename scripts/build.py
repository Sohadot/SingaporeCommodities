import shutil
from datetime import datetime, UTC
from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils import load_json, write_text, ensure_dir, ROOT
from markdown_loader import load_markdown

TEMPLATES_DIR = ROOT / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)


def render_base(title, description, canonical, content):
    template = env.get_template("base.html")
    site = load_json("data/site.json")
    return template.render(
        site=site,
        title=title,
        description=description,
        canonical=canonical,
        content=content,
        year=datetime.now(UTC).year
    )


def build_home():
    site = load_json("data/site.json")
    body_html = load_markdown("content/pages/home.md")
    page_template = env.get_template("page.html")
    content = page_template.render(
        title=site["short_name"],
        content=body_html
    )

    final_html = render_base(
        title=site["site_name"],
        description=site["description"],
        canonical=f"{site['base_url']}/",
        content=content
    )

    write_text("public/index.html", final_html)


def build_simple_page(source_md, output_dir, page_title, page_description):
    site = load_json("data/site.json")
    body_html = load_markdown(source_md)
    page_template = env.get_template("page.html")
    content = page_template.render(
        title=page_title,
        content=body_html
    )

    final_html = render_base(
        title=page_title,
        description=page_description,
        canonical=f"{site['base_url']}{output_dir}",
        content=content
    )

    write_text(f"public{output_dir}index.html", final_html)


def build_city_pages():
    site = load_json("data/site.json")
    cities = load_json("data/cities.json")
    template = env.get_template("city.html")

    for city in cities:
        content = template.render(city=city)
        final_html = render_base(
            title=city["title"],
            description=city["description"],
            canonical=f"{site['base_url']}/framework/{city['slug']}/",
            content=content
        )
        write_text(f"public/framework/{city['slug']}/index.html", final_html)


def build_articles():
    site = load_json("data/site.json")
    items = load_json("data/articles.json")
    template = env.get_template("article.html")

    for item in items:
        body_html = load_markdown(f"content/articles/{item['content_file']}")
        content = template.render(
            title=item["title"],
            content=body_html
        )
        final_html = render_base(
            title=item["title"],
            description=item["description"],
            canonical=f"{site['base_url']}/articles/{item['slug']}/",
            content=content
        )
        write_text(f"public/articles/{item['slug']}/index.html", final_html)


def build_chronicles():
    site = load_json("data/site.json")
    items = load_json("data/chronicles.json")
    template = env.get_template("chronicle.html")

    for item in items:
        body_html = load_markdown(f"content/chronicles/{item['content_file']}")
        content = template.render(
            title=item["title"],
            content=body_html
        )
        final_html = render_base(
            title=item["title"],
            description=item["description"],
            canonical=f"{site['base_url']}/chronicles/{item['slug']}/",
            content=content
        )
        write_text(f"public/chronicles/{item['slug']}/index.html", final_html)


def build_guides():
    site = load_json("data/site.json")
    items = load_json("data/guides.json")
    template = env.get_template("guide.html")

    for item in items:
        body_html = load_markdown(f"content/guides/{item['content_file']}")
        content = template.render(
            title=item["title"],
            content=body_html
        )
        final_html = render_base(
            title=item["title"],
            description=item["description"],
            canonical=f"{site['base_url']}/guide/{item['slug']}/",
            content=content
        )
        write_text(f"public/guide/{item['slug']}/index.html", final_html)


def build_tools():
    site = load_json("data/site.json")
    items = load_json("data/tools.json")
    template = env.get_template("tool.html")

    for item in items:
        content = template.render(
            title=item["title"],
            description=item["description"]
        )
        final_html = render_base(
            title=item["title"],
            description=item["description"],
            canonical=f"{site['base_url']}/tools/{item['slug']}/",
            content=content
        )
        write_text(f"public/tools/{item['slug']}/index.html", final_html)


def build_tools_index():
    site = load_json("data/site.json")
    body_html = load_markdown("content/pages/tools.md")
    page_template = env.get_template("page.html")
    content = page_template.render(
        title="Tools",
        content=body_html
    )

    final_html = render_base(
        title="Tools",
        description="Interpretive tools for understanding Singapore as a commodity control node.",
        canonical=f"{site['base_url']}/tools/",
        content=content
    )

    write_text("public/tools/index.html", final_html)


def copy_assets():
    source_assets = ROOT / "assets"
    target_assets = ROOT / "public" / "assets"

    if not source_assets.exists():
        print("No assets directory found. Skipping asset copy.")
        return

    if target_assets.exists():
        shutil.rmtree(target_assets)

    shutil.copytree(source_assets, target_assets)
    print("Assets copied to public/assets")


def main():
    ensure_dir("public")

    build_home()

    build_simple_page(
        "content/pages/manifesto.md",
        "/manifesto/",
        "Manifesto",
        "The conceptual doctrine behind SingaporeCommodities.com."
    )

    build_simple_page(
        "content/pages/about.md",
        "/about/",
        "About",
        "About SingaporeCommodities.com and its purpose."
    )

    build_simple_page(
        "content/pages/join.md",
        "/join/",
        "Request Strategic Access",
        "Institutional contact and strategic access."
    )

    build_simple_page(
        "content/pages/framework.md",
        "/framework/",
        "Framework",
        "The analytical structure used to understand Singapore as a commodity node."
    )

    build_tools_index()
    build_city_pages()
    build_articles()
    build_chronicles()
    build_guides()
    build_tools()
    copy_assets()

    print("Build complete.")


if __name__ == "__main__":
    main()
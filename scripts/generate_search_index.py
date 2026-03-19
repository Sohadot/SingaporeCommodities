import json
from pathlib import Path

from utils import ROOT, write_text


def main():
    public_dir = ROOT / "public"
    pages = []

    for file in public_dir.rglob("index.html"):
        relative = file.relative_to(public_dir)
        url_path = "/" + str(relative).replace("index.html", "")
        url_path = url_path.replace("\\", "/")

        pages.append({
            "url": url_path,
            "title": url_path.strip("/").replace("-", " ").title() or "Home"
        })

    write_text("public/search-index.json", json.dumps(pages, indent=2))
    print("Search index generated.")


if __name__ == "__main__":
    main()

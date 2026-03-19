import json
from utils import load_json, write_text


def main():
    site = load_json("data/site.json")

    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site["site_name"],
        "url": site["base_url"],
        "description": site["description"],
        "inLanguage": site["language"]
    }

    write_text("public/site-schema.json", json.dumps(schema, indent=2))
    print("Schema generated.")


if __name__ == "__main__":
    main()

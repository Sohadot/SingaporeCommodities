from utils import load_json

REQUIRED_FILES = [
    "data/site.json",
    "data/cities.json",
    "data/commodities.json",
    "data/articles.json",
    "data/chronicles.json",
    "data/guides.json",
    "data/tools.json",
]

REQUIRED_SITE_KEYS = [
    "site_name",
    "short_name",
    "domain",
    "base_url",
    "language",
    "description",
    "navigation",
]


def main():
    for file_path in REQUIRED_FILES:
        load_json(file_path)

    site = load_json("data/site.json")
    for key in REQUIRED_SITE_KEYS:
        if key not in site:
            raise ValueError(f"Missing required key in site.json: {key}")

    cities = load_json("data/cities.json")
    if not isinstance(cities, list) or len(cities) == 0:
        raise ValueError("cities.json must contain at least one city")

    for city in cities:
        for key in ["slug", "title", "thesis", "description"]:
            if key not in city:
                raise ValueError(f"Missing required city key: {key}")

    print("Data validation passed.")


if __name__ == "__main__":
    main()

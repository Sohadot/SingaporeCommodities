from utils import load_json, write_text


def main():
    site = load_json("data/site.json")
    articles = load_json("data/articles.json")
    chronicles = load_json("data/chronicles.json")

    items = []

    for article in articles:
        if article.get("published"):
            items.append({
                "title": article["title"],
                "description": article["description"],
                "link": f"{site['base_url']}/articles/{article['slug']}/",
                "pubDate": article["published"]
            })

    for chronicle in chronicles:
        if chronicle.get("published"):
            items.append({
                "title": chronicle["title"],
                "description": chronicle["description"],
                "link": f"{site['base_url']}/chronicles/{chronicle['slug']}/",
                "pubDate": chronicle["published"]
            })

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<rss version="2.0">')
    xml.append("<channel>")
    xml.append(f"<title>{site['site_name']}</title>")
    xml.append(f"<link>{site['base_url']}</link>")
    xml.append(f"<description>{site['description']}</description>")

    for item in items:
        xml.append("<item>")
        xml.append(f"<title>{item['title']}</title>")
        xml.append(f"<link>{item['link']}</link>")
        xml.append(f"<description>{item['description']}</description>")
        xml.append(f"<pubDate>{item['pubDate']}</pubDate>")
        xml.append("</item>")

    xml.append("</channel>")
    xml.append("</rss>")

    write_text("public/rss.xml", "\n".join(xml))
    print("RSS generated.")


if __name__ == "__main__":
    main()

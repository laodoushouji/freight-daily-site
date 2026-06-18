#!/usr/bin/env python3
"""
货代日报 - 站点构建器
将生成的文章渲染为HTML，重建首页、归档页、sitemap、RSS
"""

import json
import sys
import os
import re
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(SITE_DIR, "templates")
ARTICLES_DIR = os.path.join(SITE_DIR, "articles")
SITE_URL = os.environ.get("SITE_URL", "https://freight-daily.vercel.app")


def load_articles_index():
    """加载文章索引"""
    index_path = os.path.join(ARTICLES_DIR, "_index.json")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_articles_index(index):
    """保存文章索引"""
    index_path = os.path.join(ARTICLES_DIR, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def build_site(new_articles_data=None):
    """构建整个站点"""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # 加载已有索引
    index = load_articles_index()

    # 添加新文章到索引
    if new_articles_data:
        for article in new_articles_data.get("articles", []):
            date_prefix = today_str.replace("-", "")
            slug = re.sub(r'[^\w\u4e00-\u9fff-]', '-', article.get("title", "")[:30]).strip('-')
            slug = re.sub(r'-+', '-', slug)
            filename = f"{date_prefix}-{slug}"

            entry = {
                "filename": filename,
                "title": article.get("title", ""),
                "seo_title": article.get("seo_title", article.get("title", "")),
                "summary": article.get("summary", ""),
                "keywords": article.get("keywords", ""),
                "tags": article.get("tags", []),
                "category": article.get("category", "行业趋势"),
                "date": today_str,
                "date_display": today.strftime("%Y年%m月%d日"),
                "date_iso": today.isoformat(),
                "date_rfc": today.strftime("%a, %d %b %Y %H:%M:%S +0800"),
                "body_html": article.get("body_html", ""),
                "body_markdown": article.get("body_markdown", ""),
            }
            index.insert(0, entry)

        save_articles_index(index)

    if not index:
        print("[WARN] No articles in index, building empty site")

    # 渲染每篇文章页面
    article_template = env.get_template("article.html")
    for i, entry in enumerate(index):
        # 上一篇/下一篇
        prev_article = index[i + 1]["filename"] if i + 1 < len(index) else None
        next_article = index[i - 1]["filename"] if i > 0 else None

        html = article_template.render(
            title=entry["title"],
            seo_title=entry.get("seo_title", entry["title"]),
            seo_description=entry.get("summary", ""),
            seo_keywords=entry.get("keywords", ""),
            page_url=f"{SITE_URL}/articles/{entry['filename']}.html",
            date_iso=entry.get("date_iso", ""),
            date_display=entry.get("date_display", ""),
            summary=entry.get("summary", ""),
            category=entry.get("category", ""),
            body_html=entry.get("body_html", ""),
            tags=entry.get("tags", []),
            prev_article=prev_article,
            next_article=next_article,
            year=today.year,
        )

        article_path = os.path.join(ARTICLES_DIR, f"{entry['filename']}.html")
        with open(article_path, "w", encoding="utf-8") as f:
            f.write(html)

    # 渲染首页
    today_articles = [a for a in index if a.get("date") == today_str]
    recent_articles = index[:20]  # 最近20篇

    index_html = env.get_template("index.html").render(
        today_display=today.strftime("%Y年%m月%d日"),
        today_articles=today_articles,
        recent_articles=recent_articles,
        year=today.year,
    )
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # 渲染归档页
    archive = {}
    for a in index:
        date_key = a.get("date", "unknown")
        if date_key not in archive:
            archive[date_key] = {
                "date_display": a.get("date_display", date_key),
                "articles": [],
            }
        archive[date_key]["articles"].append(a)

    archive_list = sorted(archive.values(), key=lambda x: x["date_display"], reverse=True)

    archive_html = env.get_template("archive.html").render(
        archive=archive_list,
        year=today.year,
    )
    with open(os.path.join(SITE_DIR, "archive.html"), "w", encoding="utf-8") as f:
        f.write(archive_html)

    # 渲染Sitemap
    urls = [{"loc": SITE_URL, "lastmod": today_str, "priority": "1.0"}]
    for a in index:
        urls.append({
            "loc": f"{SITE_URL}/articles/{a['filename']}.html",
            "lastmod": a.get("date", today_str),
            "priority": "0.8",
        })
    urls.append({"loc": f"{SITE_URL}/archive.html", "lastmod": today_str, "priority": "0.6"})

    sitemap_xml = env.get_template("sitemap.xml").render(urls=urls)
    with open(os.path.join(SITE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    # 渲染RSS
    rss_articles = index[:20]
    rss_xml = env.get_template("rss.xml").render(
        site_url=SITE_URL,
        articles=rss_articles,
    )
    with open(os.path.join(SITE_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    print(f"Site built: {len(today_articles)} today, {len(index)} total articles")
    return len(today_articles)


if __name__ == "__main__":
    new_data = None
    if not sys.stdin.isatty():
        try:
            new_data = json.loads(sys.stdin.read())
        except Exception:
            pass

    count = build_site(new_data)
    print(f"Done. {count} new articles published today.")

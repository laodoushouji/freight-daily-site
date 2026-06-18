#!/usr/bin/env python3
"""
货代日报 - 站点构建器 v2
支持：日报简报(brief) + 深度文章(articles) + 首页信息面板
"""

import json
import sys
import os
import glob
import re
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(SITE_DIR, "templates")
ARTICLES_DIR = os.path.join(SITE_DIR, "articles")
BRIEFS_DIR = os.path.join(SITE_DIR, "briefs")
SITE_URL = os.environ.get("SITE_URL", "https://freight-daily-site.vercel.app")


def load_articles_index():
    index_path = os.path.join(ARTICLES_DIR, "_index.json")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_articles_index(index):
    index_path = os.path.join(ARTICLES_DIR, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def load_briefs():
    """加载所有简报，按日期降序"""
    briefs = []
    if not os.path.exists(BRIEFS_DIR):
        return briefs
    for fp in glob.glob(os.path.join(BRIEFS_DIR, "*.json")):
        with open(fp, "r", encoding="utf-8") as f:
            briefs.append(json.load(f))
    briefs.sort(key=lambda x: x.get("date", ""), reverse=True)
    return briefs


def build_site():
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # Load data
    index = load_articles_index()
    briefs = load_briefs()
    today_brief = next((b for b in briefs if b.get("date") == today_str), briefs[0] if briefs else None)

    # === Render article pages ===
    article_template = env.get_template("article.html")
    for i, entry in enumerate(index):
        prev_article = index[i + 1]["filename"] if i + 1 < len(index) else None
        next_article = index[i - 1]["filename"] if i > 0 else None

        html = article_template.render(
            title=entry["title"],
            seo_title=entry.get("seo_title", entry["title"]),
            seo_description=entry.get("summary", ""),
            seo_keywords=entry.get("keywords", ""),
            site_url=SITE_URL,
            filename=entry["filename"],
            date_display=entry.get("date_display", ""),
            date_iso=entry.get("date_iso", ""),
            category=entry.get("category", ""),
            impact=entry.get("impact", ""),
            action_tip=entry.get("action_tip", ""),
            body_html=entry.get("body_html", ""),
            tags=entry.get("tags", []),
            prev_article=prev_article,
            next_article=next_article,
        )
        path = os.path.join(ARTICLES_DIR, f"{entry['filename']}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    # === Render index (dashboard) ===
    today_articles = [a for a in index if a.get("date") == today_str]
    # If no articles today, show latest
    if not today_articles:
        today_articles = index[:3]

    recent_briefs = briefs[1:8] if len(briefs) > 1 else []

    index_html = env.get_template("index.html").render(
        today_display=today.strftime("%Y年%m月%d日"),
        seo_title=f"货代日报 {today.strftime('%m月%d日')} - 运价风向·船司动态·港口预警",
        seo_description=f"{today.strftime('%m月%d日')}货代日报：运价走势、船司GRI/空班、港口拥堵、操作建议，5分钟看完今日关键信息",
        seo_keywords="货代日报,运价,SCFI,GRI,港口拥堵,船司动态,海运",
        site_url=SITE_URL,
        brief=today_brief,
        today_articles=today_articles,
        recent_briefs=recent_briefs,
    )
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # === Render archive ===
    archive = {}
    for a in index:
        date_key = a.get("date", "unknown")
        if date_key not in archive:
            # Find matching brief
            match_brief = next((b for b in briefs if b.get("date") == date_key), None)
            archive[date_key] = {
                "date_display": a.get("date_display", date_key),
                "articles": [],
                "action_summary": match_brief.get("action_summary", []) if match_brief else [],
            }
        archive[date_key]["articles"].append(a)

    archive_list = sorted(archive.values(), key=lambda x: x["date_display"], reverse=True)

    archive_html = env.get_template("archive.html").render(archive=archive_list)
    with open(os.path.join(SITE_DIR, "archive.html"), "w", encoding="utf-8") as f:
        f.write(archive_html)

    # === Sitemap ===
    urls = [{"loc": SITE_URL, "lastmod": today_str, "priority": "1.0"}]
    for a in index:
        urls.append({"loc": f"{SITE_URL}/articles/{a['filename']}.html", "lastmod": a.get("date", today_str), "priority": "0.8"})
    urls.append({"loc": f"{SITE_URL}/archive.html", "lastmod": today_str, "priority": "0.6"})

    sitemap_xml = env.get_template("sitemap.xml").render(urls=urls)
    with open(os.path.join(SITE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    # === RSS ===
    rss_articles = index[:20]
    rss_xml = env.get_template("rss.xml").render(site_url=SITE_URL, articles=rss_articles)
    with open(os.path.join(SITE_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    print(f"Built: {len(today_articles)} articles, brief={'yes' if today_brief else 'no'}, {len(index)} total")
    return len(today_articles)


if __name__ == "__main__":
    count = build_site()
    print(f"Done. {count} articles published today.")

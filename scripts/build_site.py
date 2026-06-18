#!/usr/bin/env python3
"""
站点构建器 v3 — build_site.py

支持：简报面板 + 深度文章双模式渲染
输出：index.html, articles/*.html, archive.html, sitemap.xml, rss.xml
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("需要 jinja2: pip3 install jinja2")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
ARTICLES_DIR = PROJECT_ROOT / "articles"
BRIEFS_DIR = PROJECT_ROOT / "briefs"
OUTPUT_DIR = PROJECT_ROOT  # 静态文件输出到项目根目录


def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def slugify(text: str) -> str:
    """生成 URL 友好的 slug"""
    # 移除特殊字符，保留中文、字母、数字、连字符
    slug = re.sub(r'[^\w\u4e00-\u9fff-]', '-', text)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:60]


def get_latest_brief() -> Optional[dict]:
    """获取最新简报"""
    if not BRIEFS_DIR.exists():
        return None
    brief_files = sorted(BRIEFS_DIR.glob("*.json"))
    if not brief_files:
        return None
    return load_json(brief_files[-1])


def get_all_articles() -> list:
    """获取所有已生成的文章"""
    index = load_json(ARTICLES_DIR / "_index.json")
    if not index:
        return []
    articles = index if isinstance(index, list) else index.get("articles", [])

    result = []
    for a in articles:
        # 加载文章详情
        article_id = a.get("id", "")
        if not article_id:
            continue
        # 查找对应的 JSON 文件
        date_prefix = article_id[:8]
        matches = list(ARTICLES_DIR.glob(f"{date_prefix}*.json"))
        matches = [m for m in matches if m.name != "_index.json"]

        for mf in matches:
            detail = load_json(mf)
            if detail and detail.get("id") == article_id:
                a.update(detail)
                a["filename"] = mf.stem + ".html"
                break

        if a.get("generated") or a.get("body"):
            result.append(a)

    return result


def build_index(brief: Optional[dict], articles: list):
    """构建首页"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("index.html")

    # 确定首页日期
    date_display = brief.get("date_display", datetime.now().strftime("%Y年%m月%d日")) if brief else datetime.now().strftime("%Y年%m月%d日")
    date_str = brief.get("date", datetime.now().strftime("%Y-%m-%d")) if brief else datetime.now().strftime("%Y-%m-%d")

    # 运价快照
    rate_snapshot = brief.get("rate_snapshot", []) if brief else []

    # 船司动态
    carrier_updates = brief.get("carrier_updates", []) if brief else []

    # 港口动态
    port_alerts = brief.get("port_alerts", []) if brief else []

    # 操作建议
    action_summary = brief.get("action_summary", []) if brief else []

    # 深度文章
    deep_articles = []
    for a in articles[:5]:
        deep_articles.append({
            "id": a.get("id", ""),
            "title": a.get("seo_title", a.get("title", "")),
            "impact": a.get("impact", ""),
            "action_tip": a.get("action_tip", ""),
            "tags": a.get("tags", []),
            "filename": a.get("filename", slugify(a.get("seo_title", "article")) + ".html"),
            "date": a.get("date", date_str),
        })

    html = template.render(
        date_display=date_display,
        seo_title=f"货代日报 {date_display} — 运价风向·船司动态·港口预警",
        rate_snapshot=rate_snapshot,
        carrier_updates=carrier_updates,
        port_alerts=port_alerts,
        action_summary=action_summary,
        articles=deep_articles,
        brief_date=date_str,
    )

    out_path = OUTPUT_DIR / "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ index.html")


def build_article_pages(articles: list):
    """构建文章详情页"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("article.html")

    for a in articles:
        title = a.get("seo_title", a.get("title", "货代日报"))
        date = a.get("date", "")
        date_display = a.get("date_display", date)
        impact = a.get("impact", "")
        action_tip = a.get("action_tip", "")
        body = a.get("body", "")
        tags = a.get("tags", [])

        if not body:
            continue

        filename = a.get("filename", slugify(title) + ".html")

        html = template.render(
            title=title,
            date_display=date_display,
            seo_title=f"{title} - 货代日报",
            impact=impact,
            action_tip=action_tip,
            body=body,
            tags=tags,
            article_date=date,
        )

        out_path = OUTPUT_DIR / "articles" / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"  ✅ {sum(1 for a in articles if a.get('body'))} article pages")


def build_archive(articles: list):
    """构建归档页"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("archive.html")

    # 按日期分组
    by_date = {}
    for a in articles:
        d = a.get("date", "unknown")
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(a)

    html = template.render(
        seo_title="往期日报 - 货代日报",
        articles_by_date=sorted(by_date.items(), reverse=True),
    )

    out_path = OUTPUT_DIR / "archive.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ archive.html")


def build_sitemap(articles: list, brief: Optional[dict]):
    """构建 sitemap.xml"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    base = "https://freight-daily-site.vercel.app"

    # 首页
    lines.append(f"  <url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>")

    # 文章
    for a in articles:
        if a.get("body"):
            filename = a.get("filename", slugify(a.get("seo_title", "")) + ".html")
            d = a.get("date", "")
            lines.append(f'  <url><loc>{base}/articles/{filename}</loc><lastmod>{d}</lastmod><priority>0.8</priority></url>')

    # 归档
    lines.append(f"  <url><loc>{base}/archive.html</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>")

    lines.append('</urlset>')

    with open(OUTPUT_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✅ sitemap.xml")


def build_rss(articles: list, brief: Optional[dict]):
    """构建 rss.xml"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    lines.append('  <channel>')
    lines.append('    <title>货代日报 — 每日决策简报</title>')
    lines.append('    <link>https://freight-daily-site.vercel.app</link>')
    lines.append('    <description>运价风向·船司动态·港口预警·操作建议</description>')

    for a in articles[:10]:
        if a.get("body"):
            title = a.get("seo_title", a.get("title", ""))
            filename = a.get("filename", slugify(title) + ".html")
            d = a.get("date", "")
            lines.append(f'    <item>')
            lines.append(f'      <title>{title}</title>')
            lines.append(f'      <link>https://freight-daily-site.vercel.app/articles/{filename}</link>')
            lines.append(f'      <pubDate>{d}</pubDate>')
            lines.append(f'    </item>')

    lines.append('  </channel>')
    lines.append('</rss>')

    with open(OUTPUT_DIR / "rss.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✅ rss.xml")


def main():
    print(f"🔨 站点构建 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 加载数据
    brief = get_latest_brief()
    articles = get_all_articles()

    brief_status = "yes" if brief else "no"
    article_count = len(articles)
    print(f"  简报: {brief_status}, 文章: {article_count}")

    # 构建
    build_index(brief, articles)
    build_article_pages(articles)
    build_archive(articles)
    build_sitemap(articles, brief)
    build_rss(articles, brief)

    print(f"\n──────────────────────────────────────────────────")
    print(f"✅ 构建完成: {article_count} articles, brief={brief_status}")


if __name__ == "__main__":
    main()

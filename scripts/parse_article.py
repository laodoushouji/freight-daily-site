#!/usr/bin/env python3
"""
货代日报 - 解析 Hermes Agent 生成的文章文本
将 ---SECTION--- 格式的文本解析为结构化数据
"""

import json
import sys
import os
import re
import markdown
from datetime import datetime

ARTICLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "articles")


def parse_article_text(text):
    """解析 ---SECTION--- 格式的文章文本"""
    sections = {}
    current_key = None
    current_lines = []

    for line in text.split("\n"):
        match = re.match(r'^---(\w+)---$', line.strip())
        if match:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = match.group(1)
            current_lines = []
        elif current_key:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    # 标准化
    result = {
        "title": sections.get("TITLE", "未命名文章"),
        "seo_title": sections.get("SEO_TITLE", sections.get("TITLE", "")),
        "summary": sections.get("SUMMARY", ""),
        "keywords": sections.get("KEYWORDS", ""),
        "tags": [t.strip() for t in sections.get("TAGS", "").split(",") if t.strip()],
        "category": sections.get("CATEGORY", "行业趋势"),
        "body_markdown": sections.get("BODY", ""),
        "body_html": "",
    }

    # Markdown -> HTML
    if result["body_markdown"]:
        try:
            result["body_html"] = markdown.markdown(
                result["body_markdown"],
                extensions=['tables', 'fenced_code']
            )
        except Exception:
            result["body_html"] = f"<p>{result['body_markdown']}</p>"

    return result


def save_to_index(article_data):
    """保存文章到索引"""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # 生成文件名
    date_prefix = today_str.replace("-", "")
    slug = re.sub(r'[^\w\u4e00-\u9fff-]', '-', article_data["title"][:30]).strip('-')
    slug = re.sub(r'-+', '-', slug)
    filename = f"{date_prefix}-{slug}"

    entry = {
        "filename": filename,
        "title": article_data["title"],
        "seo_title": article_data.get("seo_title", article_data["title"]),
        "summary": article_data.get("summary", ""),
        "keywords": article_data.get("keywords", ""),
        "tags": article_data.get("tags", []),
        "category": article_data.get("category", "行业趋势"),
        "date": today_str,
        "date_display": today.strftime("%Y年%m月%d日"),
        "date_iso": today.isoformat(),
        "date_rfc": today.strftime("%a, %d %b %Y %H:%M:%S +0800"),
        "body_html": article_data.get("body_html", ""),
        "body_markdown": article_data.get("body_markdown", ""),
    }

    # 加载现有索引
    index_path = os.path.join(ARTICLES_DIR, "_index.json")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = []

    index.insert(0, entry)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return filename


if __name__ == "__main__":
    text = sys.stdin.read()
    if not text.strip():
        print("[ERROR] No article text provided via stdin")
        sys.exit(1)

    article = parse_article_text(text)
    filename = save_to_index(article)

    result = {
        "filename": filename,
        "title": article["title"],
        "category": article["category"],
    }
    print(json.dumps(result, ensure_ascii=False))

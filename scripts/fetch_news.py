#!/usr/bin/env python3
"""
货代日报 - 新闻源抓取
从多个公开RSS/网页源抓取货代航运行业新闻
"""

import feedparser
import requests
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# 新闻源配置
NEWS_SOURCES = [
    # 国际航运新闻
    {
        "name": "World Maritime News",
        "url": "https://worldmaritimenews.com/feed/",
        "type": "rss",
        "category": "海运",
        "lang": "en"
    },
    {
        "name": "Splash247",
        "url": "https://splash247.com/feed/",
        "type": "rss",
        "category": "海运",
        "lang": "en"
    },
    {
        "name": "The Loadstar",
        "url": "https://theloadstar.com/feed/",
        "type": "rss",
        "category": "物流",
        "lang": "en"
    },
    {
        "name": "Shipping Watch",
        "url": "https://shippingwatch.com/rss/",
        "type": "rss",
        "category": "航运",
        "lang": "en"
    },
    {
        "name": "JOC Maritime",
        "url": "https://www.joc.com/rss",
        "type": "rss",
        "category": "海运",
        "lang": "en"
    },
    {
        "name": "Seatrade Maritime",
        "url": "https://www.seatrade-maritime.com/rss",
        "type": "rss",
        "category": "航运",
        "lang": "en"
    },
]

# 中文源
CN_SOURCES = [
    {
        "name": "中国航贸网",
        "url": "https://www.snet.com.cn/rss.xml",
        "type": "rss",
        "category": "航贸",
        "lang": "zh"
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_rss(source, max_items=5):
    """抓取RSS源"""
    articles = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = entry.get("summary", entry.get("description", "")).strip()

            # 清理HTML标签
            if summary:
                summary = re.sub(r'<[^>]+>', '', summary)[:300]

            published = entry.get("published", entry.get("updated", ""))
            try:
                if entry.get("published_parsed"):
                    dt = datetime(*entry.published_parsed[:6])
                    published = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

            if title and len(title) > 5:
                articles.append({
                    "source": source["name"],
                    "category": source["category"],
                    "lang": source["lang"],
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "date": published or datetime.now().strftime("%Y-%m-%d"),
                })
    except Exception as e:
        print(f"  [WARN] Failed to fetch {source['name']}: {e}")

    return articles


def fetch_all(max_per_source=5):
    """抓取所有源"""
    all_articles = []

    for source in NEWS_SOURCES + CN_SOURCES:
        print(f"  Fetching: {source['name']}...")
        if source["type"] == "rss":
            articles = fetch_rss(source, max_per_source)
            all_articles.extend(articles)

    # 去重（按标题相似度）
    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"][:30].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    # 按日期排序
    unique.sort(key=lambda x: x.get("date", ""), reverse=True)
    return unique


def select_top_articles(articles, count=5):
    """
    筛选最适合日报的文章
    优先选择：1) 有实质内容的 2) 日期最近的 3) 分类多样的
    """
    # 按分类分组
    by_category = {}
    for a in articles:
        cat = a["category"]
        by_category.setdefault(cat, []).append(a)

    # 每个分类至少选1篇，确保多样性
    selected = []
    categories_covered = set()

    for cat, cat_articles in by_category.items():
        if len(selected) >= count:
            break
        # 选该分类最新的
        top = cat_articles[0]
        selected.append(top)
        categories_covered.add(cat)

    # 剩余名额按日期补充
    remaining = [a for a in articles if a not in selected]
    for a in remaining:
        if len(selected) >= count:
            break
        selected.append(a)

    return selected[:count]


if __name__ == "__main__":
    print("Fetching news sources...")
    articles = fetch_all()
    print(f"Total articles fetched: {len(articles)}")

    top = select_top_articles(articles, 5)
    print(f"\nTop {len(top)} articles for today's daily:")
    for i, a in enumerate(top, 1):
        print(f"  {i}. [{a['category']}] {a['title'][:60]}... ({a['source']})")

    # 输出JSON供后续脚本使用
    output = {
        "fetched_at": datetime.now().isoformat(),
        "total_fetched": len(articles),
        "selected": top
    }
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(output, ensure_ascii=False, indent=2))

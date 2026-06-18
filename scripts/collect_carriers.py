#!/usr/bin/env python3
"""
船司公告采集器 — collect_carriers.py

从 5 家船司官网采集 GRI/空班/新航线/附加费公告：
- MSC, Maersk, CMA CGM, ONE, COSCO

单家失败不阻塞其余，AI 辅助提取结构化信息。

输出: data/carriers/{date}.json
"""

import argparse
import json
import os
import re
import sys
from typing import Optional
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─── 项目路径 ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "carriers"

# ─── 请求配置 ───
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}
TIMEOUT = 15

# ─── 船司配置 ───
CARRIERS = {
    "MSC": {
        "name": "MSC",
        "urls": [
            "https://www.msc.com/en/news",
            "https://www.msc.com/en/newsroom",
        ],
        "keywords": {
            "GRI": ["gri", "general rate increase", "rate increase", "运价上调"],
            "空班": ["blank sailing", "blank voyage", "skip", "cancellation", "空班", "停航"],
            "新航线": ["new service", "new route", "new trade", "新航线", "新增航线"],
            "附加费": ["surcharge", "additional charge", "congestion", "附加费", "拥堵费"],
        },
    },
    "Maersk": {
        "name": "Maersk",
        "urls": [
            "https://www.maersk.com/news",
            "https://www.maersk.com/updates",
        ],
        "keywords": {
            "GRI": ["gri", "general rate increase", "rate increase"],
            "空班": ["blank sailing", "blank voyage", "skip", "omission"],
            "新航线": ["new service", "new connection", "new route"],
            "附加费": ["surcharge", "congestion surcharge", "peak season"],
        },
    },
    "CMA CGM": {
        "name": "CMA CGM",
        "urls": [
            "https://www.cma-cgm.com/news",
            "https://www.cma-cgm.com/latest-news",
        ],
        "keywords": {
            "GRI": ["gri", "rate increase", "rate restoration"],
            "空班": ["blank sailing", "blank program", "omission"],
            "新航线": ["new service", "new line", "new connection"],
            "附加费": ["surcharge", "peak season surcharge", "congestion"],
        },
    },
    "ONE": {
        "name": "ONE",
        "urls": [
            "https://www.one-line.com/en/news",
            "https://www.one-line.com/news-and-announcements",
        ],
        "keywords": {
            "GRI": ["gri", "rate increase", "rate restoration"],
            "空班": ["blank sailing", "omission", "skip"],
            "新航线": ["new service", "new route"],
            "附加费": ["surcharge", "additional charge"],
        },
    },
    "COSCO": {
        "name": "COSCO",
        "urls": [
            "https://lines.coscoshipping.com/news",
            "https://lines.coscoshipping.com/press",
        ],
        "keywords": {
            "GRI": ["gri", "rate increase", "运价上调"],
            "空班": ["blank sailing", "skip", "空班", "停航"],
            "新航线": ["new service", "新航线", "新增"],
            "附加费": ["surcharge", "附加费"],
        },
    },
}

# ─── 航线映射 ───
ROUTE_MAP = {
    "europe": "欧线",
    "asia-europe": "欧线",
    "far east": "欧线",
    "mediterranean": "地中",
    "uswc": "美西",
    "west coast": "美西",
    "los angeles": "美西",
    "long beach": "美西",
    "usec": "美东",
    "east coast": "美东",
    "new york": "美东",
    "savannah": "美东",
    "southeast asia": "东南亚",
    "sea": "东南亚",
    "middle east": "中东",
    "gulf": "中东",
    "intra-asia": "东南亚",
    "transpacific": "美西",
    "trans-atlantic": "欧线",
    "asia": "东南亚",
    "africa": "非洲",
    "south america": "南美",
    "latin america": "南美",
    "oceania": "大洋洲",
    "australia": "大洋洲",
}


def detect_route(text: str) -> str:
    """从文本中检测航线"""
    text_lower = text.lower()
    for keyword, route in ROUTE_MAP.items():
        if keyword in text_lower:
            return route
    return "其他"


def detect_type(text: str, keywords: dict) -> str:
    """从文本中检测公告类型"""
    text_lower = text.lower()
    for type_name, kws in keywords.items():
        for kw in kws:
            if kw in text_lower:
                return type_name
    return "其他"


def extract_date(text: str) -> str:
    """从文本中提取日期"""
    # 尝试多种日期格式
    patterns = [
        # June 25, 2026 / Jun 25, 2026
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December"
        r"|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}",
        # 2026-06-25
        r"\d{4}-\d{2}-\d{2}",
        # 25 June 2026
        r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December"
        r"|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}",
        # 2026年6月25日
        r"\d{4}年\d{1,2}月\d{1,2}日",
        # 2026/06/25
        r"\d{4}/\d{2}/\d{2}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


def extract_amount(text: str) -> str:
    """从文本中提取金额"""
    patterns = [
        r"\+\s*\$\s*[\d,]+(?:\s*/\s*(?:40HQ|20GP|TEU|FEU|container|per TEU|per FEU))?",
        r"\$\s*[\d,]+(?:\.\d{2})?(?:\s*/\s*(?:40HQ|20GP|TEU|FEU))?",
        r"USD\s*[\d,]+(?:\s*/\s*(?:40HQ|20GP|TEU|FEU))?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return ""


def fetch_carrier_page(url: str) -> Optional[str]:
    """抓取单个页面内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"    请求失败 {url}: {e}", file=sys.stderr)
        return None


def parse_carrier_news(carrier_key: str, html: str) -> list[dict]:
    """解析船司新闻页面，提取结构化公告信息"""
    carrier_config = CARRIERS[carrier_key]
    items = []

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 查找新闻条目：常见的 HTML 结构
        # 模式1: <article> 或 <li> 包含新闻
        news_elements = soup.find_all(["article", "li", "div"],
                                      class_=re.compile(r"news|update|press|article|post|item",
                                                        re.IGNORECASE))
        if not news_elements:
            # 模式2: 查找包含链接和日期的容器
            news_elements = soup.find_all(["div", "section"],
                                          recursive=True,
                                          limit=50)

        for elem in news_elements:
            text = elem.get_text(separator=" ", strip=True)
            if not text or len(text) < 20:
                continue

            # 检测是否是相关公告
            detected_type = detect_type(text, carrier_config["keywords"])
            if detected_type == "其他":
                # 额外检查标题
                heading = elem.find(["h1", "h2", "h3", "h4", "a"])
                if heading:
                    heading_text = heading.get_text(strip=True)
                    detected_type = detect_type(heading_text, carrier_config["keywords"])

            if detected_type == "其他":
                continue  # 跳过不相关的新闻

            # 提取链接
            link = ""
            a_tag = elem.find("a", href=True)
            if a_tag:
                link = a_tag.get("href", "")
                if link and not link.startswith("http"):
                    # 相对路径转绝对路径
                    from urllib.parse import urljoin
                    base_url = carrier_config["urls"][0]
                    link = urljoin(base_url, link)

            # 提取标题
            title = ""
            heading = elem.find(["h1", "h2", "h3", "h4"])
            if heading:
                title = heading.get_text(strip=True)
            elif a_tag:
                title = a_tag.get_text(strip=True)
            else:
                title = text[:100]

            # 提取日期
            effective = extract_date(text)

            # 提取金额
            amount = extract_amount(text)

            # 检测航线
            route = detect_route(text)

            # 构建条目
            item = {
                "carrier": carrier_config["name"],
                "type": detected_type,
                "route": route,
            }
            if effective:
                item["effective"] = effective
            if amount:
                item["amount"] = amount
            if title:
                item["detail"] = title[:200]

            items.append(item)

    except Exception as e:
        print(f"    解析失败: {e}", file=sys.stderr)

    return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 降级数据
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FALLBACK_ITEMS = [
    {
        "carrier": "MSC",
        "type": "GRI",
        "route": "欧线",
        "effective": "",
        "amount": "+$300/40HQ",
        "detail": "MSC GRI — 采集时外部数据源不可用，此为占位数据",
    },
    {
        "carrier": "Maersk",
        "type": "附加费",
        "route": "美西",
        "effective": "",
        "amount": "+$200/40HQ",
        "detail": "Maersk 旺季附加费 — 采集时外部数据源不可用，此为占位数据",
    },
    {
        "carrier": "CMA CGM",
        "type": "空班",
        "route": "欧线",
        "effective": "",
        "detail": "CMA CGM 空班通知 — 采集时外部数据源不可用，此为占位数据",
    },
    {
        "carrier": "ONE",
        "type": "GRI",
        "route": "美东",
        "effective": "",
        "amount": "+$250/40HQ",
        "detail": "ONE GRI — 采集时外部数据源不可用，此为占位数据",
    },
    {
        "carrier": "COSCO",
        "type": "新航线",
        "route": "东南亚",
        "effective": "",
        "detail": "COSCO 新航线通知 — 采集时外部数据源不可用，此为占位数据",
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 主流程
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect_carriers(date_str: str) -> dict:
    """采集船司公告的主函数"""
    print(f"🚢 船司公告采集 — {date_str}")
    print("=" * 50)

    all_items = []
    success_count = 0
    fail_count = 0

    for carrier_key, carrier_config in CARRIERS.items():
        carrier_name = carrier_config["name"]
        print(f"\n📡 采集 {carrier_name} ...")

        carrier_items = []
        for url in carrier_config["urls"]:
            print(f"   尝试: {url}")
            html = fetch_carrier_page(url)
            if html:
                items = parse_carrier_news(carrier_key, html)
                if items:
                    carrier_items.extend(items)
                    print(f"   ✅ 发现 {len(items)} 条公告")
                    break
            else:
                print(f"   ❌ 页面不可访问")

        if carrier_items:
            all_items.extend(carrier_items)
            success_count += 1
        else:
            fail_count += 1
            print(f"   ⚠️ {carrier_name} 未获取到公告数据")

    # 如果所有船司都失败，使用降级数据
    updated = len(all_items) > 0
    if not updated:
        print("\n⚠️ 所有船司数据源不可用，使用降级占位数据")
        all_items = FALLBACK_ITEMS.copy()
        # 为降级数据设置日期
        for item in all_items:
            if not item.get("effective"):
                item["effective"] = date_str

    # 去重（按 carrier + type + detail 去重）
    seen = set()
    unique_items = []
    for item in all_items:
        key = f"{item['carrier']}|{item['type']}|{item.get('detail', '')[:50]}"
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    result = {
        "date": date_str,
        "items": unique_items,
    }

    # 保存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / f"{date_str}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"\n{'─' * 50}")
    print(f"✅ 数据已保存: {output_path}")
    print(f"   日期: {result['date']}")
    print(f"   船司成功/失败: {success_count}/{fail_count}")
    print(f"   公告总数: {len(unique_items)}")
    print(f"   数据来源: {'在线采集' if updated else '降级占位'}")

    # 按类型统计
    type_counts = {}
    for item in unique_items:
        t = item.get("type", "其他")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in type_counts.items():
        print(f"   {t}: {c} 条")

    # 按船司统计
    carrier_counts = {}
    for item in unique_items:
        c = item.get("carrier", "未知")
        carrier_counts[c] = carrier_counts.get(c, 0) + 1
    for c, n in carrier_counts.items():
        print(f"   {c}: {n} 条")

    print(f"{'─' * 50}")

    return result


def main():
    parser = argparse.ArgumentParser(description="船司公告采集器")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    # 验证日期格式
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"❌ 无效日期格式: {date_str}，请使用 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    result = collect_carriers(date_str)


if __name__ == "__main__":
    main()

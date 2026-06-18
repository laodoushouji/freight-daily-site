#!/usr/bin/env python3
"""
运价数据采集器 — collect_rates.py

从多个数据源采集集装箱运价信息：
1. 上海航运交易所 SCFI 指数
2. Freightos 公开页面
3. RSS 新闻源（降级）
4. 上周历史数据（降级）
5. 硬编码默认值（最终降级）

输出: data/rates/{date}.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─── 项目路径 ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "rates"

# ─── 请求配置 ───
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 15

# ─── 默认航线数据（最终降级） ───
DEFAULT_ROUTES = [
    {"route": "欧线", "price": "$2,800/40HQ", "index_value": 2350.5},
    {"route": "美西", "price": "$1,950/40HQ", "index_value": 1820.3},
    {"route": "美东", "price": "$3,200/40HQ", "index_value": 2890.1},
    {"route": "东南亚", "price": "$450/20GP", "index_value": 420.0},
    {"route": "中东", "price": "$1,100/20GP", "index_value": 1050.7},
]

# ─── 方向阈值 ───
DIRECTION_THRESHOLD = 0.02  # 2%


def compute_direction(current: float, previous: float) -> str:
    """根据涨跌幅度计算方向标记：▲ / ▼ / →"""
    if previous == 0:
        return "→"
    pct = (current - previous) / previous
    if pct > DIRECTION_THRESHOLD:
        return "▲"
    elif pct < -DIRECTION_THRESHOLD:
        return "▼"
    return "→"


def format_change(current: float, previous: float) -> str:
    """格式化涨跌金额"""
    diff = current - previous
    if diff > 0:
        return f"+${int(diff)}"
    elif diff < 0:
        return f"-${int(abs(diff))}"
    return "$0"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据源 1: 上海航运交易所 SCFI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def try_scfi() -> Optional[dict]:
    """尝试从上海航运交易所官网获取 SCFI 指数"""
    urls = [
        "https://www.sse.net.cn/index.jsp",
        "https://www.sse.net.cn/",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 尝试多种常见的 SCFI 数据位置
            # 模式1: 查找包含 SCFI 的表格
            tables = soup.find_all("table")
            for table in tables:
                text = table.get_text()
                if "SCFI" in text or "上海出口集装箱" in text:
                    return _parse_scfi_table(table)

            # 模式2: 查找包含指数数据的 div/span
            for tag in soup.find_all(["div", "span", "p"]):
                text = tag.get_text(strip=True)
                if "SCFI" in text and any(c.isdigit() for c in text):
                    return _parse_scfi_text(text)

            # 模式3: 页面整体文本解析
            page_text = soup.get_text()
            if "SCFI" in page_text:
                return _parse_scfi_page(page_text)

        except Exception as e:
            print(f"  [SCFI] 请求失败 {url}: {e}", file=sys.stderr)
            continue

    return None


def _parse_scfi_table(table) -> Optional[dict]:
    """从 HTML 表格解析 SCFI 数据"""
    try:
        rows = table.find_all("tr")
        routes_data = {}
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                route_name = cells[0].get_text(strip=True)
                value_text = cells[1].get_text(strip=True)
                # 尝试提取数值
                try:
                    value = float(value_text.replace(",", "").replace("￥", "").replace("$", ""))
                    routes_data[route_name] = value
                except ValueError:
                    continue

        if routes_data:
            return {"source": "scfi", "data": routes_data}
    except Exception as e:
        print(f"  [SCFI] 表格解析失败: {e}", file=sys.stderr)
    return None


def _parse_scfi_text(text: str) -> Optional[dict]:
    """从文本中提取 SCFI 数据"""
    import re
    try:
        # 尝试匹配 SCFI 指数值
        match = re.search(r"SCFI[：:\s]*(\d+\.?\d*)", text)
        if match:
            return {"source": "scfi", "data": {"综合指数": float(match.group(1))}}
    except Exception:
        pass
    return None


def _parse_scfi_page(page_text: str) -> Optional[dict]:
    """从页面整体文本解析 SCFI 数据"""
    import re
    try:
        matches = re.findall(r"(?:欧线|美西|美东|东南亚|中东|SCFI)[：:\s]*(\d+\.?\d*)", page_text)
        if matches:
            return {"source": "scfi", "data": {"指数": float(matches[0])}}
    except Exception:
        pass
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据源 2: Freightos
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def try_freightos() -> Optional[dict]:
    """尝试从 Freightos 公开页面获取集装箱运价"""
    urls = [
        "https://www.freightos.com/freight-resources/freight-index/",
        "https://www.freightos.com/freight-resources/container-shipping-cost/",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            routes_data = {}
            page_text = soup.get_text()

            # Freightos 页面常见的关键词模式
            import re
            # 尝试提取各种航线的价格
            patterns = [
                (r"(?:Asia|China)\s*(?:to|–|-)\s*(?:Europe|EU)[^\$]*\$?([\d,]+)", "欧线"),
                (r"(?:Asia|China)\s*(?:to|–|-)\s*(?:West Coast|USWC|LA|Long Beach)[^\$]*\$?([\d,]+)", "美西"),
                (r"(?:Asia|China)\s*(?:to|–|-)\s*(?:East Coast|USEC|NY|New York)[^\$]*\$?([\d,]+)", "美东"),
                (r"(?:Asia|China)\s*(?:to|–|-)\s*(?:Southeast Asia|SEA)[^\$]*\$?([\d,]+)", "东南亚"),
                (r"(?:Asia|China)\s*(?:to|–|-)\s*(?:Middle East|ME)[^\$]*\$?([\d,]+)", "中东"),
            ]
            for pattern, route_name in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1).replace(",", ""))
                        routes_data[route_name] = value
                    except ValueError:
                        continue

            if routes_data:
                return {"source": "freightos", "data": routes_data}

        except Exception as e:
            print(f"  [Freightos] 请求失败 {url}: {e}", file=sys.stderr)
            continue

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据源 3: RSS 新闻源
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def try_rss() -> Optional[dict]:
    """尝试从 RSS 新闻源提取运价信息"""
    try:
        import feedparser
    except ImportError:
        print("  [RSS] feedparser 未安装，跳过", file=sys.stderr)
        return None

    feed_urls = [
        "https://www.freightwaves.com/feed",
        "https://splash247.com/feed/",
        "https://theloadstar.com/feed/",
        "https://www.joc.com/rss",
    ]

    routes_data = {}
    import re

    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            for entry in getattr(feed, "entries", [])[:20]:
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                text = f"{title} {summary}"

                # 在新闻文本中搜索运价数字
                price_patterns = [
                    (r"欧[美州].*?\$([\d,]+)", "欧线"),
                    (r"Europe.*?\$([\d,]+)", "欧线"),
                    (r"美西.*?\$([\d,]+)", "美西"),
                    (r"US\s*West\s*Coast.*?\$([\d,]+)", "美西"),
                    (r"美东.*?\$([\d,]+)", "美东"),
                    (r"US\s*East\s*Coast.*?\$([\d,]+)", "美东"),
                    (r"东南亚.*?\$([\d,]+)", "东南亚"),
                    (r"Middle\s*East.*?\$([\d,]+)", "中东"),
                ]
                for pattern, route_name in price_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match and route_name not in routes_data:
                        try:
                            routes_data[route_name] = float(match.group(1).replace(",", ""))
                        except ValueError:
                            continue

                if len(routes_data) >= 3:
                    break
        except Exception as e:
            print(f"  [RSS] 解析 {feed_url} 失败: {e}", file=sys.stderr)
            continue

        if len(routes_data) >= 3:
            break

    if routes_data:
        return {"source": "rss", "data": routes_data}
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 降级策略 3/4: 读取上周历史数据
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_last_week(date_str: str) -> Optional[dict]:
    """加载上周的运价数据"""
    current_date = datetime.strptime(date_str, "%Y-%m-%d")
    # 往前找最多 14 天
    for delta in range(1, 15):
        prev_date = (current_date - timedelta(days=delta)).strftime("%Y-%m-%d")
        prev_file = DATA_DIR / f"{prev_date}.json"
        if prev_file.exists():
            try:
                with open(prev_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("routes"):
                    print(f"  [降级] 使用 {prev_date} 的历史数据")
                    return data
            except Exception as e:
                print(f"  [降级] 读取 {prev_file} 失败: {e}", file=sys.stderr)
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 合并多数据源结果
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def merge_sources(scfi_data: Optional[dict], freightos_data: Optional[dict], rss_data: Optional[dict]) -> dict:
    """合并多个数据源的结果，优先级 SCFI > Freightos > RSS"""
    sources = []
    route_values = {}

    if scfi_data:
        sources.append("scfi")
        route_values.update(scfi_data.get("data", {}))
    if freightos_data:
        sources.append("freightos")
        for k, v in freightos_data.get("data", {}).items():
            if k not in route_values:
                route_values[k] = v
    if rss_data:
        sources.append("rss")
        for k, v in rss_data.get("data", {}).items():
            if k not in route_values:
                route_values[k] = v

    return {"source": "+".join(sources) if sources else "fallback", "data": route_values}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 构建最终输出
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_output(date_str: str, merged: dict, last_week_data: Optional[dict]) -> dict:
    """构建最终的 JSON 输出结构"""
    source = merged["source"]
    raw_data = merged["data"]
    updated = source != "fallback"

    # 上周各航线的 index_value
    prev_values = {}
    if last_week_data and "routes" in last_week_data:
        for r in last_week_data["routes"]:
            prev_values[r["route"]] = r.get("index_value", 0)

    routes = []
    for default in DEFAULT_ROUTES:
        route_name = default["route"]
        default_index = default["index_value"]

        # 使用采集到的数据或默认值
        index_value = raw_data.get(route_name, default_index)

        # 计算涨跌
        prev = prev_values.get(route_name, index_value)  # 无历史则认为持平
        change = format_change(index_value, prev)
        direction = compute_direction(index_value, prev)

        # 价格文本
        price = default["price"]
        # 如果有采集值，尝试更新价格中的数字
        if route_name in raw_data:
            import re
            price = re.sub(r"\$[\d,]+", f"${int(index_value):,}", price)

        routes.append({
            "route": route_name,
            "price": price,
            "change": change,
            "direction": direction,
            "index_value": round(index_value, 1),
        })

    return {
        "date": date_str,
        "source": source,
        "updated": updated,
        "routes": routes,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 主流程
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect_rates(date_str: str) -> dict:
    """采集运价数据的主函数"""
    print(f"📊 运价数据采集 — {date_str}")
    print("=" * 50)

    # 步骤 1: 尝试 SCFI
    print("[1/3] 尝试上海航运交易所 SCFI ...")
    scfi_data = try_scfi()
    if scfi_data:
        print(f"  ✅ SCFI 数据获取成功: {list(scfi_data.get('data', {}).keys())}")
    else:
        print("  ❌ SCFI 数据获取失败")

    # 步骤 2: 尝试 Freightos
    print("[2/3] 尝试 Freightos ...")
    freightos_data = try_freightos()
    if freightos_data:
        print(f"  ✅ Freightos 数据获取成功: {list(freightos_data.get('data', {}).keys())}")
    else:
        print("  ❌ Freightos 数据获取失败")

    # 步骤 3: 尝试 RSS
    print("[3/3] 尝试 RSS 新闻源 ...")
    rss_data = try_rss()
    if rss_data:
        print(f"  ✅ RSS 数据提取成功: {list(rss_data.get('data', {}).keys())}")
    else:
        print("  ❌ RSS 数据提取失败")

    # 合并数据源
    merged = merge_sources(scfi_data, freightos_data, rss_data)
    print(f"\n📡 数据来源: {merged['source']}")

    # 加载上周数据（用于计算涨跌）
    last_week_data = load_last_week(date_str)

    # 构建最终输出
    result = build_output(date_str, merged, last_week_data)

    # 保存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / f"{date_str}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"\n{'─' * 50}")
    print(f"✅ 数据已保存: {output_path}")
    print(f"   日期: {result['date']}")
    print(f"   来源: {result['source']}")
    print(f"   已更新: {'是' if result['updated'] else '否（使用默认值）'}")
    print(f"   航线数: {len(result['routes'])}")
    for r in result["routes"]:
        print(f"   {r['direction']} {r['route']}: {r['price']} ({r['change']})")
    print(f"{'─' * 50}")

    return result


def main():
    parser = argparse.ArgumentParser(description="运价数据采集器")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    # 验证日期格式
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"❌ 无效日期格式: {date_str}，请使用 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    result = collect_rates(date_str)
    if not result.get("routes"):
        print("⚠️ 警告: 未获取到任何航线数据", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

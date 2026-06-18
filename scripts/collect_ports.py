#!/usr/bin/env python3
"""
港口动态采集器 — collect_ports.py

采集 6 个目标港口的等泊/拥堵信息：
- 宁波、上海、洛杉矶、鹿特丹、巴生、新加坡

数据源：MarineTraffic / 港口官网 / RSS 新闻
异常事件（罢工/台风/封闭）标记 ⚠️

输出: data/ports/{date}.json
"""

import argparse
import json
import re
import sys
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─── 项目路径 ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ports"

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

# ─── 目标港口配置 ───
PORTS = {
    "ningbo": {
        "name": "宁波",
        "name_en": "Ningbo",
        "urls": [
            "https://www.marinetraffic.com/en/ais/details/ports/4266/China_port:NINGBO",
            "https://www.np-port.com/",
        ],
        "default_wait": "3-5",
    },
    "shanghai": {
        "name": "上海",
        "name_en": "Shanghai",
        "urls": [
            "https://www.marinetraffic.com/en/ais/details/ports/3544/China_port:SHANGHAI",
            "https://www.portshanghai.com.cn/",
        ],
        "default_wait": "2-4",
    },
    "los_angeles": {
        "name": "洛杉矶",
        "name_en": "Los Angeles",
        "urls": [
            "https://www.marinetraffic.com/en/ais/details/ports/315/United%20States_port:LOS%20ANGELES",
            "https://www.portoflosangeles.org/",
        ],
        "default_wait": "1-3",
    },
    "rotterdam": {
        "name": "鹿特丹",
        "name_en": "Rotterdam",
        "urls": [
            "https://www.marinetraffic.com/en/ais/details/ports/790/Netherlands_port:ROTTERDAM",
            "https://www.portofrotterdam.com/",
        ],
        "default_wait": "1-2",
    },
    "klang": {
        "name": "巴生",
        "name_en": "Klang",
        "urls": [
            "https://www.marinetraffic.com/en/ais/details/ports/630/Malaysia_port:KLANG",
            "https://www.pka.gov.my/",
        ],
        "default_wait": "2-3",
    },
    "singapore": {
        "name": "新加坡",
        "name_en": "Singapore",
        "urls": [
            "https://www.marinetraffic.com/en/ais/details/ports/409/Singapore_port:SINGAPORE",
            "https://www.mpa.gov.sg/",
        ],
        "default_wait": "1-2",
    },
}

# ─── 异常事件关键词 ───
ALERT_KEYWORDS = [
    "strike", "罢工",
    "typhoon", "台风", "cyclone", "hurricane",
    "closure", "closed", "封闭", "关闭",
    "blockade", "封锁",
    "explosion", "爆炸",
    "fire", "火灾",
    "earthquake", "地震",
    "tsunami", "海啸",
    "protest", "抗议",
    "curfew", "宵禁",
    "war", "战争",
    "embargo", "禁运",
]

# ─── 拥堵关键词 ───
CONGESTION_KEYWORDS = [
    "congestion", "congested", "拥堵",
    "delay", "delays", "延误", "延迟",
    "wait", "waiting", "等待", "等泊",
    "backlog", "积压",
    "bottleneck", "瓶颈",
]

# ─── 缓解关键词 ───
EASE_KEYWORDS = [
    "easing", "improved", "缓解", "改善",
    "reduced", "reduction", "减少",
    "normal", "正常", "恢复",
    "clear", "cleared", "畅通",
]


def fetch_page(url: str) -> Optional[str]:
    """抓取页面内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"    请求失败 {url}: {e}", file=sys.stderr)
        return None


def detect_alert(text: str, source_type: str = "unknown") -> tuple:
    """检测异常事件，返回 (是否异常, 事件描述, 原因, 消息源)
    
    source_type 决定检测严格度：
    - "rss": RSS 新闻标题/摘要 → 严格匹配，直接用
    - "web": 网页全文 → 容易误判，跳过（只用 RSS 判断异常）
    """
    # 从网页全文做异常检测太容易误判（如 "WAR" 出现在 title 里不是战争）
    # 只信任 RSS 新闻源
    if source_type != "rss":
        return False, "", "", ""
    
    text_lower = text.lower()
    for keyword in ALERT_KEYWORDS:
        if keyword in text_lower:
            # 提取包含关键词的句子
            sentences = re.split(r'[.。!！?？\n]', text)
            for sentence in sentences:
                if keyword in sentence.lower() and len(sentence.strip()) > 10:
                    # 清理 HTML 残留和多余空白
                    clean = re.sub(r'<[^>]+>', '', sentence.strip())
                    clean = re.sub(r'\s+', ' ', clean)[:150]
                    # 翻译关键词为中文原因
                    reason_map = {
                        "strike": "罢工", "罢工": "罢工",
                        "typhoon": "台风", "台风": "台风", "cyclone": "气旋", "hurricane": "飓风",
                        "closure": "关闭/封闭", "closed": "关闭", "封闭": "封闭", "关闭": "关闭",
                        "blockade": "封锁", "封锁": "封锁",
                        "explosion": "爆炸", "爆炸": "爆炸",
                        "fire": "火灾", "火灾": "火灾",
                        "earthquake": "地震", "地震": "地震",
                        "tsunami": "海啸", "海啸": "海啸",
                        "protest": "抗议活动", "抗议": "抗议活动",
                        "curfew": "宵禁", "宵禁": "宵禁",
                        "war": "武装冲突", "战争": "战争",
                        "embargo": "禁运", "禁运": "禁运",
                    }
                    reason = reason_map.get(keyword, keyword)
                    return True, f"⚠️ {reason}", reason, clean
    return False, "", "", ""


def detect_congestion(text: str) -> str:
    """分析拥堵状况，返回状态描述"""
    text_lower = text.lower()

    has_congestion = any(kw in text_lower for kw in CONGESTION_KEYWORDS)
    has_ease = any(kw in text_lower for kw in EASE_KEYWORDS)

    if has_congestion and has_ease:
        return "拥堵缓解"
    elif has_congestion:
        return "拥堵中"
    elif has_ease:
        return "正常运行"
    else:
        return "运行正常"


def extract_wait_days(text: str, port_key: str) -> str:
    """尝试从文本中提取等泊天数"""
    # 模式1: "wait 3-5 days" / "waiting 2 days"
    patterns = [
        r"wait(?:ing)?\s+(\d+[-–]\d+)\s*days?",
        r"wait(?:ing)?\s+(\d+)\s*[-–to]+\s*(\d+)\s*days?",
        r"(\d+[-–]\d+)\s*days?\s*(?:wait|delay)",
        r"delay(?:s)?\s*(?:of)?\s*(\d+[-–]\d+)\s*days?",
        r"等泊\s*(\d+[-–]\d+)\s*天",
        r"延误\s*(\d+[-–]\d+)\s*天",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).replace("–", "-")

    # 模式2: 单个数字 "3 days waiting"
    single_patterns = [
        r"wait(?:ing)?\s+(\d+)\s*days?",
        r"(\d+)\s*days?\s*(?:wait|delay)",
        r"等泊\s*(\d+)\s*天",
    ]
    for pattern in single_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            days = match.group(1)
            return f"{days}"

    return ""


def try_marinetraffic(port_key: str) -> Optional[dict]:
    """尝试从 MarineTraffic 获取港口信息"""
    port_config = PORTS[port_key]
    url = port_config["urls"][0]  # MarineTraffic URL 在第一位

    html = fetch_page(url)
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        if not text or len(text) < 50:
            return None

        alert, alert_desc, alert_reason, alert_source = detect_alert(text, "marinetraffic")
        status = detect_congestion(text)
        wait_days = extract_wait_days(text, port_key)

        return {
            "source": "marinetraffic",
            "source_url": url,
            "status": status,
            "wait_days": wait_days,
            "alert": alert,
            "alert_desc": alert_desc,
            "alert_reason": alert_reason,
            "alert_source": alert_source,
            "detail": "",
        }
    except Exception as e:
        print(f"    MarineTraffic 解析失败: {e}", file=sys.stderr)
        return None


def try_port_website(port_key: str) -> Optional[dict]:
    """尝试从港口官网获取信息"""
    port_config = PORTS[port_key]
    # 官网 URL 在第二位
    if len(port_config["urls"]) < 2:
        return None
    url = port_config["urls"][1]

    html = fetch_page(url)
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        if not text or len(text) < 50:
            return None

        alert, alert_desc, alert_reason, alert_source = detect_alert(text, "port_website")
        status = detect_congestion(text)
        wait_days = extract_wait_days(text, port_key)

        return {
            "source": "port_website",
            "source_url": url,
            "status": status,
            "wait_days": wait_days,
            "alert": alert,
            "alert_desc": alert_desc,
            "alert_reason": alert_reason,
            "alert_source": alert_source,
            "detail": "",
        }
    except Exception as e:
        print(f"    官网解析失败: {e}", file=sys.stderr)
        return None


def try_rss_news(port_key: str) -> Optional[dict]:
    """尝试从 RSS 新闻获取港口相关信息"""
    try:
        import feedparser
    except ImportError:
        print("    feedparser 未安装，跳过 RSS", file=sys.stderr)
        return None

    port_config = PORTS[port_key]
    port_name_en = port_config["name_en"]
    port_name_cn = port_config["name"]

    feed_urls = [
        "https://www.freightwaves.com/feed",
        "https://splash247.com/feed/",
        "https://theloadstar.com/feed/",
    ]

    relevant_texts = []

    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            for entry in getattr(feed, "entries", [])[:30]:
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                text = f"{title} {summary}"

                # 检查是否与该港口相关
                if port_name_en.lower() in text.lower() or port_name_cn in text:
                    relevant_texts.append(text)
        except Exception:
            continue

    if not relevant_texts:
        return None

    combined_text = " ".join(relevant_texts)
    alert, alert_desc, alert_reason, alert_source = detect_alert(combined_text, "rss")
    status = detect_congestion(combined_text)
    wait_days = extract_wait_days(combined_text, port_key)

    return {
        "source": "rss",
        "source_url": feed_urls[0] if feed_urls else "",
        "status": status,
        "wait_days": wait_days,
        "alert": alert,
        "alert_desc": alert_desc,
        "alert_reason": alert_reason,
        "alert_source": alert_source,
        "detail": "",
    }


def load_last_week(date_str: str) -> Optional[dict]:
    """加载上周的港口数据"""
    current_date = datetime.strptime(date_str, "%Y-%m-%d")
    for delta in range(1, 15):
        prev_date = (current_date - timedelta(days=delta)).strftime("%Y-%m-%d")
        prev_file = DATA_DIR / f"{prev_date}.json"
        if prev_file.exists():
            try:
                with open(prev_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("ports"):
                    return data
            except Exception:
                continue
    return None


def build_fallback_port(port_key: str, date_str: str) -> dict:
    """构建降级港口数据"""
    port_config = PORTS[port_key]
    return {
        "port": port_config["name"],
        "status": "运行正常",
        "wait_days": port_config["default_wait"],
        "alert": False,
        "reason": "",
        "source": "",
        "source_url": "",
        "alternative": "",
        "detail": "外部数据源不可用，使用默认数据",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 主流程
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect_ports(date_str: str) -> dict:
    """采集港口动态的主函数"""
    print(f"⚓ 港口动态采集 — {date_str}")
    print("=" * 50)

    # 加载上周数据用于对比
    last_week_data = load_last_week(date_str)
    last_week_ports = {}
    if last_week_data:
        for p in last_week_data.get("ports", []):
            last_week_ports[p["port"]] = p

    result_ports = []
    success_count = 0
    fallback_count = 0

    for port_key, port_config in PORTS.items():
        port_name = port_config["name"]
        print(f"\n📡 采集 {port_name} ({port_config['name_en']}) ...")

        port_data = None
        sources_tried = []

        # 步骤 1: 尝试 MarineTraffic
        print(f"   [1/3] 尝试 MarineTraffic ...")
        sources_tried.append("marinetraffic")
        port_data = try_marinetraffic(port_key)
        if port_data:
            print(f"   ✅ MarineTraffic 数据获取成功")
        else:
            print(f"   ❌ MarineTraffic 不可用")

            # 步骤 2: 尝试港口官网
            print(f"   [2/3] 尝试港口官网 ...")
            sources_tried.append("port_website")
            port_data = try_port_website(port_key)
            if port_data:
                print(f"   ✅ 港口官网数据获取成功")
            else:
                print(f"   ❌ 港口官网不可用")

                # 步骤 3: 尝试 RSS
                print(f"   [3/3] 尝试 RSS 新闻 ...")
                sources_tried.append("rss")
                port_data = try_rss_news(port_key)
                if port_data:
                    print(f"   ✅ RSS 数据提取成功")
                else:
                    print(f"   ❌ RSS 无相关数据")

        # 构建端口条目
        if port_data:
            success_count += 1
            status = port_data["status"]
            wait_days = port_data.get("wait_days", port_config["default_wait"])
            alert = port_data.get("alert", False)
            detail = port_data.get("detail", "")
            alert_reason = port_data.get("alert_reason", "")
            alert_source = port_data.get("alert_source", "")
            data_source = port_data.get("source", "")
            source_url = port_data.get("source_url", "")

            # 如果有异常事件描述，加到状态前面
            if alert and port_data.get("alert_desc"):
                status = port_data['alert_desc']

            # 与上周数据对比
            prev = last_week_ports.get(port_name, {})
            if prev and not alert:
                prev_status = prev.get("status", "")
                prev_wait = prev.get("wait_days", "")
                if prev_wait and wait_days:
                    detail = f"上周等泊 {prev_wait} 天"
                    if wait_days != prev_wait:
                        detail = f"较上周({prev_wait}天)有变化"

            # 替代港口建议
            alternative = ""
            if alert and alert_reason:
                alternatives_map = {
                    "洛杉矶": "长滩/奥克兰（内支线加$200-350/40HQ）",
                    "鹿特丹": "汉堡/不来梅/安特卫普（等泊更短）",
                    "宁波": "上海/舟山（近洋替代）",
                    "上海": "宁波/舟山（近洋替代）",
                    "巴生": "新加坡/丹戎帕拉帕斯（近洋替代）",
                    "新加坡": "巴生/丹戎帕拉帕斯（近洋替代）",
                }
                alternative = alternatives_map.get(port_name, "咨询船公司替代航线")

            entry = {
                "port": port_name,
                "status": status,
                "wait_days": wait_days or port_config["default_wait"],
                "alert": alert,
                "reason": alert_reason,
                "source": data_source,
                "source_url": source_url,
                "alternative": alternative,
                "detail": detail,
            }
        else:
            # 降级: 使用默认数据
            fallback_count += 1
            entry = build_fallback_port(port_key, date_str)

            # 如果有上周数据，沿用上周的对比信息
            prev = last_week_ports.get(port_name, {})
            if prev:
                entry["wait_days"] = prev.get("wait_days", entry["wait_days"])
                entry["status"] = prev.get("status", entry["status"])
                entry["reason"] = prev.get("reason", "")
                entry["source"] = prev.get("source", "")
                entry["source_url"] = prev.get("source_url", "")
                entry["alternative"] = prev.get("alternative", "")
                if prev.get("alert"):
                    entry["alert"] = prev["alert"]
                    entry["status"] = f"{prev['status'].replace('⚠️ ', '')}（沿用上周）"

        result_ports.append(entry)

    result = {
        "date": date_str,
        "ports": result_ports,
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
    print(f"   港口成功/降级: {success_count}/{fallback_count}")
    print(f"   异常港口数: {sum(1 for p in result_ports if p.get('alert'))}")

    for p in result_ports:
        alert_mark = "⚠️" if p.get("alert") else "  "
        print(f"   {alert_mark} {p['port']}: {p['status']} (等泊 {p['wait_days']} 天)")

    print(f"{'─' * 50}")

    return result


def main():
    parser = argparse.ArgumentParser(description="港口动态采集器")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    # 验证日期格式
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"❌ 无效日期格式: {date_str}，请使用 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    result = collect_ports(date_str)


if __name__ == "__main__":
    main()

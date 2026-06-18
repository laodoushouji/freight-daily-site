#!/usr/bin/env python3
"""
深度文章生成器 — generate_articles.py

基于当日简报数据，选择 2-3 个最有价值的话题，生成货代视角深度分析文章。
输出: articles/{date}-*.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRIEFS_DIR = PROJECT_ROOT / "briefs"
ARTICLES_DIR = PROJECT_ROOT / "articles"

# 文章选题优先级权重
TOPIC_WEIGHTS = {
    "gri_effect": 10,       # GRI 生效 = 直接影响成本
    "port_alert": 9,        # 港口异常 = 直接影响交期
    "rate_rising": 8,       # 运价上涨 = 影响报价
    "rate_falling": 6,      # 运价下跌 = 锁价机会
    "new_route": 5,         # 新航线 = 新选择
    "blank_sailing": 7,     # 空班 = 舱位紧张
    "surcharge": 7,         # 附加费 = 成本上升
}


def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def pick_topics(brief: dict, max_topics: int = 3) -> List[dict]:
    """从简报中选择最有价值的话题"""
    candidates = []

    # 运价变化话题
    for r in brief.get("rate_snapshot", []):
        direction = r.get("direction", "→")
        if direction in ("▲", "▼"):
            weight = TOPIC_WEIGHTS["rate_rising"] if direction == "▲" else TOPIC_WEIGHTS["rate_falling"]
            candidates.append({
                "type": "rate_change",
                "weight": weight,
                "route": r["route"],
                "direction": direction,
                "note": r["note"],
                "title_hint": f"{r['route']}运价{'上涨' if direction == '▲' else '下跌'}分析"
            })

    # 船司动态话题
    for u in brief.get("carrier_updates", []):
        weight = 3
        topic_type = "carrier_news"
        if "GRI" in u:
            weight = TOPIC_WEIGHTS["gri_effect"]
            topic_type = "gri"
        elif "空班" in u:
            weight = TOPIC_WEIGHTS["blank_sailing"]
            topic_type = "blank_sailing"
        elif "附加费" in u:
            weight = TOPIC_WEIGHTS["surcharge"]
            topic_type = "surcharge"
        elif "新开" in u or "新航线" in u:
            weight = TOPIC_WEIGHTS["new_route"]
            topic_type = "new_route"

        candidates.append({
            "type": topic_type,
            "weight": weight,
            "detail": u,
            "title_hint": u[:30]
        })

    # 港口预警话题
    for p in brief.get("port_alerts", []):
        if "⚠️" in p:
            candidates.append({
                "type": "port_alert",
                "weight": TOPIC_WEIGHTS["port_alert"],
                "detail": p,
                "title_hint": p[:30]
            })

    # 按权重排序，取 top N
    candidates.sort(key=lambda x: x["weight"], reverse=True)
    return candidates[:max_topics]


def build_article_prompt(topic: dict, brief: dict, date_str: str) -> str:
    """构建文章生成 prompt"""
    topic_type = topic["type"]
    year = date_str[:4]
    month = date_str[5:7]

    # 根据话题类型选择文章模板
    if topic_type == "gri":
        title_template = f"GRI分析{topic.get('detail', '')[:15]}：{month}月涨价对货代的影响与应对"
        focus = "分析GRI的具体金额、生效时间、影响航线，给出货代企业如何提前布局的建议"
    elif topic_type == "port_alert":
        title_template = f"港口预警：{topic.get('detail', '')[:20]}，货代如何应对"
        focus = "分析港口异常的具体原因、预计持续时间、受影响航线，给出替代港口和出运方案"
    elif topic_type == "rate_rising":
        title_template = f"{topic.get('route', '')}运价{year}年{month}月上涨分析：货代报价策略调整"
        focus = "分析运价上涨原因、涨幅、与历史对比，给出货代如何调整报价和锁价策略"
    elif topic_type == "rate_falling":
        title_template = f"{topic.get('route', '')}运价{year}年{month}月走势：低点锁价窗口分析"
        focus = "分析运价下跌原因、是否触底、未来走势预判，给出是否锁长协的建议"
    elif topic_type == "blank_sailing":
        title_template = f"空班影响分析：{topic.get('detail', '')[:20]}"
        focus = "分析空班对舱位供给的影响、替代航线选择、订舱建议"
    elif topic_type == "surcharge":
        title_template = f"附加费解读：{topic.get('detail', '')[:20]}"
        focus = "分析附加费的具体金额、适用范围、与GRI的叠加效应"
    elif topic_type == "new_route":
        title_template = f"新航线解读：{topic.get('detail', '')[:20]}"
        focus = "分析新航线的挂靠港、航程、对现有航线格局的影响"
    else:
        title_template = f"航运市场{year}年{month}月动态分析"
        focus = "分析当前市场变化对货代业务的影响"

    # 构建完整 prompt
    brief_summary = json.dumps(brief, ensure_ascii=False, indent=2)[:2000]

    prompt = f"""你是一名有10年经验的货代行业分析师。请基于以下当日简报数据，写一篇800-1200字的深度分析文章。

## 文章标题
{title_template}

## 重点关注
{focus}

## 当日简报数据
{brief_summary}

## 文章结构要求（严格遵守）

---SECTION---标题
{title_template}

---SECTION---影响
⚡ 对货代的影响（30秒看懂）
用3-4条要点，每条1-2句话，从货代从业者视角直接说明影响。
不要写"建议关注"，要写"你的成本将增加X"或"你的客户可能延期X天"。

---SECTION---建议
💡 操作建议
2-3条可执行的建议，每条包含具体时间节点。
例如："7/1前完成XX航线订舱"、"经巴生中转的货改新加坡"。

---SECTION---正文
正文内容（600-900字）
- 用数据和事实说话，不用空话
- 可以引用简报中的具体价格和日期
- 分析因果关系，不做无根据的预测
- 用货代语言（舱位/GRI/即期/长协/等泊/跳港）

---SECTION---标签
货代,{topic.get('route', '航运')},{year}年,{month}月
"""
    return prompt


def create_article_json(topic: dict, brief: dict, date_str: str, article_id: int) -> dict:
    """创建文章 JSON 结构（不含 AI 生成的正文，正文由 Hermes cron 生成）"""
    topic_type = topic["type"]
    year = date_str[:4]
    month = date_str[5:7]

    # 生成 SEO 标题
    route = topic.get("route", "")
    if topic_type == "gri":
        seo_title = f"GRI涨价{month}月{route}：{year}年货代成本影响分析"
    elif topic_type == "port_alert":
        seo_title = f"港口异常{month}月：{year}年货代应对方案"
    elif topic_type in ("rate_rising", "rate_falling"):
        direction = "上涨" if topic_type == "rate_rising" else "下跌"
        seo_title = f"{route}运价{direction}{year}年{month}月：3个关键信号"
    else:
        seo_title = f"航运{topic_type}{year}年{month}月：货代影响与建议"

    return {
        "id": f"{date_str.replace('-', '')}-{article_id}",
        "date": date_str,
        "date_display": f"{year}年{month}月{date_str[8:10]}日",
        "seo_title": seo_title,
        "topic_type": topic_type,
        "topic_detail": topic.get("detail", topic.get("note", "")),
        "prompt": build_article_prompt(topic, brief, date_str),
        "impact": "",
        "action_tip": "",
        "body": "",
        "tags": [route, "货代", year, month],
        "generated": False
    }


def main():
    parser = argparse.ArgumentParser(description="生成深度文章选题和 prompt")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD")
    parser.add_argument("--max", type=int, default=3, help="最多生成几篇文章")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"📝 深度文章选题 — {date_str}")
    print("=" * 50)

    # 读取简报
    brief = load_json(BRIEFS_DIR / f"{date_str}.json")
    if not brief:
        print(f"❌ 未找到简报: {BRIEFS_DIR / date_str}.json")
        print("请先运行 generate_brief.py")
        sys.exit(1)

    # 选题
    topics = pick_topics(brief, max_topics=args.max)
    if not topics:
        print("⚠️ 无合适话题，跳过文章生成")
        sys.exit(0)

    # 生成文章 JSON
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    articles = []
    for i, topic in enumerate(topics, 1):
        article = create_article_json(topic, brief, date_str, i)
        articles.append(article)

        # 保存单篇文章
        slug = article["seo_title"][:20].replace(" ", "-")
        out_path = ARTICLES_DIR / f"{date_str.replace('-', '')}-{slug}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2)

        print(f"\n  [{i}/{len(topics)}] {article['seo_title']}")
        print(f"      类型: {topic['type']} | 权重: {topic['weight']}")
        print(f"      保存: {out_path.name}")

    # 更新索引
    index_path = ARTICLES_DIR / "_index.json"
    existing = load_json(index_path) or {"articles": []}
    # 移除同日期旧文章
    existing["articles"] = [
        a for a in existing["articles"]
        if not a.get("date") == date_str
    ]
    for a in articles:
        existing["articles"].append({
            "id": a["id"],
            "date": a["date"],
            "seo_title": a["seo_title"],
            "topic_type": a["topic_type"],
            "generated": False
        })
    existing["articles"].sort(key=lambda x: x.get("date", ""), reverse=True)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"\n──────────────────────────────────────────────────")
    print(f"✅ 生成 {len(articles)} 篇文章选题")
    print(f"   待 AI 生成正文（通过 Hermes cron 或手动执行）")


if __name__ == "__main__":
    main()

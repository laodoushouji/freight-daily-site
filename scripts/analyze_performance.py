#!/usr/bin/env python3
"""
迭代分析器 — analyze_performance.py

每2周运行一次：分析搜索关键词、反馈数据、调整内容策略。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ANALYTICS_DIR = DATA_DIR / "analytics"
FEEDBACK_DIR = DATA_DIR / "feedback"


def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def analyze_feedback() -> dict:
    """分析用户反馈数据"""
    if not FEEDBACK_DIR.exists():
        return {"status": "no_data", "message": "暂无反馈数据"}

    useful_count = 0
    outdated_count = 0
    by_topic = {}

    for f in sorted(FEEDBACK_DIR.glob("*.json")):
        data = load_json(f)
        if not data:
            continue
        for item in data.get("items", []):
            fb_type = item.get("feedback", "")
            if fb_type == "useful":
                useful_count += 1
            elif fb_type == "outdated":
                outdated_count += 1

    total = useful_count + outdated_count
    useful_rate = round(useful_count / total * 100, 1) if total > 0 else 0

    return {
        "total_feedback": total,
        "useful": useful_count,
        "outdated": outdated_count,
        "useful_rate": f"{useful_rate}%",
        "recommendation": "增加深度分析比例" if useful_rate > 70 else "优化内容质量" if useful_rate > 40 else "需要内容改进"
    }


def analyze_content_mix() -> dict:
    """分析内容配比"""
    import glob

    # 统计最近 14 天的文章类型
    articles_dir = PROJECT_ROOT / "articles"
    index = load_json(articles_dir / "_index.json")
    if not index:
        return {"status": "no_data"}

    articles = index if isinstance(index, list) else index.get("articles", [])

    type_counts = {}
    for a in articles:
        t = a.get("topic_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "total_articles": len(articles),
        "type_distribution": type_counts,
        "recommendation": "当前配比合理" if len(type_counts) >= 3 else "建议增加话题多样性"
    }


def generate_strategy_report() -> dict:
    """生成策略调整报告"""
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "feedback_analysis": analyze_feedback(),
        "content_mix": analyze_content_mix(),
        "title_strategy": {
            "current_template": "关键词+数字+年份",
            "收录率_estimate": "待数据（需Google Search Console接入）",
            "recommendation": "保持当前标题格式，待30天后根据收录数据调整"
        },
        "next_actions": []
    }

    # 生成下一步建议
    fb = report["feedback_analysis"]
    cm = report["content_mix"]

    if isinstance(fb, dict) and fb.get("useful_rate", "0%").replace("%", "").replace(".", "").isdigit():
        rate = float(fb["useful_rate"].replace("%", ""))
        if rate < 50:
            report["next_actions"].append("反馈有用率低于50%，建议提升文章实用性")

    if isinstance(cm, dict) and cm.get("type_distribution"):
        types = cm["type_distribution"]
        if types.get("port_alert", 0) > types.get("gri", 0) * 2:
            report["next_actions"].append("港口预警类文章过多，建议增加运价分析类")

    if not report["next_actions"]:
        report["next_actions"].append("当前策略表现良好，继续观察")

    return report


def main():
    print(f"📊 迭代分析 — {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 50)

    report = generate_strategy_report()

    # 保存报告
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANALYTICS_DIR / f"strategy-{report['date']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"\n📝 反馈分析:")
    fb = report["feedback_analysis"]
    if isinstance(fb, dict):
        print(f"   总反馈: {fb.get('total_feedback', 0)}")
        print(f"   有用率: {fb.get('useful_rate', 'N/A')}")
        print(f"   建议: {fb.get('recommendation', 'N/A')}")

    print(f"\n📝 内容配比:")
    cm = report["content_mix"]
    if isinstance(cm, dict):
        print(f"   总文章: {cm.get('total_articles', 0)}")
        for t, c in cm.get("type_distribution", {}).items():
            print(f"   {t}: {c}")
        print(f"   建议: {cm.get('recommendation', 'N/A')}")

    print(f"\n📝 下一步:")
    for a in report["next_actions"]:
        print(f"   ▸ {a}")

    print(f"\n✅ 报告已保存: {out_path}")


if __name__ == "__main__":
    main()

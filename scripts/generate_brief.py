#!/usr/bin/env python3
"""
简报生成器 — generate_brief.py

读取 data/ 下采集的数据，汇总生成每日决策简报 JSON。
输出: briefs/{date}.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BRIEFS_DIR = PROJECT_ROOT / "briefs"


def load_json(path: Path) -> Optional[dict]:
    """安全读取 JSON 文件"""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def generate_rate_snapshot(rates_data: Optional[dict]) -> list:
    """生成运价风向板块"""
    if not rates_data or not rates_data.get("routes"):
        return [{"route": "暂无数据", "direction": "→", "note": "数据源暂未更新，请稍后查看"}]

    snapshot = []
    for r in rates_data["routes"]:
        direction = r.get("direction", "→")
        price = r.get("price", "N/A")
        change = r.get("change", "$0")
        route = r.get("route", "未知航线")

        # 构建简洁注释
        if direction == "▲":
            note = f"上涨 {change}，当前 {price}"
        elif direction == "▼":
            note = f"下跌 {change}，当前 {price}"
        else:
            note = f"持平，当前 {price}"

        if not rates_data.get("updated", True):
            note += "（数据暂未更新）"

        snapshot.append({
            "route": route,
            "direction": direction,
            "note": note
        })

    return snapshot


def generate_carrier_updates(carriers_data: Optional[dict]) -> list:
    """生成船司动态板块"""
    if not carriers_data or not carriers_data.get("items"):
        return ["暂无船司公告更新"]

    updates = []
    for item in carriers_data["items"]:
        carrier = item.get("carrier", "未知")
        ctype = item.get("type", "其他")
        route = item.get("route", "")
        effective = item.get("effective", "")
        amount = item.get("amount", "")
        detail = item.get("detail", "")

        if ctype == "GRI":
            line = f"{carrier}：{effective}起 {route}GRI {amount}"
        elif ctype == "空班":
            line = f"{carrier}：{route}空班 {effective}"
        elif ctype == "新航线":
            line = f"{carrier}：新开{route}航线，{detail[:40]}"
        elif ctype == "附加费":
            line = f"{carrier}：{route}附加费 {amount}，{effective}起"
        else:
            line = f"{carrier}：{detail[:60]}" if detail else f"{carrier}：{ctype} {route}"

        updates.append(line)

    return updates


def generate_port_alerts(ports_data: Optional[dict]) -> list:
    """生成港口动态板块 — 含原因、消息源、替代方案"""
    if not ports_data or not ports_data.get("ports"):
        return ["暂无港口动态数据"]

    alerts = []
    for p in ports_data["ports"]:
        port = p.get("port", "未知")
        status = p.get("status", "")
        wait = p.get("wait_days", "N/A")
        alert = p.get("alert", False)
        reason = p.get("reason", "")
        source = p.get("source", "")
        alternative = p.get("alternative", "")
        detail = p.get("detail", "")

        if alert:
            parts = [f"{port}：⚠️"]
            if reason:
                parts.append(f"原因：{reason}")
            parts.append(f"等泊 {wait} 天")
            if alternative:
                parts.append(f"替代：{alternative}")
            if source:
                parts.append(f"来源：{source}")
            if detail:
                parts.append(detail)
            line = " | ".join(parts)
        else:
            line = f"{port}：{status}（等泊 {wait}）"
            if detail:
                line += f" {detail}"

        alerts.append(line)

    return alerts


def generate_action_summary(rates_data: Optional[dict],
                            carriers_data: Optional[dict],
                            ports_data: Optional[dict]) -> list:
    """生成操作建议板块 — 具体可执行，不是空话"""
    actions = []

    # 基于运价方向
    if rates_data and rates_data.get("routes"):
        falling = [r for r in rates_data["routes"] if r.get("direction") == "▼"]
        rising = [r for r in rates_data["routes"] if r.get("direction") == "▲"]

        if falling:
            routes_str = "、".join([r["route"] for r in falling[:2]])
            actions.append(f"{routes_str}运价处于低位，有出货计划的建议本周锁价")

        if rising:
            routes_str = "、".join([r["route"] for r in rising[:2]])
            actions.append(f"{routes_str}运价上涨中，尽快确认订舱避免成本上升")

    # 基于船司 GRI
    if carriers_data and carriers_data.get("items"):
        gri_items = [i for i in carriers_data["items"] if i.get("type") == "GRI"]
        surcharge_items = [i for i in carriers_data["items"] if i.get("type") == "附加费"]
        
        for g in gri_items[:2]:
            actions.append(
                f"{g['carrier']} {g['route']}GRI {g.get('amount','')} "
                f"{g.get('effective','')}生效，建议GRI生效前完成订舱"
            )
        for s in surcharge_items[:2]:
            actions.append(
                f"{s['carrier']} {s['route']}附加费 {s.get('amount','')} "
                f"{s.get('effective','')}起，锁定长协可免附加费"
            )

    # 基于港口预警 — 关键改动：带原因和替代方案
    if ports_data and ports_data.get("ports"):
        alert_ports = [p for p in ports_data["ports"] if p.get("alert", False)]
        for p in alert_ports[:3]:
            reason = p.get("reason", "异常")
            alternative = p.get("alternative", "咨询船公司替代航线")
            wait = p.get("wait_days", "N/A")
            actions.append(
                f"{p['port']}因{reason}等泊{wait}天 → {alternative}"
            )

    if not actions:
        actions.append("今日无明显风险信号，按正常节奏操作即可")

    return actions[:5]  # 最多5条


def generate_brief(date_str: str) -> dict:
    """生成完整简报"""
    # 读取当日数据
    rates_data = load_json(DATA_DIR / "rates" / f"{date_str}.json")
    carriers_data = load_json(DATA_DIR / "carriers" / f"{date_str}.json")
    ports_data = load_json(DATA_DIR / "ports" / f"{date_str}.json")

    # 尝试读前一天的数据做对比
    from datetime import timedelta
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        yesterday = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        yesterday = ""

    brief = {
        "date": date_str,
        "date_display": f"{date_str.replace('-', '年', 1).replace('-', '月', 1)}日",
        "rate_snapshot": generate_rate_snapshot(rates_data),
        "carrier_updates": generate_carrier_updates(carriers_data),
        "port_alerts": generate_port_alerts(ports_data),
        "action_summary": generate_action_summary(rates_data, carriers_data, ports_data),
        "meta": {
            "rates_updated": rates_data.get("updated", False) if rates_data else False,
            "carriers_count": len(carriers_data.get("items", [])) if carriers_data else 0,
            "ports_alert_count": sum(1 for p in (ports_data.get("ports", []) if ports_data else []) if p.get("alert", False))
        }
    }

    return brief


def main():
    parser = argparse.ArgumentParser(description="生成每日货代简报")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"📋 简报生成 — {date_str}")
    print("=" * 50)

    brief = generate_brief(date_str)

    # 保存
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BRIEFS_DIR / f"{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"\n📊 运价风向: {len(brief['rate_snapshot'])} 条")
    for r in brief["rate_snapshot"]:
        print(f"   {r['direction']} {r['route']}: {r['note']}")

    print(f"\n🚢 船司动态: {len(brief['carrier_updates'])} 条")
    for u in brief["carrier_updates"][:3]:
        print(f"   ▸ {u}")

    print(f"\n🏭 港口动态: {len(brief['port_alerts'])} 条")
    for p in brief["port_alerts"][:3]:
        print(f"   ▸ {p}")

    print(f"\n💡 操作建议: {len(brief['action_summary'])} 条")
    for a in brief["action_summary"]:
        print(f"   ▸ {a}")

    print(f"\n──────────────────────────────────────────────────")
    print(f"✅ 简报已保存: {out_path}")


if __name__ == "__main__":
    main()

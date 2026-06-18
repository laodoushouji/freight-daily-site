#!/usr/bin/env python3
"""
货代日报 - 数据迁移：给现有文章添加 impact + action_tip 字段
"""
import json, os

ARTICLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "articles")
ARTICLES_DIR = os.path.abspath(ARTICLES_DIR)
index_path = os.path.join(ARTICLES_DIR, "_index.json")

with open(index_path, "r", encoding="utf-8") as f:
    index = json.load(f)

# 给每篇文章添加货代影响和操作建议
enhancements = {
    "2025年干散货并购加速": {
        "impact": "干散货船东集中度提高，Capesize期租议价空间收窄；中长期合约客户优先，spot市场灵活性降低",
        "action_tip": "好望角型中长期合约建议提前锁定，关注合并后运力部署调整"
    },
    "2025集装箱运价风向标": {
        "impact": "欧线运价连跌3周处于调整期，是签约窗口；红海溢价仍在，不可抗力条款必加",
        "action_tip": "本周是欧线锁价窗口，合约加不可抗力+运价调整条款"
    },
    "2025VLCC租船纠纷升级": {
        "impact": "租船违约风险上升，运价倒挂是主因；合同审查需加强保障机制",
        "action_tip": "租船合同加信用证/银行保函，明确减租触发条件和仲裁条款"
    },
    "2025航运投资转向": {
        "impact": "化学品船运力短期趋紧，老旧船加速退出；干散货3-5年后可能运力过剩",
        "action_tip": "化工品货代提前规划化学品船运力，关注二手船价格走势作市场风向标"
    },
    "2025中国造船新订单": {
        "impact": "MR型成品油轮2027年交付，短期运力影响有限；中国船厂接单=更多空船回程货机会",
        "action_tip": "关注新船交付时间表预判2-3年运力供给，运营中国出发回程货的可寻找新机会"
    },
}

for entry in index:
    for key, enh in enhancements.items():
        if key in entry.get("title", ""):
            entry["impact"] = enh["impact"]
            entry["action_tip"] = enh["action_tip"]
            break
    # 确保字段存在
    entry.setdefault("impact", "")
    entry.setdefault("action_tip", "")

with open(index_path, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"Updated {len(index)} articles with impact + action_tip")

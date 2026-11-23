#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 生成 2026-11-23 文章正文（由 Hermes cron 执行）
今日船司数据源全部降级，三篇占位选题内容雷同。
处理：删除 2 篇占位稿，将 1 篇改写为基于当日真实运价/港口数据的深度文章。
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(BASE, "articles")
IDX = os.path.join(ART, "_index.json")

DROP_IDS = ["20261123-2", "20261123-3"]

# ---- 1. 删除占位雷同稿 ----
for aid in DROP_IDS:
    matches = [f for f in os.listdir(ART) if f.startswith(aid) and f.endswith(".json")]
    for m in matches:
        os.remove(os.path.join(ART, m))
        print(f"🗑️  已删除占位稿: {m}")

# ---- 2. 重写 20261123-1 为真实内容 ----
upd = {
    "seo_title": "运价全线持平11月底：欧线2700美元下的出货决策窗口（2026年11月）",
    "impact": (
        "⚡ 对货代的影响（30秒看懂）\n"
        "- 五大航线即期价全线持平：欧线 $2,700/40HQ、美西 $1,950、美东 $3,200、东南亚 $450/20GP、中东 $3,850/20GP——本周出货的海运费成本不变，报价有据可依。\n"
        "- 今日五大船司（MSC/Maersk/CMA CGM/ONE/COSCO）官网与RSS均未获取到经核实的公告——12月首周是船司集中宣告 GRI/附加费的传统窗口，你现在报出去的即期价大概率只保 7-10 天。\n"
        "- 六大监测港口无异常预警，但宁波等泊 3-5 天仍是全网最长：华东起运的货，交期按\"+2天\"报才安全。"
    ),
    "action_tip": (
        "💡 操作建议\n"
        "1. 今天起所有即期报价单有效期统一改 7 天，并加注\"12月1日起 GRI/附加费以船司公布为准\"——12月首周是宣告窗口，别用 30 天有效期的报价单接年底的单。\n"
        "2. 客户已确认出运计划（圣诞补单尾批/年底赶工货）：本周内按当前即期价锁定 12 月上旬舱位，欧线 $2,700/40HQ 处于年内偏低区间，锁舱即锁成本。\n"
        "3. 华东（尤其宁波）起运的货，截关时间统一提前 48 小时操作；宁波等泊 3-5 天未缓解前，对客户承诺交期按订舱时效 +2 天报。"
    ),
    "body": (
        "11月23日的市场，用一句话概括：运价不动，风险在暗处移动。五大航线即期价全线持平——欧线 $2,700/40HQ、美西 $1,950/40HQ、美东 $3,200/40HQ、东南亚 $450/20GP、中东 $3,850/20GP（Freightos 数据）。表面平静，但对货代来说，11月底这个时间点的\"持平\"恰恰是需要警惕的信号，而不是可以放松的理由。\n\n"
        "先说运价面。11月下旬是圣诞货出运的收尾阶段，传统上货量会逐步回落，运价持平说明船司当前的舱位管控还在托底——没有大面积放舱砸价，也没有动力推 GRI 拉涨。但注意历史规律：每年 12 月首周是船司集中宣告次年 1 月 GRI、旺季附加费（PSS）续期和年度费率调整的窗口。也就是说，你现在按 $2,700 报的欧线即期价，大概率只能保到 12 月上旬。报价单有效期还写着 30 天的同行，这个月接的年底单，很可能在 12 月第二周变成成本倒挂的单。\n\n"
        "再说信息面，这是今天最需要注意的一点。MSC、Maersk、CMA CGM、ONE、COSCO 五家的官网和 RSS 今日均未获取到经核实的公告——按本站的数据铁律，\"没有来源的消息不推送\"，所以今日船司动态栏显示为无公告，而不是编几条凑数。这对你意味着：任何从群里、同行转发里看到的\"船司要涨价/要空班\"消息，在去船司官网 tariff 页核对之前，都不要写进报价依据。尤其是临近 12 月宣告窗口，真假 GRI 消息会开始密集出现，这是每年年底传统节目。\n\n"
        "港口面整体健康：上海、洛杉矶、鹿特丹、新加坡、巴生等泊均在 1-4 天的正常区间，六大监测港口无一例异常预警。唯一要盯的是宁波——等泊 3-5 天，仍是全网最长。华东出口的舱位消化速度慢于其他区域，这意味着两点：一是华东起运的截关容错空间小，甩柜补订的成本远高于提前 48 小时操作；二是如果 12 月初船司在华东收紧舱位（年底控舱保价是常规操作），宁波的等泊时间会进一步拉长。\n\n"
        "操作上，本周的核心动作是三个字：锁、核、留。锁——已确认出运计划的客户，本周内按当前即期价锁定 12 月上旬舱位，欧线 $2,700 处于年内偏低区间，锁舱即锁成本，12 月宣告落地后这就是你的价差优势。核——所有报价单有效期改 7 天，加注\"12月1日起 GRI/附加费以船司公布为准\"；群传的涨价消息一律先上官网核对再进报价。留——华东起运统一提前 48 小时截关，交期承诺按订舱时效 +2 天报，给宁波的 3-5 天等泊留出缓冲。\n\n"
        "一句话总结：运价持平的窗口期，是拿来锁成本的，不是拿来观望的。本周锁完舱、改完报价模板，12 月的宣告潮来的时候，你就是拿旧价格出 12 月货的那一方。（数据来源：Freightos 运价指数、各船司官网/RSS 监测、港口拥堵监测，2026-11-23）"
    ),
    "tags": ["欧线运价", "GRI", "即期运价", "舱位", "2026年", "11月"],
    "generated": True,
}

matches = [f for f in os.listdir(ART) if f.startswith("20261123-1") and f.endswith(".json")]
if not matches:
    raise SystemExit("❌ 未找到 20261123-1 文件")
path = os.path.join(ART, matches[0])
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
data.update(upd)
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
print(f"✅ 已写入正文: {matches[0]}")

# ---- 3. 同步 _index.json ----
with open(IDX, encoding="utf-8") as fh:
    idx = json.load(fh)
items = idx if isinstance(idx, list) else idx.get("articles", [])
before = len(items)
items = [it for it in items if it.get("id") not in DROP_IDS]
removed = before - len(items)
for it in items:
    if it.get("id") == "20261123-1":
        it["seo_title"] = upd["seo_title"]
        it["tags"] = upd["tags"]
        it["generated"] = True
with open(IDX, "w", encoding="utf-8") as fh:
    json.dump(idx, fh, ensure_ascii=False, indent=2)
print(f"✅ 索引已同步: 删除 {removed} 项, 共 {len(items)} 篇")

#!/usr/bin/env python3
"""
货代日报 - Hermes Agent 内容生成辅助脚本
读取 Hermes 传入的新闻素材（JSON），输出文章框架提示词
此脚本不直接调用 LLM API，而是生成 prompt 供 Hermes Agent 处理
"""

import json
import sys
import os
import re
from datetime import datetime

def generate_prompts(articles_data):
    """为每条新闻生成一个 prompt，供 Hermes Agent 使用"""
    prompts = []
    for article in articles_data:
        title = article.get("title", "")
        summary = article.get("summary", "")
        source = article.get("source", "")
        category = article.get("category", "行业趋势")

        cat_map = {
            "海运": "海运运价",
            "航运": "航线变动",
            "物流": "行业趋势",
            "航贸": "报关政策",
            "港口": "港口动态",
            "空运": "空运动态",
            "趋势": "行业趋势",
            "报关": "报关政策",
        }
        cn_category = cat_map.get(category, "行业趋势")

        prompt = f"""基于以下国际货代航运新闻素材，撰写一篇中文行业日报文章。

【原始新闻】
标题：{title}
摘要：{summary}
来源：{source}

【要求】
1. 标题：包含关键词+具体信息+2025年，15-25字
2. 摘要：50-80字概括核心信息
3. 正文：800-1200字，分3-4个小节，每节有小标题
4. 内容必须包含：事件背景和现状、对货代/外贸企业的影响、行业趋势分析或建议
5. 正文使用 Markdown 格式
6. SEO关键词：5-8个
7. 标签：3-5个话题标签

【输出格式】严格按以下格式，方便脚本解析：
---TITLE---
文章标题
---SEO_TITLE---
SEO标题
---SUMMARY---
50-80字摘要
---KEYWORDS---
关键词1,关键词2,关键词3
---TAGS---
标签1,标签2,标签3
---CATEGORY---
{cn_category}
---BODY---
正文markdown内容
---END---"""
        prompts.append(prompt)

    return prompts


if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    articles = data.get("selected", data.get("articles", []))

    if not articles:
        print("[ERROR] No articles to process")
        sys.exit(1)

    prompts = generate_prompts(articles)
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "count": len(prompts),
        "prompts": prompts,
        "raw_articles": articles,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))

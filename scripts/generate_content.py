#!/usr/bin/env python3
"""
货代日报 - AI内容生成
使用免费大模型API将抓取的新闻素材生成SEO优化的中文日报文章
"""

import json
import sys
import os
import re
import markdown
from datetime import datetime

# 支持多种免费模型提供商
# 优先级: 环境变量 > 内置配置

def get_api_config():
    """获取API配置，支持多种免费模型"""
    configs = []

    # 1. 环境变量配置
    if os.environ.get("LLM_API_KEY") and os.environ.get("LLM_API_URL"):
        configs.append({
            "url": os.environ["LLM_API_URL"],
            "key": os.environ["LLM_API_KEY"],
            "model": os.environ.get("LLM_MODEL", "default"),
        })

    # 2. SiliconFlow (有免费额度)
    if os.environ.get("SILICONFLOW_API_KEY"):
        configs.append({
            "url": "https://api.siliconflow.cn/v1/chat/completions",
            "key": os.environ["SILICONFLOW_API_KEY"],
            "model": "Qwen/Qwen2.5-7B-Instruct",
        })

    # 3. DeepSeek (低价)
    if os.environ.get("DEEPSEEK_API_KEY"):
        configs.append({
            "url": "https://api.deepseek.com/v1/chat/completions",
            "key": os.environ["DEEPSEEK_API_KEY"],
            "model": "deepseek-chat",
        })

    # 4. Zhipu (智谱，有免费额度)
    if os.environ.get("ZHIPU_API_KEY"):
        configs.append({
            "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "key": os.environ["ZHIPU_API_KEY"],
            "model": "glm-4-flash",
        })

    # 5. 本地Ollama
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            if models:
                configs.append({
                    "url": "http://localhost:11434/api/chat",
                    "key": "ollama",
                    "model": models[0]["name"],
                    "type": "ollama",
                })
    except Exception:
        pass

    return configs


def call_llm(prompt, system_msg="你是一位资深国际货代行业分析师，擅长将行业新闻整理成专业、可读性强的中文日报文章。"):
    """调用LLM生成内容"""
    configs = get_api_config()
    if not configs:
        print("[ERROR] No LLM API configured. Set LLM_API_KEY+LLM_API_URL or install Ollama.")
        return None

    import requests

    for config in configs:
        try:
            if config.get("type") == "ollama":
                resp = requests.post(config["url"], json={
                    "model": config["model"],
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                }, timeout=120)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
            else:
                resp = requests.post(config["url"], headers={
                    "Authorization": f"Bearer {config['key']}",
                    "Content-Type": "application/json",
                }, json={
                    "model": config["model"],
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                }, timeout=60)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  [WARN] Failed with {config['model']}: {e}")
            continue

    return None


def generate_article(news_item):
    """基于单条新闻素材生成完整文章"""
    title = news_item.get("title", "")
    summary = news_item.get("summary", "")
    source = news_item.get("source", "")
    category = news_item.get("category", "")

    # 类别映射
    cat_map = {
        "海运": "海运运价",
        "航运": "航线变动",
        "物流": "行业趋势",
        "航贸": "报关政策",
    }
    cn_category = cat_map.get(category, "行业趋势")

    prompt = f"""基于以下国际货代航运新闻素材，撰写一篇中文行业日报文章。

【原始新闻】
标题：{title}
摘要：{summary}
来源：{source}
分类：{cn_category}

【要求】
1. 标题：包含关键词+具体信息+2025年，15-25字，例："2025年海运运价走势：欧线回落亚线稳中有升"
2. 摘要：50-80字概括核心信息
3. 正文：800-1200字，分3-4个小节，每节有小标题
4. 内容必须包含：
   - 事件背景和现状
   - 对货代/外贸企业的影响
   - 行业趋势分析或建议
5. SEO关键词：5-8个，用逗号分隔
6. 标签：3-5个话题标签

【输出格式】严格按以下JSON输出，不要添加其他内容：
```json
{{
  "title": "文章标题",
  "seo_title": "SEO标题(可不同于文章标题，更利于搜索)",
  "summary": "50-80字摘要",
  "keywords": "关键词1,关键词2,关键词3",
  "tags": ["标签1", "标签2", "标签3"],
  "category": "{cn_category}",
  "body_markdown": "正文markdown内容，含小标题"
}}
```"""

    result = call_llm(prompt)
    if not result:
        return None

    # 提取JSON
    try:
        # 尝试从markdown代码块中提取
        json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
        if json_match:
            article = json.loads(json_match.group(1))
        else:
            article = json.loads(result)
    except json.JSONDecodeError:
        # 如果JSON解析失败，手动构建
        article = {
            "title": title,
            "seo_title": f"{title} - 2025货代日报",
            "summary": summary[:100],
            "keywords": f"{cn_category},货代,国际物流",
            "tags": [cn_category, "货代"],
            "category": cn_category,
            "body_markdown": result,
        }

    return article


def md_to_html(md_text):
    """Markdown转HTML"""
    try:
        return markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
    except Exception:
        # 简单的fallback
        html = md_text
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\n\n', '</p><p>', html)
        return f'<p>{html}</p>'


if __name__ == "__main__":
    # 从stdin读取抓取结果
    input_data = json.loads(sys.stdin.read())
    selected = input_data.get("selected", [])

    if not selected:
        print("[ERROR] No articles to process")
        sys.exit(1)

    print(f"Generating articles for {len(selected)} news items...")

    results = []
    for i, news in enumerate(selected, 1):
        print(f"  [{i}/{len(selected)}] Processing: {news['title'][:50]}...")
        article = generate_article(news)
        if article:
            article["source_news"] = news
            article["body_html"] = md_to_html(article.get("body_markdown", ""))
            results.append(article)
            print(f"    -> Generated: {article.get('title', 'UNTITLED')[:50]}")
        else:
            print(f"    -> FAILED")

    output = {
        "generated_at": datetime.now().isoformat(),
        "count": len(results),
        "articles": results,
    }

    print(f"\nGenerated {len(results)} articles")
    print("--- JSON OUTPUT ---")
    print(json.dumps(output, ensure_ascii=False, indent=2))

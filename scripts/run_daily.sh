#!/bin/bash
# 货代日报 - 一键生成+构建+部署
# 用法: bash run_daily.sh [--skip-push]

set -euo pipefail
cd "$(dirname "$0")/.."
SITE_DIR="$(pwd)"

echo "========================================="
echo "  货代日报 - Daily Run"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

SKIP_PUSH=false
if [[ "${1:-}" == "--skip-push" ]]; then
    SKIP_PUSH=true
fi

# Step 1: 抓取新闻
echo ""
echo "[1/4] Fetching news sources..."
FETCH_OUTPUT=$(python3 scripts/fetch_news.py 2>&1)
FETCH_JSON=$(echo "$FETCH_OUTPUT" | sed -n '/^--- JSON OUTPUT ---$/,/^$/p' | tail -n +2)
ARTICLE_COUNT=$(echo "$FETCH_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_fetched',0))" 2>/dev/null || echo "0")
echo "  Fetched: $ARTICLE_COUNT articles"

if [[ "$ARTICLE_COUNT" == "0" ]]; then
    echo "[WARN] No articles fetched. Will try to generate from fallback topics."
    # Fallback: 生成行业通用话题
    FETCH_JSON=$(python3 -c "
import json, datetime
topics = [
    {'title': 'Container Shipping Rates Weekly Update', 'summary': 'Latest container shipping rate trends on major trade lanes', 'source': 'Auto-generated', 'category': '海运', 'lang': 'en', 'date': datetime.date.today().isoformat()},
    {'title': 'Port Congestion Report Major Hubs', 'summary': 'Current congestion status at major global ports', 'source': 'Auto-generated', 'category': '港口', 'lang': 'en', 'date': datetime.date.today().isoformat()},
    {'title': 'Air Freight Market Monthly Overview', 'summary': 'Air cargo capacity and rate developments', 'source': 'Auto-generated', 'category': '空运', 'lang': 'en', 'date': datetime.date.today().isoformat()},
    {'title': 'Customs Policy Updates China Trade', 'summary': 'Recent customs regulation changes affecting China trade', 'source': 'Auto-generated', 'category': '报关', 'lang': 'en', 'date': datetime.date.today().isoformat()},
    {'title': 'Freight Forwarding Industry Trends 2025', 'summary': 'Digital transformation and market outlook for freight forwarders', 'source': 'Auto-generated', 'category': '趋势', 'lang': 'en', 'date': datetime.date.today().isoformat()},
]
print(json.dumps({'fetched_at': datetime.datetime.now().isoformat(), 'total_fetched': len(topics), 'selected': topics}, ensure_ascii=False))
")
fi

# Step 2: AI生成内容
echo ""
echo "[2/4] Generating articles with AI..."
GEN_OUTPUT=$(echo "$FETCH_JSON" | python3 scripts/generate_content.py 2>&1)
GEN_JSON=$(echo "$GEN_OUTPUT" | sed -n '/^--- JSON OUTPUT ---$/,/^$/p' | tail -n +2)
GEN_COUNT=$(echo "$GEN_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
echo "  Generated: $GEN_COUNT articles"

if [[ "$GEN_COUNT" == "0" ]]; then
    echo "[ERROR] No articles generated. Check LLM API config."
    exit 1
fi

# Step 3: 构建站点
echo ""
echo "[3/4] Building site..."
BUILD_OUTPUT=$(echo "$GEN_JSON" | python3 scripts/build_site.py 2>&1)
echo "  $BUILD_OUTPUT"

# Step 4: Git push部署
echo ""
if [[ "$SKIP_PUSH" == "true" ]]; then
    echo "[4/4] Skipping git push (--skip-push)"
else
    echo "[4/4] Pushing to GitHub..."
    cd "$SITE_DIR"
    git add -A
    CHANGES=$(git diff --cached --stat)
    if [[ -n "$CHANGES" ]]; then
        DATE=$(date '+%Y-%m-%d')
        git commit -m "daily: ${DATE} 货代日报更新 - ${GEN_COUNT}篇"
        git push origin main 2>&1 || echo "[WARN] Push failed, will retry next run"
        echo "  Pushed to GitHub!"
    else
        echo "  No changes to push"
    fi
fi

echo ""
echo "========================================="
echo "  Done! $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Articles today: $GEN_COUNT"
echo "========================================="

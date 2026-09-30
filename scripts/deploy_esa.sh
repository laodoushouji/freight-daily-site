#!/bin/bash
# ESA 国内站部署（降级方案）
# 背景：整仓 assets 会触发 totalfilecountexceed（文件数超限），
# 所以只打包首页+最新200篇文章+静态资源到临时目录再部署。
# 默认域名当前返回 401（Authorization Required），待控制台排查路由/鉴权配置。
set -e
SITE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PKG=/tmp/esa-pkg

rm -rf "$PKG"
mkdir -p "$PKG/assets"

cp "$SITE_DIR/index.html" "$SITE_DIR/about.html" "$SITE_DIR/archive.html" \
   "$SITE_DIR/robots.txt" "$SITE_DIR/rss.xml" "$SITE_DIR/sitemap.xml" "$PKG/" 2>/dev/null || true
cp -r "$SITE_DIR/assets/." "$PKG/assets/"

python3 - "$SITE_DIR" "$PKG" <<'EOF'
import json, shutil, os, sys
site, pkg = sys.argv[1], sys.argv[2]
idx = json.load(open(os.path.join(site, 'articles/_index.json')))
sel = idx[:200]
os.makedirs(os.path.join(pkg, 'articles'), exist_ok=True)
json.dump(sel, open(os.path.join(pkg, 'articles/_index.json'), 'w'), ensure_ascii=False, indent=1)
for a in sel:
    for f in os.listdir(os.path.join(site, 'articles')):
        if f.startswith(a['id']) and f.endswith('.html'):
            shutil.copy(os.path.join(site, 'articles', f), os.path.join(pkg, 'articles', f))
            break
EOF

cat > "$PKG/esa.jsonc" <<'EOF'
{
  "name": "freight-daily",
  "assets": {
    "directory": "."
  }
}
EOF

cd "$PKG"
esa deploy --assets . --environment production --description "daily $(date +%Y-%m-%d)" --no-bundle

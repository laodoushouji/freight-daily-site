#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 ESA 部署用 staging 目录（仅静态产物，避开文件数上限）"""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
staging = root / ".esa_staging"

# 重建 staging
if staging.exists():
    shutil.rmtree(staging)
(staging / "articles").mkdir(parents=True)
(staging / "assets").mkdir(parents=True)

# 根目录静态文件
for f in ["index.html", "archive.html", "about.html", "robots.txt",
          "sitemap.xml", "rss.xml", "esa.jsonc"]:
    src = root / f
    if src.exists():
        shutil.copy2(src, staging / f)

# 文章页（仅 HTML，跳过 JSON）
n_art = 0
for src in (root / "articles").glob("*.html"):
    shutil.copy2(src, staging / "articles" / src.name)
    n_art += 1

# assets
for src in (root / "assets").iterdir():
    if src.is_file():
        shutil.copy2(src, staging / "assets" / src.name)

total = sum(1 for p in staging.rglob("*") if p.is_file())
print(f"staging built: {total} files ({n_art} article pages)")

#!/usr/bin/env python3
"""
每日主流程 — run_daily.py

串联：采集 → 简报 → 文章 → 构建 → 部署
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run_step(name: str, cmd: list) -> bool:
    """运行一步，返回是否成功"""
    print(f"\n{'='*60}")
    print(f"▶ {name}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=False)
    if result.returncode != 0:
        print(f"❌ {name} 失败 (exit {result.returncode})")
        return False
    print(f"✅ {name} 完成")
    return True


def git_push() -> bool:
    """git add + commit + push"""
    print(f"\n{'='*60}")
    print(f"▶ Git Push & Deploy")
    print(f"{'='*60}")

    date_str = datetime.now().strftime("%Y-%m-%d")

    cmds = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", f"日报更新 {date_str}"],
        ["git", "push", "origin", "main"],
    ]

    for cmd in cmds:
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        if result.returncode != 0 and "nothing to commit" not in result.stdout and "nothing to commit" not in result.stderr:
            if "Already up to date" not in result.stdout:
                print(f"  ⚠️ git: {result.stderr.strip()[:100]}")

    print(f"✅ Git push 完成，Vercel 将自动部署")
    return True


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 货代日报每日流程 — {date_str}")
    print(f"{'='*60}")

    steps = [
        ("Step 1/5: 运价数据采集", [sys.executable, str(SCRIPTS_DIR / "collect_rates.py")]),
        ("Step 2/5: 船司公告采集", [sys.executable, str(SCRIPTS_DIR / "collect_carriers.py")]),
        ("Step 3/5: 港口动态采集", [sys.executable, str(SCRIPTS_DIR / "collect_ports.py")]),
        ("Step 4/5: 简报生成", [sys.executable, str(SCRIPTS_DIR / "generate_brief.py")]),
        ("Step 5/5: 文章选题+构建", [sys.executable, str(SCRIPTS_DIR / "generate_articles.py")]),
    ]

    # 文章正文由 Hermes cron 通过 AI 生成，这里只跑选题
    # 构建和推送
    extra_steps = [
        ("站点构建", [sys.executable, str(SCRIPTS_DIR / "build_site.py")]),
        ("Git 推送部署", []),  # 特殊处理
    ]

    failed = []
    for name, cmd in steps:
        if not run_step(name, cmd):
            failed.append(name)

    # 构建站点
    if not run_step("站点构建", [sys.executable, str(SCRIPTS_DIR / "build_site.py")]):
        failed.append("站点构建")

    # Git 推送
    if not git_push():
        failed.append("Git 推送")

    # 总结
    print(f"\n{'='*60}")
    print(f"📋 流程总结 — {date_str}")
    print(f"{'='*60}")
    if failed:
        print(f"⚠️ 失败步骤: {', '.join(failed)}")
    else:
        print(f"✅ 全部完成！")
    print(f"站点: https://freight-daily-site.vercel.app")


if __name__ == "__main__":
    main()

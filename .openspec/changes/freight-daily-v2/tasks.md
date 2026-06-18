# Tasks: freight-daily-v2

## 1. 项目结构重组
- [ ] 1.1 创建 `data/` 目录及子目录 `rates/`, `carriers/`, `ports/`, `feedback/`, `analytics/`
- [ ] 1.2 创建 `scripts/collect_rates.py` 骨架（空文件，import 声明）
- [ ] 1.3 创建 `scripts/collect_carriers.py` 骨架
- [ ] 1.4 创建 `scripts/collect_ports.py` 骨架
- [ ] 1.5 创建 `scripts/generate_brief.py` 骨架
- [ ] 1.6 创建 `scripts/generate_articles.py` 骨架
- [ ] 1.7 创建 `scripts/run_daily.py` 骨架
- [ ] 1.8 创建 `scripts/analyze_performance.py` 骨架

## 2. 运价数据采集器
- [ ] 2.1 实现 SCFI 指数抓取：请求上海航运交易所页面，解析 SCFI 及各航线分项数据
- [ ] 2.2 实现 Freightos 指数抓取：请求 freightos.com 公开页面，提取集装箱运价
- [ ] 2.3 实现数据对比逻辑：本周 vs 上周，计算涨跌方向和幅度
- [ ] 2.4 实现降级逻辑：主源失败切备用源，全部失败保留上周数据并标注
- [ ] 2.5 实现数据存储：写入 `data/rates/{date}.json`，格式为 `{date, source, routes: [{route, price, change, direction}]}`

## 3. 船司公告采集器
- [ ] 3.1 实现 MSC 公告页抓取：请求 MSC 新闻页，提取 GRI/空班/新航线信息
- [ ] 3.2 实现马士基公告页抓取
- [ ] 3.3 实现 CMA 公告页抓取
- [ ] 3.4 实现 ONE 公告页抓取
- [ ] 3.5 实现中远公告页抓取
- [ ] 3.6 实现单家失败不阻塞其余的容错逻辑
- [ ] 3.7 实现数据存储：写入 `data/carriers/{date}.json`

## 4. 港口动态采集器
- [ ] 4.1 实现 MarineTraffic 港口等泊数据抓取（6 个目标港口）
- [ ] 4.2 实现异常事件检测（罢工/台风/封闭 → ⚠️ 标记）
- [ ] 4.3 实现数据存储：写入 `data/ports/{date}.json`

## 5. 简报生成器
- [ ] 5.1 实现简报 JSON 生成：读取当日 data/ 下所有 JSON，汇总为 briefs/{date}.json
- [ ] 5.2 实现运价风向板块：方向箭头 + 价格 + 周度变化
- [ ] 5.3 实现船司动态板块：GRI/空班/新航线摘要
- [ ] 5.4 实现港口预警板块：等泊天数 + ⚠️ 标记
- [ ] 5.5 实现操作建议板块：基于数据的规则模板（GRI 前订舱、预警港口替代方案）

## 6. 深度文章生成器
- [ ] 6.1 实现选题逻辑：从简报数据中选择变化最大的 2-3 个话题
- [ ] 6.2 实现文章生成：AI 基于简报数据写 800-1200 字深度分析
- [ ] 6.3 实现"⚡ 对货代的影响"板块自动生成
- [ ] 6.4 实现"💡 操作建议"板块自动生成
- [ ] 6.5 实现 SEO 标题生成：关键词+数字+年份格式
- [ ] 6.6 实现文章 JSON 存储：写入 `articles/` 目录

## 7. 站点构建器重写
- [ ] 7.1 重写 build_site.py：支持简报+文章双模式渲染
- [ ] 7.2 更新 index.html 模板：从 briefs JSON 渲染信息面板
- [ ] 7.3 更新 article.html 模板：确保货代影响+操作建议在正文前
- [ ] 7.4 实现 sitemap.xml 自动更新
- [ ] 7.5 实现 rss.xml 自动更新

## 8. 每日主流程
- [ ] 8.1 实现 run_daily.py：串联采集→简报→文章→构建→推送
- [ ] 8.2 实现钉钉推送：简报摘要发到钉钉 webhook
- [ ] 8.3 实现 git push 自动触发 Vercel 部署

## 9. 用户反馈机制
- [ ] 9.1 在文章页和简报板块加"有用"/"过时"按钮
- [ ] 9.2 实现反馈数据收集（静态站用 fetch → JSON 文件方案）
- [ ] 9.3 实现反馈数据存储到 `data/feedback/`

## 10. 自我迭代机制
- [ ] 10.1 实现 analyze_performance.py：每 2 周分析搜索关键词和反馈数据
- [ ] 10.2 实现内容策略调整：根据分析结果调整生成参数
- [ ] 10.3 实现标题策略进化：对比收录率切换标题模板
- [ ] 10.4 设置分析 cron：每 2 周 1 次

## 11. Cron 和 Skill 更新
- [ ] 11.1 更新 Hermes cron prompt 适配新流程
- [ ] 11.2 更新 freight-daily-site skill 文档
- [ ] 11.3 更新 memory 记录新架构

## 12. 端到端验证
- [ ] 12.1 运行完整流程：采集→简报→文章→构建→部署
- [ ] 12.2 验证线上站点渲染正确
- [ ] 12.3 验证钉钉推送成功
- [ ] 12.4 验证 cron 可自动运行

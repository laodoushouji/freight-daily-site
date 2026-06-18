# Spec: feedback-loop

## ADDED Requirements

### Requirement: 用户反馈收集

页面必须提供轻量反馈机制。

#### Scenario: 有用/过时按钮
- **WHEN** 用户点击文章或简报板块的"有用"或"过时"按钮
- **THEN** 系统记录反馈到 `data/feedback/{date}.json`，包含文章ID、板块、反馈类型、时间戳

#### Scenario: 反馈数据聚合
- **WHEN** 反馈数据累积超过 7 天
- **THEN** 系统按板块统计"有用率"，作为内容策略调整的输入

### Requirement: 搜索流量分析

系统必须定期分析搜索引擎带来的流量。

#### Scenario: 关键词分析
- **WHEN** 每两周运行一次流量分析
- **THEN** 提取带来流量最高的 10 个搜索关键词，输出到 `data/analytics/keywords.json`

#### Scenario: 内容策略调整
- **WHEN** 某类关键词流量占比超过 30%
- **THEN** 自动增加该类内容在每日生成中的比例

### Requirement: 标题策略进化

标题策略必须基于收录数据自动优化。

#### Scenario: 收录率检测
- **WHEN** 每周检测 Google/百度收录情况
- **THEN** 对比不同标题格式的收录率，记录到 `data/analytics/title-strategy.json`

#### Scenario: 策略切换
- **WHEN** "数字+年份"标题格式的收录率比纯描述格式高 2x 以上
- **THEN** 自动切换为高收录率标题模板

# Spec: daily-brief

## ADDED Requirements

### Requirement: 每日简报自动生成

系统必须基于采集数据自动生成每日决策简报。

#### Scenario: 完整简报生成
- **WHEN** 数据采集完成且当天尚未生成简报
- **THEN** 系统生成包含运价风向、船司动态、港口预警、操作建议四个板块的简报 JSON

#### Scenario: 数据不完整时的简报
- **WHEN** 部分数据源采集失败
- **THEN** 系统用已有数据生成简报，缺失板块标注"数据暂无"，不阻塞发布

### Requirement: 运价风向板块

运价数据必须以方向箭头+具体价格+周度变化呈现。

#### Scenario: 运价方向判断
- **WHEN** 本周 SCFI 航线指数高于上周
- **THEN** 该航线标记 ▲，并附具体价格和变化幅度

#### Scenario: 运价持平
- **WHEN** 本周与上周指数差异 < 2%
- **THEN** 该航线标记 →

### Requirement: 操作建议板块

操作建议必须可执行、有具体时间节点。

#### Scenario: GRI 前订舱建议
- **WHEN** 船司公告 GRI 在未来 7 天内生效
- **THEN** 操作建议包含"GRI 前抓紧订舱"并注明生效日期和金额

#### Scenario: 港口异常替代方案
- **WHEN** 某港口标记 ⚠️ 预警
- **THEN** 操作建议包含替代港口或提前出运方案

### Requirement: 简报持久化

简报必须持久化存储以供历史查询和趋势分析。

#### Scenario: 简报存档
- **WHEN** 简报生成完成
- **THEN** 存入 `briefs/{date}.json`，同时构建为首页 HTML

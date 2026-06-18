# Spec: data-pipeline

## ADDED Requirements

### Requirement: 运价数据自动采集

系统必须从公开数据源自动采集集装箱运价指数数据。

#### Scenario: SCFI 周度数据采集
- **WHEN** 每周五 SCFI 发布新数据
- **THEN** 系统在下一个 cron 周期自动采集 SCFI 指数及各航线分项数据，存入 `data/rates/` 目录

#### Scenario: 数据源不可用降级
- **WHEN** 主数据源（SCFI）无法访问
- **THEN** 系统尝试备用数据源（Freightos），如果全部失败则保留上周数据并在简报中标注"数据暂未更新"

### Requirement: 船司公告采集

系统必须从主要船司官网采集 GRI、空班、新航线、附加费公告。

#### Scenario: MSC GRI 公告采集
- **WHEN** MSC 官网发布新的 GRI 通知
- **THEN** 系统提取生效日期、航线、金额，结构化存入 `data/carriers/` 目录

#### Scenario: 多船司采集
- **WHEN** cron 运行时
- **THEN** 系统依次采集 MSC、马士基、CMA、ONE、中远 5 家船司的最新公告，不因单家失败阻塞其余

### Requirement: 港口动态采集

系统必须采集主要港口的拥堵/等泊信息。

#### Scenario: 港口等泊数据采集
- **WHEN** cron 运行时
- **THEN** 系统采集宁波、上海、洛杉矶、鹿特丹、巴生、新加坡 6 个港口的等泊天数和拥堵状态

#### Scenario: 罢工/异常预警
- **WHEN** 某港口出现罢工/台风/封闭等异常事件
- **THEN** 系统在港口动态中标记 ⚠️ 预警标签

### Requirement: 数据结构化存储

所有采集数据必须以 JSON 格式结构化存储。

#### Scenario: 数据文件命名
- **WHEN** 数据采集完成
- **THEN** 文件按 `data/{category}/{date}.json` 格式存储，category 为 rates/carriers/ports 之一

#### Scenario: 数据去重
- **WHEN** 同一天重复运行采集
- **THEN** 后续运行覆盖当天文件，不产生重复记录

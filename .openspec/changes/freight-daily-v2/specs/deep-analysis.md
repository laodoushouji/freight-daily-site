# Spec: deep-analysis

## ADDED Requirements

### Requirement: 深度分析文章生成

系统必须基于当日简报数据生成 2-3 篇货代视角的深度分析文章。

#### Scenario: 文章选题自动判断
- **WHEN** 当日简报生成完成
- **THEN** 系统从运价/船司/港口三个维度中选择变化最大的 2-3 个话题生成深度分析

#### Scenario: 文章必须包含货代影响
- **WHEN** 深度文章生成
- **THEN** 每篇文章必须包含"⚡ 对货代的影响（30秒看懂）"板块，用货代从业者视角解读

#### Scenario: 文章必须包含操作建议
- **WHEN** 深度文章生成
- **THEN** 每篇文章必须包含"💡 操作建议"板块，给出具体可执行的行动项

### Requirement: 文章 SEO 优化

每篇文章必须优化搜索引擎收录。

#### Scenario: 标题格式
- **WHEN** 文章生成
- **THEN** 标题格式为"关键词+数字+年份"，例如"欧线运价2026年7月走势：3个关键信号"

#### Scenario: 结构化数据
- **WHEN** 文章 HTML 生成
- **THEN** 包含 Schema.org Article 标记和 Open Graph 元标签

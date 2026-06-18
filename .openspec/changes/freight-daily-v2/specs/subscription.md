# Spec: subscription

## ADDED Requirements

### Requirement: 钉钉推送

每日简报必须推送到钉钉频道。

#### Scenario: 每日推送
- **WHEN** 简报生成并构建完成
- **THEN** 系统将简报摘要推送到配置的钉钉 webhook，包含运价风向和操作建议

#### Scenario: 推送失败不阻塞
- **WHEN** 钉钉 webhook 调用失败
- **THEN** 记录错误日志，不影响站点发布

### Requirement: 按航线订阅（未来）

用户可以按航线订阅特定推送。

#### Scenario: 订阅欧线动态
- **WHEN** 用户选择订阅"欧线"更新
- **THEN** 仅当欧线运价变化超过阈值或欧线有重要船司公告时推送通知

注意：此需求标记为 v2.1，v2.0 不实现。

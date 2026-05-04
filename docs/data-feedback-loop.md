# 数据闭环与用户偏好更新设计

## 1. 设计目标

本阶段为系统加入数据闭环能力，让每次执行不只是返回结果，还能形成可追踪的使用事件，并根据行为生成用户偏好更新。

核心链路：

```text
ExecutionResult
  -> UsageEvent
  -> usage_events.jsonl
  -> PreferenceUpdate
  -> preference_updates.jsonl
  -> 网页展示 / 后续画像更新
```

## 2. 当前实现

新增模块：

- `feedback/usage_logger.py`
- `feedback/preference_updater.py`
- `feedback/feedback_service.py`

运行数据默认写入：

```text
runtime/usage_events.jsonl
runtime/preference_updates.jsonl
```

`runtime/` 已加入 `.gitignore`，避免运行数据进入版本库。

## 3. UsageEvent

每次执行记录以下字段：

- request_id
- user_id
- user_input
- command_type
- safety
- network
- execution_status
- output
- timestamp

这类结构化事件后续可以用于：

- 用户画像更新。
- 行为分析。
- 模型评估。
- 线上问题追踪。

## 4. PreferenceUpdate

当前偏好更新使用规则模拟：

- 导航成功：`路线偏好高速 +1`
- 打开座椅加热：`座椅加热偏好 +1`
- 充电规划：`补能提醒关注 +1`
- 危险指令拦截：不更新偏好

示例：

```text
打开座椅加热
  -> UsageEvent(command_type=CAR_CONTROL)
  -> PreferenceUpdate(comfort_seat_heat +1)
```

## 5. 接入方式

`VehicleCoreService` 支持可选注入：

```python
VehicleCoreService(feedback_service=FeedbackService())
```

这样核心测试可以不写运行文件，而控制台和网页演示可以真实记录数据闭环。

## 6. 网页展示

网页新增“数据闭环”区域，展示：

- 事件记录状态。
- usage log 文件路径。
- 本次偏好更新说明。

面试时可以用它说明系统不是一次性问答，而是具备后续持续优化的基础。

## 7. 工程取舍

当前使用 JSONL 而不是数据库，原因是：

- 保持 offline 可运行。
- 便于观察和调试。
- 写入逻辑简单可靠。
- 后续可以替换为 SQLite、PostgreSQL、Kafka 或埋点平台。

面试表达：

> 我没有只做单次请求响应，而是加入了数据闭环。每次执行会生成结构化 UsageEvent，并基于规则生成 PreferenceUpdate。第一版用 JSONL 模拟，后续可以迁移到数据库、埋点平台或用户画像服务。

## 8. 后续升级路径

推荐升级：

```text
JSONL
  -> SQLite
  -> 用户画像表
  -> 行为聚合任务
  -> 画像向量化
  -> 实时推荐 / 个性化决策
```

更进一步可以加入：

- 用户偏好权重累计。
- 行程结束总结。
- 负反馈入口。
- 隐私脱敏。
- 数据保留策略。

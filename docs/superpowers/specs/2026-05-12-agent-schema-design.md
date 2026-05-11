# Agent 消息 Schema 设计

## 背景

当前项目已经具备 `Message`、`TraceEvent`、Provider 结果、前端观测面板等结构，但 Agent 之间仍有一部分数据通过 dict 或局部 dataclass 传递。下一步需要把“Agent 间不是随便传字符串”的工程边界表达清楚，同时避免大规模重构造成稳定链路回退。

## 目标

新增统一 Agent 消息 schema，用于描述意图、车辆状态、Provider 输出、Agent 观测和最终执行结果。第一阶段只做兼容式升级：保留现有 `Message` 和 `ExecutionResult`，新增转换入口，让既有业务代码可以逐步迁移。

## 设计

新增 `core/agent_schema.py`，定义：

- `IntentFrame`：一次用户输入的结构化意图帧。
- `VehicleStateFrame`：车辆状态快照。
- `ProviderResultFrame`：外部 Provider 或内部工具调用的标准结果。
- `AgentTraceFrame`：单个 Agent 的观测帧，可承载多个工具输出。
- `ExecutionResultFrame`：最终执行结果的统一结构。

`Message` 增加：

- `to_dict()`
- `to_intent_frame(...)`

`ExecutionResult` 增加：

- `to_frame()`
- `to_dict()`

## 边界

本次不强制改造全部 Agent 内部逻辑，不引入 pydantic，不改变前端 API 字段结构。Schema 先作为稳定协议层存在，后续可逐步替换散落的 dict。

## 测试

新增 `tests/test_agent_schema.py`，覆盖：

- `Message` 转 `IntentFrame`
- dict 与车辆状态对象转 `VehicleStateFrame`
- `TraceEvent` 转 `ProviderResultFrame`
- `ExecutionResult` 转 `ExecutionResultFrame`
- 所有 frame 可序列化为 dict，枚举统一输出字符串值

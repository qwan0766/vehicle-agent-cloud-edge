# 系统架构说明

更新时间：2026-05-06

## 1. 架构口径

本项目已从最初 demo 结构重构为课程附件对齐的交付结构：

```text
八大业务 Agent + 一个全局调度编排器 + 三层端云协同架构
```

八大业务 Agent 是业务能力单元；`GlobalDispatchAgent` 是云端编排器，负责拆任务、调工具、合并结果，不计入八大业务 Agent。当前编排层已经抽象为显式图执行：默认尝试真实 LangGraph `StateGraph`；如果未安装 `langgraph`，自动回退到项目内置 lightweight graph；设置 `ENABLE_LANGGRAPH=0` 时可强制只走 lightweight graph。

## 2. 三层架构

- 车载执行层：`LocalIntentAgent`、`GlobalSafetyDispatchAgent`、`CabinVehicleControlAgent`、`DataUploadAgent`。
- 端云通信层：统一 `Message` 协议，封装用户、意图、安全等级、网络状态和指令内容。
- 云端决策层：`GlobalDispatchAgent` 编排 `GlobalTripPlanningAgent`、`UserProfileAgent`、`VectorKnowledgeAgent`、`ExternalEcologyAgent`。

## 2.1 默认启用 LangGraph 编排

云端图节点与 Agent/tool 对应：

```text
profile -> knowledge -> route_preference? -> ecology -> trip_plan? -> decision -> assemble
```

其中：

- `route_preference` 和 `trip_plan` 只在 `NAVIGATION` / `CHARGE_PLAN` 时进入。
- `CAR_CONTROL` / `PERSONALIZE` 会跳过路线节点，直接进入生态和最终决策。
- 默认启用 LangGraph；没有安装 LangGraph 时，系统使用同样节点函数的 lightweight graph fallback，保证离线可运行。
- 前端会展示本轮 `graph.mode` 和 `graph.path`，用于说明实际执行路径。

## 3. 八大业务 Agent

| Agent | 部署位置 | 职责 |
| --- | --- | --- |
| `GlobalTripPlanningAgent` | 云端 | 路线规划、补能规划、地图 Provider、路线 RAG 和 LLM 路线说明 |
| `UserProfileAgent` | 云端 | 用户长期画像、路线偏好、座舱偏好和动态偏好读取 |
| `VectorKnowledgeAgent` | 云端 | 意图、路线、画像知识的统一 RAG 召回 |
| `ExternalEcologyAgent` | 云端 | 天气、充电站/POI 等外部生态 Provider 聚合 |
| `GlobalSafetyDispatchAgent` | 车端 | 指令安全校验、危险操作拦截、云端结果二次校验 |
| `LocalIntentAgent` | 车端 | 本地意图识别、本地 RAG、可选本地/兜底 LLM |
| `CabinVehicleControlAgent` | 车端 | 座舱/车控/离线导航执行适配 |
| `DataUploadAgent` | 车端 | 交互日志、执行结果、偏好更新和数据闭环上报 |

旧类名如 `CloudScheduleAgent` 仍保留为兼容入口，但主链路和文档口径以新 Agent 为准。

## 4. 在线调用链

```text
用户输入
  -> LocalIntentAgent
  -> GlobalSafetyDispatchAgent
  -> Message
  -> GlobalDispatchAgent
       -> UserProfileAgent
       -> VectorKnowledgeAgent
       -> ExternalEcologyAgent
       -> GlobalTripPlanningAgent (导航/补能时调用)
       -> Cloud LLM decision.summarize
  -> GlobalSafetyDispatchAgent 二次校验云端结果
  -> DataUploadAgent 记录闭环
```

车控和个性化指令不会调用 `GlobalTripPlanningAgent`，避免把空调、座椅、画像查询误送到地图路线规划。

## 5. 离线调用链

```text
用户输入
  -> LocalIntentAgent
  -> GlobalSafetyDispatchAgent
  -> LocalIntentAgent.build_local_llm_context
  -> CabinVehicleControlAgent
  -> DataUploadAgent
```

离线模式读取的是本地意图 Agent 私有上下文，不是全系统共享上下文。

## 6. 本地上下文边界

本地上下文由 `LocalAgentContextManager` 维护，持久化到：

```text
runtime/local_context_state.json
```

隔离键：

```text
agent_id + user_id + session_id
```

当前默认作用域：

```text
agent_id = local_intent
session_id = default
```

也就是说，上下文管理只服务于本地小参数 LLM 所在的 `LocalIntentAgent`。云端 LLM 不主动读取这份多轮上下文，只接收当前请求所需的结构化数据。

## 7. 工具调用与可观测性

`GlobalDispatchAgent` 通过 `ToolRegistry` 暴露工具：

```text
user_profile.lookup
knowledge.retrieve
user_profile.route_preference
ecology.snapshot
trip.plan
decision.summarize
```

同时每次云端执行会记录 graph metadata：

```text
mode: lightweight / langgraph
backend: python / StateGraph
fallback: true / false
path: profile -> knowledge -> ecology -> ...
```

导航/补能场景还会记录 Provider 级 trace：

```text
provider.geocode
provider.map.route
```

Web 页面会展示 Agent 调用链、Runtime Trace、RAG 召回、路线与补能、数据闭环和本地意图 Agent 上下文。

## 8. 安全原则

安全校验优先于任何执行路径。

- 危险指令在车端前置拦截。
- 云端结果返回后仍由 `GlobalSafetyDispatchAgent` 二次校验。
- `CabinVehicleControlAgent` 只接收安全校验后的结构化动作。
- 制动、转向、动力、AEB 等安全关键动作不能交给生成式 LLM 做最终裁决。

## 9. 可替换边界

- `SimpleRetriever` 可替换为 FAISS/Milvus。
- `DeepSeekClient` 可替换为其他云端 LLM。
- 本地 LLM 可接入 Qwen-7B-Int4、ChatGLM3-6B-Int4 等小模型。
- 地图、天气、充电站 Provider 可在真实 API 和离线 Provider 之间切换。

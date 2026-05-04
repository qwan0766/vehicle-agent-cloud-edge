# 阶段实现总结

## 1. 本轮完成内容

本轮在已有 Multi-Agent、RAG、用户画像和数据闭环基础上，继续完成了：

- 多用户切换。
- 动态偏好状态存储。
- 安全策略引擎。
- 端到端场景测试。
- 面试演示脚本。
- Mermaid 架构图。

## 2. 多用户切换

网页新增用户选择器，当前支持：

- `user_001`：舒适 + 高速偏好。
- `user_002`：音乐 + 补能提醒。

前端会把 `user_id` 传给 `/api/run`，后端根据用户召回不同画像上下文。

面试表达：

> 我支持多用户画像切换，说明系统不是写死单用户 demo，而是具备用户上下文隔离意识。

## 3. 动态偏好状态

新增：

- `feedback/preference_store.py`
- `runtime/user_preference_state.json`

每次 `PreferenceUpdate` 会被累计到用户状态中。

面试表达：

> 我把数据闭环从“只记录日志”推进到“可累计偏好状态”。后续可以让这些状态进一步影响用户画像召回排序和个性化路线规划。

## 4. 安全策略引擎

新增：

- `safety/safety_policy.py`

当前规则：

- 危险指令直接拦截。
- 未知指令不进入执行链路。
- 安全指令继续端云或本地执行。

面试表达：

> 我把安全判断从关键词判断升级为独立策略层。这样后续可以继续加入车速、电量、网络状态、场景权限等规则。

## 5. E2E 测试

新增：

- `tests/test_e2e_scenarios.py`

覆盖：

- 在线导航走云端。
- 数据闭环写入。
- 未知指令被策略层拦截。

## 6. 演示材料

新增：

- `docs/demo-script.md`
- `docs/architecture-diagram.md`

这些文档用于面试时快速讲清楚项目。

## 7. 当前推荐讲法

> 这个项目从智能座舱场景出发，构建了一个 offline 端云协同 Multi-Agent 原型。车端负责意图识别、安全拦截和断网兜底，云端负责用户画像、生态数据和路线规划。系统抽象了本地 Retriever，实现意图、画像、路线知识的可解释召回；通过 SafetyPolicy 保证危险和未知指令不会进入执行链路；通过 FeedbackService 记录 UsageEvent 并累计 PreferenceUpdate，形成数据闭环。网页端展示 Agent 调用链、RAG 召回依据和数据闭环结果，便于面试演示。

## 8. 下一步方向

后续可以继续做：

- 将动态偏好状态真正参与 RAG 排序权重。
- 接入 Open-Meteo 作为可选真实外部 API。
- 新增 FastAPI 工程接口版本。
- 加入 SQLite 存储运行数据。
- 可选接入 LLM 或 LangGraph，但必须保留 SafetyPolicy 前置。

# 阶段实现总结

## 1. 本轮完成内容

本轮在已有 Multi-Agent、RAG、用户画像和数据闭环基础上，继续完成了：

- 多用户切换。
- 动态偏好状态存储。
- 安全策略引擎。
- Agent Runtime 与 Tool Registry。
- Tool Schema 与离线 Provider。
- DeepSeek LLM Adapter 与真实 Provider 接口。
- 20 条离线场景评测集。
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

## 6. Agent Runtime 与 Tool Registry

新增：

- `runtime/tool_registry.py`
- `runtime/agent_runtime.py`
- `docs/agent-runtime-tool-registry.md`

当前云端调度已经从“硬编码顺序调用”升级为“Runtime 调 Tool”：

- `user_profile.lookup`
- `user_profile.route_preference`
- `ecology.snapshot`
- `route.plan`

每次工具调用都会记录输入、输出和耗时，并通过 Web API 的 `runtime_trace` 返回给前端。

面试表达：

> 我把 LangChain Tool / Function Calling 的核心思想抽象到了离线项目里。现在虽然工具实现还是 mock，但工具注册、统一调用、trace 观测这些工程边界已经具备，后续接真实 API 或大模型工具调用时不用重写主链路。

## 7. 离线工程闭环

新增：

- `runtime/tool_schema.py`
- `providers/offline_weather_provider.py`
- `providers/offline_charge_provider.py`
- `data/offline_scenarios.py`
- `evaluation/offline_evaluator.py`
- `run_offline_eval.py`
- `docs/offline-completion.md`

当前离线闭环包括：

- Tool 输入输出 schema 校验。
- 离线天气与换电站 Provider。
- 20 条内置场景评测样本。
- 意图准确率、安全召回率、执行状态准确率、RAG 命中率。
- Web 页面离线评测指标展示。

面试表达：

> 我把 offline 项目从 demo 推进到可评测工程。每次修改 Agent、知识库或安全策略，都可以通过离线评测集确认有没有破坏意图识别、安全拦截、执行状态和 RAG 召回。

## 8. LLM 与真实 API 接口

新增：

- `llm/mock_llm_client.py`
- `llm/deepseek_client.py`
- `llm/factory.py`
- `providers/baidu_map_provider.py`
- `providers/open_meteo_weather_provider.py`
- `providers/open_charge_map_provider.py`
- `providers/factory.py`
- `docs/llm-and-real-provider-integration.md`

当前 LLM 接入点：

- `CloudScheduleAgent`：通过 `decision.summarize` Tool 生成最终云端决策说明。
- `CloudRoutePlanAgent`：基于 RAG、地图路线和用户偏好生成路线建议。
- `LocalIntentAgent`：支持可选 LLM 意图兜底，但危险关键词仍然先由本地规则处理。

面试表达：

> 这个项目不是把每个 Agent 都接 LLM，而是只在需要语义推理的位置接。安全策略、车控执行、车辆状态仍然保持确定性。这样符合车载场景里 LLM 能力边界和安全边界分离的原则。

## 9. 演示材料

新增：

- `docs/demo-script.md`
- `docs/architecture-diagram.md`
- `docs/agent-runtime-tool-registry.md`
- `docs/offline-completion.md`
- `docs/llm-and-real-provider-integration.md`

这些文档用于面试时快速讲清楚项目。

## 10. 当前推荐讲法

> 这个项目从智能座舱场景出发，构建了一个 offline-first 的端云协同 Multi-Agent 原型。车端负责意图识别、安全拦截和断网兜底，云端负责用户画像、生态数据和路线规划。系统抽象了本地 Retriever，实现意图、画像、路线知识的可解释召回；通过 AgentRuntime、ToolRegistry 和 ToolSpec 模拟 LangChain Tool 调用链和参数协议；通过 DeepSeekLLMClient / MockLLMClient 接入可替换 LLM 推理层；通过离线与真实 Provider 双实现支持地图、天气、充电站扩展；通过 SafetyPolicy 保证危险和未知指令不会进入执行链路；通过 FeedbackService 记录 UsageEvent 并累计 PreferenceUpdate，形成数据闭环。网页端展示 Agent 调用链、Tool 调用明细、RAG 召回依据、离线评测指标和数据闭环结果，便于面试演示。

## 11. 下一步方向

后续可以继续做：

- 将动态偏好状态真正参与 RAG 排序权重。
- 给 Tool 增加失败降级和重试策略。
- 接入 Open-Meteo 作为可选真实外部 API。
- 新增 FastAPI 工程接口版本。
- 加入 SQLite 存储运行数据。
- 可选接入 LLM 或 LangGraph，但必须保留 SafetyPolicy 前置。

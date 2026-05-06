# 本地 Agent 上下文管理设计

更新时间：2026-05-06

## 1. 设计目标

本地上下文管理只针对车端本地小参数 LLM 所在的单个 Agent，而不是全系统共享记忆。

当前项目默认管理对象是：

```text
LocalIntentAgent
agent_id = local_intent
```

这样设计是为了贴合真实车载部署：云端可以有多个 LLM 调用，但云端 LLM 每次只接收当前请求的结构化上下文；本地小模型受算力、窗口和离线约束，才需要短期窗口、压缩摘要和 Token 预算管理。

## 2. 核心模块

```text
memory/local_agent_context_manager.py
memory/local_context_manager.py
agents/vehicle/local_intent_agent.py
llm/local_provider.py
core/vehicle_core_service.py
web_demo/app_model.py
```

`LocalContextManager` 仍保留为兼容类，实际能力由 `LocalAgentContextManager` 提供。

## 3. 隔离维度

上下文按三元组隔离：

```text
agent_id + user_id + session_id
```

这意味着：

- `local_intent` 的历史不会污染未来可能存在的 `local_summary`。
- 同一个用户的不同会话可以拆开管理。
- 本地 Agent 上下文不会被云端 LLM 自动读取。

## 4. 上下文内容

`build_local_llm_context` 返回：

```text
memory_scope
agent_id
session_id
current_input
summary
recent_turns
preference_state
vehicle_state
retrieved_context
window
local_llm
```

其中：

- `summary` 是被压缩的旧历史。
- `recent_turns` 是最近 N 轮完整交互。
- `preference_state` 是长期偏好读取结果，不和短期上下文混存。
- `retrieved_context` 是本地意图 Agent 的本地 RAG 召回。
- `window` 包含 `context_limit_tokens=7500` 和 `generation_buffer_tokens=500`，用于说明本地小模型的工程边界。
- `local_llm` 包含本地 Provider、模型名、Agent scope、system prompt、user prompt 和 prompt 预览。

## 4.1 本地 LLM Provider

新增 `llm/local_provider.py` 后，车端本地 LLM 与云端 DeepSeek 分离：

| Provider | 配置值 | 默认地址 | 说明 |
| --- | --- | --- | --- |
| Mock | `mock_local` | 无需地址 | 默认模式，方便纯离线测试，不要求安装模型 |
| Ollama | `ollama` | `http://127.0.0.1:11434` | 调用 `/api/generate` |
| LM Studio | `lmstudio` | `http://127.0.0.1:1234/v1` | OpenAI-compatible `/chat/completions` |
| llama.cpp server | `llama_cpp` | `http://127.0.0.1:8080/v1` | OpenAI-compatible `/chat/completions` |

`.env.example` 中的关键配置：

```text
LOCAL_LLM_PROVIDER=mock_local
LOCAL_LLM_MODEL=mock-local-intent
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_TIMEOUT=8
ENABLE_LLM_INTENT_FALLBACK=0
```

`ENABLE_LLM_INTENT_FALLBACK=0` 是有意为之：默认情况下，意图识别先由规则、目的地解析和本地 RAG 完成；只有在需要演示本地小模型兜底时，才打开本地 LLM fallback。危险关键词仍然在 fallback 前被拦截，不会交给 LLM 自由判断。

## 5. 压缩策略

当前实现使用确定性压缩：

```text
新结果写入 recent_turns
  -> 超过 max_recent_turns
  -> 最旧 turn 转为短摘要
  -> 合并进 summary
  -> summary 超出字符预算时保留最新尾部
```

真实上车时可以把摘要函数替换为本地小模型摘要，但接口边界不需要变化。

## 6. 在线与离线边界

在线模式：

```text
LocalIntentAgent -> GlobalSafetyDispatchAgent -> GlobalDispatchAgent -> Cloud tools/LLM
执行结果记录进 local_intent 的 Agent 级上下文
```

离线模式：

```text
LocalIntentAgent -> GlobalSafetyDispatchAgent
  -> LocalIntentAgent.build_local_llm_context
  -> CabinVehicleControlAgent
  -> DataUploadAgent
```

离线链路才会把本地上下文作为执行辅助信息展示出来。

## 7. 面试表达

可以这样讲：

> 我没有做一个全局共享对话记忆，因为车载 Multi-Agent 里不同 Agent 的职责和安全等级不同。真正需要上下文窗口的是车端离线小模型，比如本地意图识别 Agent。所以我把上下文管理收敛到 agent_id、user_id、session_id 三元组下，云端 LLM 保持请求级无状态，本地 LLM 才做最近窗口、压缩摘要和 Token 预算控制。

如果被追问本地 LLM 现在是否真正接入：

> 已经抽象了 `LocalLLMProvider`，支持 mock、Ollama、LM Studio 和 llama.cpp server。当前默认是 `mock_local`，保证项目不用安装模型也能跑；如果本地启动 Ollama 或 LM Studio，只要改 `.env` 就能把 `LocalIntentAgent` 的 fallback 切到真实本地模型。前端会展示本地 Provider、模型、prompt 预览和估算 token 数，说明上下文确实进入了本地 Agent 的推理包。

如果被追问为什么线上 LLM 不做上下文管理：

> 云端 LLM 是编排和生成层，输入应该来自当前车况、用户画像、RAG、Provider 结果和安全策略。把历史会话无限带到云端会增加成本、延迟和污染风险，所以项目里云端只接结构化上下文，本地小模型才维护 Agent 私有上下文。

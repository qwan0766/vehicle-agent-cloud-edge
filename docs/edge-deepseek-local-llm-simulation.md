# DeepSeek 模拟车端小模型接入说明

更新时间：2026-05-06

## 1. 这一步解决什么问题

本项目没有把 DeepSeek 包装成“真正离线部署模型”，而是把它作为车端小参数 LLM 的工程行为模拟器：

- 云端 LLM：继续由 `DeepSeekLLMClient` 承担，用于云端决策、路线规划总结等复杂生成任务。
- 车端 LLM 模拟：由 `EdgeDeepSeekSimProvider` 承担，用 DeepSeek API 模拟车端小模型的输入输出约束。
- 默认兜底：没有 key 或不想联网时，仍然可以用 `mock_local` 保证项目可运行。

面试表达时建议说：

> 当前项目用 DeepSeek 低成本模型模拟车端小参数 LLM 的推理行为，并在工程层实现 Provider 抽象、prompt 预算、单 Agent 上下文压缩和安全边界。它不是声称已经完成真实车端离线部署，而是为后续替换 Ollama、LM Studio、llama.cpp 或量化车端模型预留了接口。

## 2. 配置方式

默认配置仍然是纯离线：

```env
LOCAL_LLM_PROVIDER=mock_local
LOCAL_LLM_MODEL=mock-local-intent
```

如果要用 DeepSeek 模拟车端小模型：

```env
LOCAL_LLM_PROVIDER=edge_deepseek_sim
LOCAL_LLM_MODEL=deepseek-v4-flash
LOCAL_LLM_MAX_CONTEXT_TOKENS=7500
LOCAL_LLM_GENERATION_BUFFER_TOKENS=500
LOCAL_LLM_MAX_OUTPUT_TOKENS=64
ENABLE_LLM_INTENT_FALLBACK=0
```

说明：

- `DEEPSEEK_API_KEY` 仍然只放在本地 `.env`，不进入 Git。
- `LOCAL_LLM_DEEPSEEK_BASE_URL` 可选，默认是 `https://api.deepseek.com`。
- `LOCAL_LLM_BASE_URL` 仍然留给 Ollama / LM Studio / llama.cpp 这类本地服务，不会被 `edge_deepseek_sim` 误用。

## 3. Prompt 和上下文预算

当前项目里已有本地上下文窗口参数：

```text
context_limit_tokens = 7500
generation_buffer_tokens = 500
```

本次实现新增：

```text
max_output_tokens = 64
prompt_budget_tokens = context_limit_tokens - generation_buffer_tokens
```

当 prompt 超出预算时，`EdgeDeepSeekSimProvider` 会压缩输入，只保留：

- 当前用户指令
- 本地 Agent 摘要尾部
- 最近 2 轮关键交互
- 用户偏好状态
- 车辆状态
- 最多 2 条 RAG 召回摘要
- window 元信息

这模拟的是车端小模型“上下文窗口有限、输出短、只处理当前 Agent 任务”的限制。

## 4. Agent 分工变化

### LocalIntentAgent

负责本地意图识别、RAG 召回和本地上下文封装。打开 `ENABLE_LLM_INTENT_FALLBACK=1` 时，未知意图会交给 `edge_deepseek_sim` 判断。

### GlobalSafetyDispatchAgent

安全判断仍然由规则和策略优先完成。可选打开：

```env
ENABLE_LOCAL_LLM_SAFETY_EXPLAIN=1
```

此时本地 LLM 只生成“为什么被拦截”的解释，不参与是否放行的决策。

### CabinVehicleControlAgent

车控执行仍然走确定性规则。可选打开：

```env
ENABLE_LOCAL_LLM_CONTROL_EXPLAIN=1
```

此时本地 LLM 只生成简短执行说明，不生成新的车控动作。

## 5. 前端展示

网页会展示：

- `Provider 状态`：云端 LLM、车端模拟 LLM、地图、天气、充电站 Provider。
- `本地上下文管理`：provider、model、agent scope、summary、recent turns、prompt preview。
- prompt 预算：`estimated / prompt_budget prompt tokens`、`max_output_tokens`、是否 over budget。

这样面试时可以直接演示“本地小模型为什么需要上下文管理”，而不是只口头解释。

## 6. 面试追问回答

如果被问“这是不是假本地模型”：

> 是工程模拟，不是真离线部署。我把真实车端模型抽象为 `LocalLLMProvider`，目前可选用 DeepSeek 轻量模型模拟小模型行为。重点是验证端云分层、上下文预算、安全边界和 Provider 替换能力。真实部署时可以把 Provider 切换到 Ollama、LM Studio、llama.cpp server 或车端量化模型。

如果被问“为什么云端不做上下文管理”：

> 云端 LLM 是按请求接收结构化上下文：用户画像、RAG、地图、天气、充电站、车况。它不持有本地短期对话记忆，避免历史污染、成本膨胀和安全边界模糊。上下文压缩只针对车端本地小模型所在的单个 Agent。


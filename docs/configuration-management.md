# 配置管理与环境变量分层

本项目已经把散落在 Provider、LLM Client、Agent 编排器里的环境变量读取统一收敛到 `config/settings.py`。这一步的目的不是增加复杂度，而是让端云协同系统具备更清晰的工程边界：Agent 只关心“拿到的配置是什么”，不直接关心“配置从哪里读取”。

## 为什么要集中配置

早期原型里，地图、天气、DeepSeek、本地 LLM 模拟、LangGraph 开关会分别在不同模块里读取 `os.getenv`。这在 demo 阶段能跑，但后续会带来几个问题：

- 接口越来越多后，很难确认一个环境变量到底在哪里生效。
- 测试时需要在多个模块里 patch 环境变量，容易遗漏。
- 前端 Provider 状态、后端 Provider 工厂、测试报告可能显示不一致。
- API Key 有误打印或误提交风险。

现在统一通过 `get_settings()` 读取配置，返回一个结构化的 `AppSettings`。

## 配置分层

### `LLMSettings`

用于云端 LLM 能力，当前主要对应 DeepSeek：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`
- `DEEPSEEK_BASE_URL`

典型用途：

- 云端决策说明
- 云端结果总结
- Provider smoke test 中的 DeepSeek LLM 检测

### `LocalLLMSettings`

用于模拟车端离线小参数 LLM。真实车载系统里这部分会是端侧模型，本项目允许用 mock、本地 Ollama/LM Studio，或 DeepSeek 低成本模型模拟：

- `LOCAL_LLM_PROVIDER`
- `LOCAL_LLM_MODEL`
- `LOCAL_LLM_API_KEY`
- `LOCAL_LLM_BASE_URL`
- `LOCAL_LLM_DEEPSEEK_BASE_URL`
- `LOCAL_LLM_TIMEOUT`
- `LOCAL_LLM_MAX_CONTEXT_TOKENS`
- `LOCAL_LLM_GENERATION_BUFFER_TOKENS`
- `LOCAL_LLM_MAX_OUTPUT_TOKENS`

典型用途：

- 本地意图识别补充
- 输入重写
- 本地 Agent 上下文压缩预算控制

### `ProviderSettings`

用于外部生态接口：

- `AMAP_API_KEY`
- `AMAP_GEOCODE_CITY`
- `BAIDU_MAP_AK`
- `USE_OPEN_METEO`
- `OPENCHARGEMAP_API_KEY`
- `USE_OPENCHARGEMAP`

典型用途：

- 高德地理编码
- 高德驾车路线
- 高德 POI 候选地点和补能站
- Open-Meteo 天气

### `ProviderRuntimeSettings`

用于统一控制外部 Provider 的容错行为：

- `PROVIDER_TIMEOUT_SECONDS`
- `PROVIDER_RETRIES`
- `PROVIDER_BACKOFF_SECONDS`
- `PROVIDER_CIRCUIT_FAILURE_THRESHOLD`
- `PROVIDER_CIRCUIT_RESET_SECONDS`
- `PROVIDER_HEALTH_TTL_SECONDS`

典型用途：

- 外部 API 超时控制
- HTTP 5xx / 429 重试
- 连续失败后的熔断保护
- Provider health cache 状态记录

### `RuntimeSettings`

用于控制工程链路开关：

- `ENABLE_LANGGRAPH`
- `ENABLE_LLM_INTENT_FALLBACK`
- `ENABLE_LOCAL_LLM_INPUT_REWRITE`
- `ENABLE_LOCAL_LLM_SAFETY_EXPLAIN`
- `ENABLE_LOCAL_LLM_CLOUD_REVIEW`
- `ENABLE_LOCAL_LLM_CONTROL_EXPLAIN`

这些开关适合用于面试演示：可以清楚展示“纯规则离线链路”“车端小模型增强链路”“云端 LangGraph 编排链路”的差异。

## 安全处理

所有 API Key 字段在 dataclass 中都设置了 `repr=False`，避免日志、测试失败输出或前端状态误显示真实密钥。

对外展示时只展示：

- 是否已配置
- 当前 provider 名称
- 对应接口名称
- smoke test 状态

不展示真实 key。

## 使用方式

Provider 或 Agent 不再直接读取环境变量，而是：

```python
from config.settings import get_settings

settings = get_settings()

if settings.providers.amap_configured:
    ...

if settings.runtime.enable_langgraph:
    ...
```

这让测试可以稳定 patch 环境变量，也让未来切换配置来源更容易。以后如果要从 `.env` 升级到 YAML、数据库、远端配置中心，只需要改配置加载层，而不用改每个 Agent。

## 面试表述

可以这样介绍：

> 我把环境变量读取从业务模块中抽离出来，统一封装成 `AppSettings`，并按云端 LLM、车端本地 LLM、外部 Provider、运行时开关四类配置分层。这样 Agent 间不会散落读取环境变量，测试也可以针对配置层做集中验证，同时 API Key 字段不会出现在日志 repr 中，符合更接近真实工程的配置治理方式。

# LLM 与真实 Provider 接入说明

## 当前接入范围

本轮把项目从“纯离线规则 Agent”升级为“默认离线、可选真实 API”的工程形态。

新增接口：

- `llm/`
  - `MockLLMClient`：默认离线 LLM 兜底。
  - `DeepSeekLLMClient`：DeepSeek OpenAI-compatible Chat Completions 接入。
  - `create_llm_client()`：检测 `DEEPSEEK_API_KEY`，有 key 时走 DeepSeek，否则走 mock。

- `providers/`
  - `OfflineMapProvider`
  - `AmapPOIProvider`
  - `BaiduMapProvider`
  - `OpenMeteoWeatherProvider`
  - `OpenChargeMapProvider`
  - `create_map_provider()`
  - `create_weather_provider()`
  - `create_charge_provider()`

## LLM 接入点

不是 8 个 Agent 全部接 LLM，而是在真正需要语义推理的位置接：

1. `CloudScheduleAgent`
   - 新增 `decision.summarize` Tool。
   - 基于用户画像、外部生态、路线结果生成最终云端决策说明。

2. `CloudRoutePlanAgent`
   - 基于 RAG 路线知识、MapProvider 路线、用户偏好生成路线建议。

3. `LocalIntentAgent`
   - 支持可选 LLM 兜底。
   - 只有本地知识库和 RAG 都识别失败时才启用。
   - 危险关键词仍然先由本地规则识别，不交给 LLM。

安全边界：

- `SafetyAgent` 不接 LLM。
- `SafetyPolicy` 不接 LLM。
- `CarControlAgent` 不接 LLM。
- 真实车控不接入，只保留 mock adapter 思路。

## 环境变量

项目不会把 API Key 写进代码或 git。

可参考 `.env.example`：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-v4-flash
BAIDU_MAP_AK=your_baidu_map_ak
AMAP_API_KEY=your_amap_web_service_key
OPENCHARGEMAP_API_KEY=your_openchargemap_key
USE_OPEN_METEO=1
USE_OPENCHARGEMAP=1
ENABLE_LLM_INTENT_FALLBACK=1
```

说明：

- `DEEPSEEK_API_KEY`：启用真实 DeepSeek LLM。
- `DEEPSEEK_MODEL`：默认 `deepseek-v4-flash`。
- `BAIDU_MAP_AK`：启用百度地图驾车路线 Provider。
- `AMAP_API_KEY`：启用高德 POI 周边搜索 Provider，优先用于附近充电站查询。
- `USE_OPEN_METEO=1`：启用 Open-Meteo 天气 Provider。
- `OPENCHARGEMAP_API_KEY` 或 `USE_OPENCHARGEMAP=1`：启用 OpenChargeMap 充电站 Provider。
- `ENABLE_LLM_INTENT_FALLBACK=1`：启用 LLM 意图兜底。

## 真实接口 Smoke Test

本地 `.env` 已被 `.gitignore` 忽略。可以把真实 key 写入 `.env`，然后运行：

```bash
python scripts/smoke_real_providers.py
```

脚本会测试：

- DeepSeek LLM
- Open-Meteo Weather
- AMap POI
- OpenChargeMap
- Baidu Map

注意：

- AMap POI 当前要求 `AMAP_API_KEY`。
- OpenChargeMap 当前要求 `OPENCHARGEMAP_API_KEY`。
- Baidu Map 当前要求 `BAIDU_MAP_AK`。
- 脚本不会打印 API Key，只输出接口成功、失败或跳过原因。

## 面试讲法

可以这样讲：

> 我没有把 LLM 硬塞进每个 Agent，而是把它作为可替换推理层放在云端调度、路线规划和意图兜底这些需要语义能力的位置。安全拦截、车控执行、车辆状态读取仍然保持确定性。这样既体现了 LLM Agent 能力，也保留了车载场景必须具备的安全边界。

也可以补一句：

> DeepSeek 接口采用 OpenAI-compatible chat completions 形式，因此我没有绑定特定 SDK，而是用标准 HTTP Adapter 封装。后续换 OpenAI、Qwen、Doubao 或本地模型，只需要替换 LLM Client，不影响 Agent 主链路。

# 面试项目总结：车载 Multi-Agent 端云协同系统

更新时间：2026-05-06

## 1. 项目一句话

这是一个面向智能座舱场景的 **车载 Multi-Agent 端云协同 AI 应用原型**。系统支持本地意图识别、车规级安全拦截、云端多 Agent 调度、RAG 检索增强、真实 LLM/地图/天气/充电站 API 接入、网页可视化展示和自动化验收。

面试时可以这样开场：

> 我做的不是单纯聊天机器人，而是把车端安全、云端决策、RAG、真实外部 API 和可观测测试链路串起来的 AI 应用工程项目。它模拟的是智能座舱里“用户说一句话，系统决定能不能执行、走本地还是云端、调用哪些工具、如何给出可执行结果”的完整链路。

## 2. 当前完成度

当前项目已经从最初控制台 demo 演进为：

- 有本地 Git 管理的完整 Python 项目。
- 有 8 个职责清晰的 Agent。
- 有 Web 展示页面。
- 有 DeepSeek LLM 接入。
- 有高德路线、高德 POI、Open-Meteo 天气接口。
- 有离线评测集和一键验收脚本。
- 有真实错误处理和用户友好错误解释。
- 有本地 LLM Provider 抽象：支持 mock、Ollama、LM Studio、llama.cpp server。
- 默认启用 LangGraph 编排：安装 `langgraph` 后使用真实 `StateGraph`，未安装时自动 fallback 到 lightweight graph。
- 有本地上下文管理：最近交互窗口、压缩摘要、长期偏好读取、prompt 预览和 Web 可视化。
- 有面试演示脚本、架构文档和验收报告。

当前最新自动化验收结果：

```text
unit tests: PASS
offline evaluation: PASS
provider smoke: PASS
online matrix: PASS
```

最近一次报告显示：

```text
Ran 121 tests
OK
```

验收报告路径：

```text
reports/acceptance_report.md
```

网页演示地址：

```text
http://127.0.0.1:8028/
```

## 3. 系统架构怎么讲

项目采用端云协同三层架构：

1. 车载执行层
   - 负责本地意图识别、安全校验、断网执行、车控/导航模拟。

2. 端云通信层
   - 使用统一 `Message` 报文封装用户、意图、安全等级、网络状态和指令内容。

3. 云端决策层
   - 负责用户画像、外部生态、路线规划、LLM 决策说明和工具调用 trace。

面试表达：

> 我先定义统一消息协议，再让各个 Agent 围绕这个协议协作。这样后续扩展真实车控、真实向量库或更多外部工具时，不需要推翻主流程。

核心文件：

```text
core/constants.py
core/message.py
core/vehicle_core_service.py
agents/
providers/
runtime/
web_demo/
```

## 4. 8 个业务 Agent 职责

当前版本已经按课程附件口径重构为“八大业务 Agent + 一个全局调度编排器”。`GlobalDispatchAgent` 是编排器，不计入八大业务 Agent。

| Agent | 部署位置 | 职责 | 是否接 LLM |
| --- | --- | --- | --- |
| `GlobalTripPlanningAgent` | 云端 | 路线规划、补能规划、地图 Provider、路线 RAG 和路线建议 | 是 |
| `UserProfileAgent` | 云端 | 用户长期画像、路线偏好、座舱偏好和动态偏好读取 | 可选 |
| `VectorKnowledgeAgent` | 云端 | 意图、路线、画像知识的统一 RAG 召回 | 不直接接 |
| `ExternalEcologyAgent` | 云端 | 天气、充电站/POI 等外部生态 Provider 聚合 | 不直接接 |
| `GlobalSafetyDispatchAgent` | 车端 | 指令安全校验、危险操作拦截、云端结果二次校验 | 不接 |
| `LocalIntentAgent` | 车端 | 本地意图识别、本地 RAG、可选本地/兜底 LLM | 可选 |
| `CabinVehicleControlAgent` | 车端 | 座舱、车控、离线导航执行适配 | 不接 |
| `DataUploadAgent` | 车端 | 交互日志、执行结果、偏好更新和数据闭环上报 | 不接 |

关键讲法：

> 我把 Agent 拆分成业务能力单元，而不是按 demo 类名凑数量。全局调度器负责任务拆解和工具编排；真正的八大 Agent 分别覆盖行程规划、用户画像、知识库、生态接口、安全、意图、车控和数据闭环。

### 4.1 LangGraph 怎么讲

当前云端编排已经默认启用 LangGraph：

```text
默认：尝试 LangGraph StateGraph
fallback：未安装 langgraph -> lightweight graph
强制轻量：ENABLE_LANGGRAPH=0 -> lightweight graph
```

图节点是：

```text
profile -> knowledge -> route_preference? -> ecology -> trip_plan? -> decision -> assemble
```

面试表达：

> 我没有在一开始就强行引入 LangGraph，而是先把 Agent 边界、统一状态、工具 trace 和条件分流拆清楚。现在 `GlobalDispatchAgent` 已经抽象为显式图执行，并默认尝试用 LangGraph `StateGraph` 执行；如果环境里没有安装 `langgraph`，同一套节点函数会 fallback 到 lightweight graph。这样既能把真实框架作为默认路径展示，也保留了项目离线可运行和低依赖的交付要求。

## 5. RAG 是怎么做的

当前实现是轻量级 RAG 模拟，不依赖向量库：

- `rag/simple_retriever.py`：关键词检索器。
- `rag/documents.py`：本地和云端知识文档。
- `LocalIntentAgent`：用本地知识辅助意图识别。
- `VectorKnowledgeAgent`：统一召回意图、画像和路线知识。
- `GlobalTripPlanningAgent`：用路线知识辅助规划。

当前 RAG 知识包括：

- 电量低于 20% 建议前往换电站。
- 长途优先高速路线。
- 断网时自动切换离线导航。
- 车内舒适温度 22~25℃。
- 危险指令包括动力、制动、转向、加速等。

面试表达：

> 这个项目的 RAG 重点不是堆向量库，而是展示“检索上下文如何进入 Agent 决策链”。我先用轻量检索把接口边界打通，后续可以把 `SimpleRetriever` 替换成 Milvus、FAISS 或云端向量数据库。

## 6. LLM 和真实 API 接入

### 6.1 LLM

当前 LLM Provider：

```text
云端：DeepSeek
本地：mock_local / Ollama / LM Studio / llama.cpp server
```

接入点：

- `GlobalTripPlanningAgent`：生成路线建议。
- `GlobalDispatchAgent`：生成最终执行说明。
- `LocalIntentAgent`：本地小模型可选意图兜底，使用本地 Agent 上下文包。

不接 LLM 的关键模块：

- `GlobalSafetyDispatchAgent`
- `SafetyPolicy`
- `CabinVehicleControlAgent`

面试表达：

> LLM 在这里是语义推理层，不是安全控制层。安全拦截和车控执行必须保持确定性。

本地 LLM 的配置方式：

```text
LOCAL_LLM_PROVIDER=mock_local
LOCAL_LLM_MODEL=mock-local-intent
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
ENABLE_LLM_INTENT_FALLBACK=0
```

面试表达：

> 我把云端 LLM 和车端本地 LLM 分开抽象。云端用 DeepSeek 做路线解释和最终说明；车端本地 LLM 通过 `LocalLLMProvider` 接入，默认 mock，后续可以切到 Ollama、LM Studio 或 llama.cpp。它只服务 `LocalIntentAgent` 的兜底识别和上下文窗口展示，不参与最终安全裁决。

### 6.2 外部接口 Provider

当前真实 Provider：

| 能力 | 当前 Provider |
| --- | --- |
| LLM | DeepSeek |
| 地图路线 | 高德 `amap_route` |
| 充电站 POI | 高德 `amap_poi` |
| 天气 | Open-Meteo |

可选 Provider：

- OpenChargeMap
- Baidu Map

当前网页的 **Provider 状态** 模块展示的是“现在系统配置了哪些真实接口”。点击 `Smoke Test` 会做一次真实连通性检查。

面试表达：

> 我把外部能力都封装成 Provider，而不是在 Agent 里直接写 HTTP 请求。这样可以做到真实 Provider、离线 Provider、测试 Provider 之间可替换。

## 7. 安全策略怎么讲

当前安全链路：

```text
用户输入 -> LocalIntentAgent -> GlobalSafetyDispatchAgent -> SafetyPolicy -> 执行/拦截
```

危险输入例子：

- `加速到100km/h`
- `关闭AEB`
- `接管方向盘`
- `踩刹车`

这些指令会被识别为车控相关，但执行状态是 `BLOCKED`。

面试表达：

> 我没有简单把危险指令识别成 unknown，而是保留它的意图类型，再由安全策略拦截。这样系统能解释“它是什么”和“为什么不能执行”。

## 8. 端云协同与断网策略

在线模式：

```text
本地意图识别 -> 安全校验 -> 云端调度 -> 用户画像 -> 外部生态 -> 路线规划/LLM 决策 -> 返回执行说明
```

离线模式：

```text
本地意图识别 -> 安全校验 -> 本地执行/本地兜底
```

重要取舍：

- 离线模式可以本地兜底。
- 在线演示不做静默离线兜底，真实 API 失败就暴露失败并给用户解释。

面试表达：

> 在线链路不做假成功，是为了展示真实 Provider 的可观测性。失败时系统不会瞎编结果，而是明确告诉用户是地理编码、路线规划还是 LLM 生成失败。

### 8.1 本地上下文管理怎么讲

当前新增了 `LocalAgentContextManager`：

- 按 `agent_id + user_id + session_id` 隔离本地历史。
- 保留最近交互窗口。
- 超出窗口后把旧 turn 压缩成摘要。
- 离线链路由 `LocalIntentAgent` 读取压缩摘要、最近 turn、本地 RAG 召回和长期偏好状态。
- 在线 LLM 不主动读取多轮历史，避免云端 prompt 膨胀和历史噪声污染。

面试表达：

> 我没有做全局共享记忆，而是把上下文管理收敛到本地意图 Agent。在线链路只接收当前请求需要的结构化上下文；断网时 `LocalIntentAgent` 会拿到自己的短期窗口、压缩摘要、本地 RAG 召回和长期偏好，这样本地小模型可以理解连续任务，同时保持离线可运行。

## 9. 网页展示有哪些内容

网页当前展示：

- 车辆状态：车速、电量、GPS、网络状态。
- 指令执行：用户画像、快捷场景、自定义输入。
- Agent 调用链：展示本地和云端 Agent 经过了哪些节点。
- Runtime Trace：展示工具调用、输出和耗时。
- RAG 召回知识：展示命中的知识条目。
- 数据闭环：展示事件记录和偏好更新。
- 本地意图 Agent 上下文：展示压缩摘要、最近交互窗口和已压缩轮数。
- 离线评测：展示意图准确率、安全召回率、RAG 命中率。
- 验收报告：展示最近一次自动化验收结果。
- Provider 状态：展示真实外部接口配置和 smoke test。
- 路线与补能：展示地图路线、距离、预计时间、附近充电站。
- 执行结果：Markdown 渲染最终说明。

面试表达：

> 我做 Web 页面不是为了好看，而是为了让 Agent 决策过程可观测。面试官可以直接看到每次请求经过了哪些 Agent、调用了哪些 Provider、每一步输出是什么。

## 10. 测试和验收体系

项目现在有三类测试：

1. 单元测试
   - 覆盖 Agent、Provider、RAG、Tool Registry、Web app model 等。

2. 离线评测
   - 20 条内置场景。
   - 指标包括意图准确率、安全准确率、执行状态准确率、安全拦截召回、RAG 命中率。

3. 一键验收
   - 命令：

```bash
python scripts/run_acceptance.py
```

验收步骤：

- `unit tests`
- `offline evaluation`
- `provider smoke`
- `online matrix`

面试表达：

> 我不靠手动点页面证明系统能跑，而是用一键验收脚本把单元测试、离线评测、真实接口检测和在线代表输入矩阵串起来。每次修改之后都能生成报告。

## 11. 可以主动讲的真实问题

这些问题很适合面试主动讲，因为它们体现工程排错能力。

### 11.1 `打开视频网站` 被误判为车控

原因：

- 早期规则看到“打开”就倾向车控。

修复：

- 收紧车控领域词，必须命中座椅、空调、车窗、AEB 等车辆相关词。

可以怎么讲：

> 这个问题说明意图识别不能只靠通用动词，还要结合领域词。

### 11.2 `到外滩` 地理编码跑偏

原因：

- 高德地理编码对短地名存在城市歧义。

修复：

- 增加城市语境推断：`外滩` 默认约束到上海，`萧山机场` 约束到杭州。

可以怎么讲：

> 真实 API 的问题不只是能不能调通，还包括返回是否符合业务语境。

### 11.3 `温度调到24度` 误调用路线 Agent

原因：

- 早期云端调度把所有在线安全指令都送进路线规划工具。

修复：

- `GlobalDispatchAgent` 按 `CommandType` 分流。
- 导航/补能调用路线 Agent。
- 车控/个性化不调用路线 Agent。

可以怎么讲：

> Multi-Agent 编排不是 Agent 越多越好，而是要按任务类型调用正确 Agent。

### 11.4 `关闭AEB` 没有被危险拦截

原因：

- 早期危险词没有覆盖辅助驾驶相关表达。

修复：

- 扩展危险关键词，并加入测试矩阵。

可以怎么讲：

> 安全策略需要持续通过测试样例扩展，而不是一次性拍脑袋写几个关键词。

## 12. 面试常见追问回答

### 问：这个项目和普通 Chatbot 有什么区别？

答：

> 普通 Chatbot 主要是对话生成，而这个项目强调“指令能不能执行、由谁执行、调用哪些工具、失败如何解释”。它有安全策略、端云分流、Provider 接口和验收体系，更接近 AI 应用工程。

### 问：为什么不是 8 个 Agent 都接 LLM？

答：

> 因为车载场景里安全和控制链路需要确定性。LLM 适合做语义理解、路线建议和最终说明生成，但 `GlobalSafetyDispatchAgent`、`SafetyPolicy` 和 `CabinVehicleControlAgent` 不能依赖概率模型。

### 问：RAG 为什么没有用向量库？

答：

> 当前阶段目标是把 RAG 的工程链路跑通，所以先用轻量关键词检索模拟。代码上已经把 retriever 做成独立模块，后续可以替换成 FAISS、Milvus 或云端向量库。

### 问：真实 API 失败怎么办？

答：

> 在线演示不会静默降级成假数据。失败会被转换成用户能理解的错误，比如目的地无法解析、地图路线不可达、LLM 生成失败，并给出下一步建议。

### 问：你怎么证明项目可维护？

答：

> 我做了统一 Message 协议、Provider 抽象、Tool Registry、Runtime Trace、离线评测和一键验收脚本。每个模块职责比较清晰，修改后可以通过验收报告判断是否退化。

### 问：如果要上线，还差什么？

答：

> 还需要真实车控 Adapter、权限系统、更多安全策略、日志脱敏、限流重试、真实向量库、配置中心、监控告警和更严格的端到端测试。当前项目定位是面向面试展示的工程原型，不是直接上车的生产系统。

## 13. 推荐演示顺序

面试演示时建议按这个顺序：

1. 打开网页，先展示整体页面。
2. 展示 Provider 状态，说明当前接入 DeepSeek、高德、Open-Meteo。
3. 展示验收报告，说明最近一次自动化验收通过。
4. 使用“面试演示模式”依次点击 5 个步骤。
5. `导航去蔚来中心`：展示完整端云协同链路。
6. `温度调到24度`：说明车控不调用路线 Agent。
7. `电量低`：展示补能 RAG、高德 POI 和路线规划。
8. `关闭AEB`：展示安全拦截。
9. `导航去巴黎`：展示真实 API 失败时的友好错误解释。

## 14. 简历写法参考

可以写成：

> 设计并实现车载 Multi-Agent 端云协同 AI 应用原型，基于 Python 标准库构建 8 个 Agent 的模块化架构，支持本地意图识别、车规级安全拦截、断网本地兜底、云端 LLM 决策、RAG 路线规划、用户画像召回和数据闭环。接入 DeepSeek、高德路线/POI、Open-Meteo 等真实 Provider，并实现 Runtime Trace、Web 可视化、一键验收脚本和 91 条自动化测试，覆盖意图识别、安全拦截、外部接口、在线矩阵和错误处理。

如果要更短：

> 车载智能座舱 Multi-Agent 项目：实现 8 个 Agent 端云协同、RAG 检索增强、DeepSeek/高德/Open-Meteo 接入、安全拦截、Web 可视化和自动化验收，覆盖真实 API 调用与异常处理。

## 15. 你应该强调的能力

这个项目能体现：

- AI 应用工程能力：不是只会调模型，而是能把模型接进业务流程。
- Agent 架构能力：能拆职责、做调度、做 trace。
- RAG 工程意识：能把检索结果纳入决策链。
- 安全边界意识：知道哪些地方不能交给 LLM。
- 外部 API 集成能力：能处理真实 Provider 的成功、失败和歧义。
- 测试意识：能用测试矩阵和验收脚本证明系统稳定。
- 面试表达能力：能讲清楚为什么这么设计，而不是只展示页面。

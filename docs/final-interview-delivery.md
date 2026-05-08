# 最终面试交付说明

更新时间：2026-05-06

## 1. 项目定位

这是一个面向智能座舱场景的车载 Multi-Agent 端云协同系统原型。项目重点不是做一个普通 Chatbot，而是把“用户自然语言指令 -> 本地意图识别 -> 安全拦截 -> 端云分流 -> 云端多 Agent 编排 -> 真实 Provider 调用 -> 最终说明 -> 数据闭环”串成一条可解释、可测试、可演示的 AI 应用工程链路。

一句话介绍：

> 我做的是一个车载 Multi-Agent 端云协同 AI 应用工程项目。车端负责意图、安全、执行和数据闭环，云端负责画像、知识、生态和行程规划；中间用统一 Message 协议和默认启用的 LangGraph 工作流编排。在线链路接入 DeepSeek、高德地图、Open-Meteo 和高德 POI，离线链路保留本地 RAG、本地小模型上下文管理和车端兜底执行。

## 2. 当前交付物

- Python 可运行代码：`agents/`、`core/`、`providers/`、`workflow/`、`web_demo/`
- Web 展示页：`web_demo/static/index.html`
- 一键验收脚本：`scripts/run_acceptance.py`
- Web QA 脚本：`scripts/web_qa.py`
- 验收报告：`reports/acceptance_report.md`
- Web QA 报告：`reports/web_qa_report.md`
- 架构与面试文档：`docs/architecture.md`、`docs/agent-roles-and-workflows.md`、`docs/interview-current-summary.md`

## 3. 架构讲解口径

系统按三层拆分：

| 层级 | 职责 | 代表模块 |
| --- | --- | --- |
| 车载执行层 | 本地意图识别、安全拦截、座舱车控、数据闭环 | `LocalIntentAgent`、`GlobalSafetyDispatchAgent`、`CabinVehicleControlAgent`、`DataUploadAgent` |
| 端云通信层 | 统一请求报文、网络状态、执行结果结构 | `Message`、`VehicleCoreService` |
| 云端决策层 | 用户画像、知识召回、生态数据、路线/补能规划 | `GlobalDispatchAgent`、`UserProfileAgent`、`VectorKnowledgeAgent`、`ExternalEcologyAgent`、`GlobalTripPlanningAgent` |

面试表达重点：

> 我没有把所有逻辑塞进一个 LLM prompt，而是先定义清楚 Agent 边界和数据协议。LLM 负责语义总结和路线说明，安全、车控和 Provider 调用都保持确定性边界。

## 4. 八大 Agent 分工

| Agent | 位置 | 核心职责 | 是否依赖 LLM |
| --- | --- | --- | --- |
| `LocalIntentAgent` | 车端 | 本地 RAG 意图识别、本地小模型上下文管理 | 可选 |
| `GlobalSafetyDispatchAgent` | 车端 | 输入安全拦截、云端结果二次校验 | 不依赖 |
| `CabinVehicleControlAgent` | 车端 | 座椅、空调、离线导航等本地执行 | 不依赖 |
| `DataUploadAgent` | 车端 | 使用事件、偏好更新、数据闭环 | 不依赖 |
| `UserProfileAgent` | 云端 | 用户画像、路线偏好、座舱偏好 | 可选 |
| `VectorKnowledgeAgent` | 云端 | 云端 RAG 召回 | 不直接依赖 |
| `ExternalEcologyAgent` | 云端 | 天气、充电站、POI 聚合 | 不依赖 |
| `GlobalTripPlanningAgent` | 云端 | 高德路线、补能规划、路线说明 | 依赖云端 LLM |

`GlobalDispatchAgent` 是编排器，不算入八大业务 Agent。它负责把云端 Agent 按任务类型串起来。

## 5. LangGraph 工作流

当前默认启用 LangGraph。系统启动时优先尝试真实 `StateGraph`；如果环境没有安装 `langgraph`，会自动回退到项目内置 lightweight graph；如需强制关闭，可设置：

```text
ENABLE_LANGGRAPH=0
```

在线导航/补能图路径：

```text
profile -> knowledge -> route_preference -> ecology -> trip_plan -> decision -> assemble
```

车控/个性化图路径会跳过 `trip_plan`，避免把温度、座椅、画像查询误送到地图路线规划。

面试表达：

> 我先把节点函数、状态结构和条件分流抽象清楚，再接入 LangGraph。这样同一套业务节点既能用真实 `StateGraph` 跑，也能在低依赖环境 fallback，符合课程 offline 交付和真实框架展示两个目标。

## 6. RAG 与 LLM 接入点

RAG 分布在多个位置：

| 位置 | 用途 |
| --- | --- |
| `LocalIntentAgent` | 本地意图识别和相似指令召回 |
| `VectorKnowledgeAgent` | 云端意图、画像、路线知识召回 |
| `UserProfileAgent` | 用户画像和长期偏好召回 |
| `GlobalTripPlanningAgent` | 路线规划知识增强 |

LLM 接入点：

- 云端 DeepSeek：路线说明、最终执行说明。
- 本地 LLM Provider：模拟车端离线小模型，可切换 mock、Ollama、LM Studio、llama.cpp server。
- 安全与车控：不交给 LLM 做最终判断。

## 7. 本地上下文管理

本地上下文只服务车端本地 Agent，默认作用域：

```text
agent_id = local_intent
session_id = default
```

上下文内容包括：

- 最近多轮交互
- 压缩摘要
- 本地 RAG 召回
- 用户偏好状态
- 车辆状态
- 本地 LLM prompt 预览

面试表达：

> 云端 LLM 可以保持请求级无状态，但车端离线小模型上下文窗口小，所以我只给单个本地 Agent 做上下文管理。这样既能模拟车载小模型的窗口压缩，又避免全局共享记忆带来的污染。

## 8. 安全策略

安全链路有两层：

1. 输入侧安全拦截：用户说“关闭AEB”“加速到100km/h”等，会在车端前置拦截。
2. 云端结果二次校验：如果云端结果包含可执行危险动作，也会被车端拦截。

最近一次全面测试修复了一个重要问题：云端结果里如果只是普通安全提示，例如“注意制动距离和AEB状态”，不应该被误判为危险动作。现在系统只拦截“关闭AEB”“立即加速”等可执行危险控制语句。

## 9. 演示流程

推荐 5 步演示：

| 步骤 | 指令 | 讲解重点 |
| --- | --- | --- |
| 1 | `导航去蔚来中心` | 在线端云协同、LangGraph、RAG、DeepSeek、高德路线 |
| 2 | `温度调到24度` | 车控指令不调用路线 Agent，体现按意图分流 |
| 3 | `电量低` | 补能 RAG、高德 POI、附近充电站 |
| 4 | `关闭AEB` | 车规安全拦截，危险指令不进入执行链路 |
| 5 | `导航去巴黎` | 在线真实 Provider 失败时不造假，返回友好错误解释 |

演示时重点看这些面板：

- Agent 调用链
- Runtime Trace
- RAG 召回知识
- Graph 模式和路径
- 路线与补能
- 本地意图 Agent 上下文
- Provider 状态
- 验收报告

## 10. 验收与 QA

自动化验收：

```bash
python scripts/run_acceptance.py
```

Web QA：

```bash
python scripts/web_qa.py --base-url http://127.0.0.1:8000 --screenshots
```

当前验收覆盖：

- 121 条单元测试
- 20 条离线评测样本
- DeepSeek、Open-Meteo、高德路线、高德 POI smoke test
- 在线矩阵测试
- Web 静态资源检查
- Web API 关键场景检查
- 桌面和移动视口截图

面试表达：

> 我不是靠手工点页面证明项目能跑，而是把单元测试、离线评测、真实 Provider smoke、在线矩阵和 Web QA 串起来。每次改动后都能生成验收报告和浏览器截图，这说明项目具备基本工程可验证性。

## 11. 简历写法

长版：

> 设计并实现车载 Multi-Agent 端云协同 AI 应用原型，基于 Python 构建 8 个业务 Agent 和 LangGraph 云端编排工作流，支持本地 RAG 意图识别、车规级安全拦截、DeepSeek 路线/决策说明、高德地图路线与 POI、Open-Meteo 天气、本地 LLM 上下文压缩、用户偏好数据闭环和 Web 可视化。建立一键验收脚本与 Web QA 脚本，覆盖单元测试、离线评测、Provider smoke、在线矩阵和浏览器截图，形成可演示、可解释、可验证的 AI 应用工程项目。

短版：

> 车载智能座舱 Multi-Agent 项目：实现 8 Agent 端云协同、默认 LangGraph 编排、RAG 检索增强、DeepSeek/高德/Open-Meteo 接入、安全拦截、本地上下文管理、Web 可视化和自动化验收。

## 12. 后续可扩展方向

优先级从高到低：

1. 接入真实本地 LLM：Ollama / LM Studio / llama.cpp。
2. 将 `SimpleRetriever` 替换为 FAISS 或 Milvus。
3. 增加 LangGraph checkpoint、interrupt、human-in-the-loop。
4. 引入更完整的安全策略集和权限系统。
5. 把 JSONL 数据闭环迁移到 SQLite 或轻量数据库。

## 13. 交付级演示脚本

面试时建议不要从“项目用了哪些技术”开始讲，而是从“车载 AI 为什么需要端云协同和多 Agent”切入，然后按下面 5 个场景现场演示。

| 顺序 | 场景 | 操作 | 讲解重点 |
| --- | --- | --- | --- |
| 1 | 正常导航端云协同 | 点击 `正常导航端云协同` / 输入 `导航去蔚来中心` | 展示本地意图识别、安全校验、LangGraph 云端编排、RAG、地图路线、LLM 最终说明。 |
| 2 | 模糊目的地澄清 | 点击 `模糊目的地澄清` / 输入 `导航去北京` | 说明导航不是地图返回一个点就执行，城市级或低置信度目的地要进入 `NEEDS_CLARIFICATION`。 |
| 3 | 高速速度请求确认 | 点击 `高速速度请求确认` / 输入 `加速到100km/h` | 展示同一句危险相关指令在高速限速 120 场景下不会直接控制动力，而是转为驾驶员确认。 |
| 4 | 城市超限危险拦截 | 点击 `城市超限危险拦截` / 输入 `加速到100km/h` | 展示车辆状态是决策输入：切换到城市限速 60 后，同一句话会被策略层拦截。 |
| 5 | 低电量状态与能源策略 | 点击 `低电量状态与能源策略` / 输入 `导航去蔚来中心` | 展示低电量不是用户输入才触发，而是车辆状态事件；严重低电量会影响后续导航策略。 |

面试表达可以这样收束：

> 这套演示不是单纯把大模型接到车机页面上，而是把车端状态、用户意图、安全策略、云端编排、真实 Provider 和数据闭环串成一个可观测链路。每个场景都能看到 Agent Trace、Runtime Trace、RAG 召回和最终业务状态，因此能解释“为什么执行、为什么拦截、为什么要澄清”。

## 14. 一键交付验收

新增交付验收脚本：

```bash
python scripts/run_delivery_check.py
```

脚本会生成：

```text
reports/delivery_check_report.md
```

验收内容包括：

- 全量单元测试。
- 前端 ES Module 语法检查。
- 五个面试 Demo 场景回归。
- 可选真实 Provider smoke test：`python scripts/run_delivery_check.py --include-provider-smoke`。

快速演示前检查：

```bash
python scripts/run_delivery_check.py --skip-unit-tests
```

当前稳定测试基线：

```text
231 passed, 1 warning, 139 subtests passed
```

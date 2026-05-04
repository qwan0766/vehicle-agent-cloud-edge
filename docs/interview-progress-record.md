# 面试准备记录：当前项目已完成内容

## 1. 当前项目定位

项目名称：车载 Multi-Agent 端云协同系统开发（offline）

当前版本已经从控制台 demo 扩展为一个可运行、可测试、可网页展示的 AI 应用工程原型。

一句话介绍：

> 这是一个面向智能座舱场景的端云协同 Multi-Agent 原型系统，支持本地意图识别、云端多 Agent 调度、RAG 思想模拟、安全拦截、断网兜底和网页可视化展示。

## 2. 已完成阶段

### 2.1 项目初始化与文档规划

已完成：

- 建立本地 git 仓库。
- 编写项目初始指导文档 `README.md`。
- 编写项目启动方案 `docs/project-kickoff.md`。
- 编写 MVP 实现计划 `docs/superpowers/plans/2026-05-04-vehicle-multi-agent-mvp.md`。

面试表达：

> 我不是直接堆功能，而是先明确项目定位、MVP 边界、目录结构和实现顺序。这样可以保证后续代码围绕清晰的工程目标推进。

### 2.2 核心协议层

已完成文件：

- `core/constants.py`
- `core/message.py`
- `tests/test_core_message.py`

核心设计：

- `CommandType`：定义导航、车控、充电规划、个性化等意图。
- `SafetyLevel`：定义安全和危险。
- `NetworkStatus`：定义在线和离线。
- `ExecutionStatus`：定义执行、拦截和兜底。
- `Message`：统一封装端云请求。

面试表达：

> 多 Agent 系统里，如果模块之间随意传字符串，后续很难测试和扩展。所以我先定义统一 Message 协议，让车端、云端、网页展示和测试都围绕同一套数据结构协作。

### 2.3 离线数据层

已完成文件：

- `data/knowledge_base.py`
- `data/user_profiles.py`
- `data/vehicle_state.py`
- `tests/test_data_sources.py`

当前数据包括：

- 本地意图知识库。
- 路线规划知识。
- 危险关键词。
- 用户画像。
- 车辆状态。
- 外部生态模拟数据。

面试表达：

> 第一版保持 offline，使用本地数据模拟 RAG、用户画像和外部生态。这样可以保证项目无依赖、可复现，同时保留后续替换真实向量库和外部 API 的接口边界。

### 2.4 车载端 Agent

已完成文件：

- `agents/vehicle/safety_agent.py`
- `agents/vehicle/local_intent_agent.py`
- `agents/vehicle/car_control_agent.py`
- `agents/vehicle/nav_agent.py`
- `tests/test_safety_agent.py`
- `tests/test_intent_agent.py`

职责拆分：

- `SafetyAgent`：危险指令拦截。
- `LocalIntentAgent`：本地意图识别。
- `CarControlAgent`：车控执行模拟。
- `NavAgent`：导航执行模拟。

关键点：

- “加速到100km/h” 会被识别为 `CAR_CONTROL`。
- 同时会被 `SafetyAgent` 标记为 `DANGEROUS`。
- 最终执行状态是 `BLOCKED`。

面试表达：

> 加速、制动、转向这些指令从语义上属于车控意图，但在安全等级上属于危险指令。所以系统会先识别它是什么，再由 SafetyAgent 判断能不能执行。这样输出能同时说明“它是什么”和“为什么被拦截”。

### 2.5 云端 Agent

已完成文件：

- `agents/cloud/cloud_schedule_agent.py`
- `agents/cloud/cloud_user_profile_agent.py`
- `agents/cloud/cloud_ecology_agent.py`
- `agents/cloud/cloud_route_plan_agent.py`
- `tests/test_cloud_agents.py`

职责拆分：

- `CloudScheduleAgent`：模拟 LangChain 多 Agent 调度。
- `CloudUserProfileAgent`：用户画像召回。
- `CloudEcologyAgent`：天气、换电站等生态数据模拟。
- `CloudRoutePlanAgent`：云端 RAG 路线规划模拟。

面试表达：

> 云端 Agent 负责更复杂的决策和外部生态聚合。当前版本使用本地数据模拟，后续可以把 CloudEcologyAgent 替换为天气 API 或充电站 API，把 CloudRoutePlanAgent 替换为真实 RAG 检索。

### 2.6 核心编排层与控制台入口

已完成文件：

- `core/vehicle_core_service.py`
- `main.py`
- `tests/test_vehicle_core_service.py`

核心链路：

```text
用户输入
  -> LocalIntentAgent
  -> SafetyAgent
  -> Message
  -> 网络状态判断
  -> ONLINE: CloudScheduleAgent
  -> OFFLINE: 本地 Agent / 本地兜底
  -> ExecutionResult
```

控制台覆盖场景：

- 行程启动：导航去蔚来中心。
- 行驶途中：断网打开座椅加热。
- 中途补给：电量低。
- 行程结束：我的偏好。
- 安全测试：加速到100km/h。

面试表达：

> VehicleCoreService 是流程编排层，不直接承担具体业务能力。具体能力交给 Agent，编排层负责意图、安全、网络判断和结果封装。这种拆分让每个模块职责更清晰，也更容易测试。

### 2.7 网页展示层

已完成文件：

- `web_demo/server.py`
- `web_demo/app_model.py`
- `web_demo/static/index.html`
- `web_demo/static/styles.css`
- `web_demo/static/app.js`
- `tests/test_web_demo_app_model.py`
- `docs/web-demo.md`

网页能力：

- 展示车辆状态：车速、电量、网络、GPS。
- 支持 ONLINE/OFFLINE 切换。
- 支持预设指令按钮。
- 支持自定义指令输入。
- 展示 Agent 调用链。
- 展示 request_id、意图、安全等级、执行状态和最终结果。

面试表达：

> 网页层没有直接耦合 Agent 内部实现，而是通过 `web_demo/app_model.py` 把核心服务输出转换成稳定 JSON。这样前端只关心展示协议，后端 Agent 可以独立演进。

## 3. 当前技术路线

当前版本使用：

- Python 标准库。
- `dataclasses`
- `enum`
- `unittest`
- `http.server`
- 原生 HTML / CSS / JavaScript

没有引入：

- 大模型 API。
- 向量数据库。
- LangChain 真实依赖。
- FastAPI / Flask。
- Streamlit。
- Docker。

工程取舍：

> 当前阶段重点是验证 Agent 编排、端云协同、安全拦截和断网兜底。为了保证应届生作品的可运行性和可复现性，第一版刻意保持零额外依赖。

## 4. 当前验证情况

已建立自动化测试：

- 核心协议测试。
- 数据源测试。
- 意图识别测试。
- 安全拦截测试。
- 云端 Agent 测试。
- 核心编排测试。
- 网页展示模型测试。

最近验证结果：

```text
Ran 17 tests
OK
```

网页服务验证：

```text
GET http://127.0.0.1:8000/
StatusCode: 200
```

## 5. 当前项目亮点

### 5.1 不是普通聊天机器人

项目不是只做问答，而是包含：

- 意图识别。
- 安全判断。
- 端云路由。
- Agent 调度。
- 本地执行。
- 断网兜底。
- 页面展示。

面试表达：

> 普通聊天机器人主要关注生成文本，而这个项目关注 AI 能力如何进入业务执行链路，这更接近 AI 应用工程师岗位的工作。

### 5.2 安全策略前置

危险指令不会进入执行链路。

面试表达：

> 在车载场景中，安全优先级高于模型能力。即使云端可用，危险车控指令也必须先在本地被拦截。

### 5.3 端云协同清晰

ONLINE 和 OFFLINE 走不同路径：

- ONLINE：上报云端多 Agent 调度。
- OFFLINE：本地 Agent 或本地规则兜底。

面试表达：

> 这个设计体现了车端和云端职责差异。车端负责实时性和可用性，云端负责更复杂的个性化和路线规划。

### 5.4 网页展示可讲清链路

网页能直接看到：

- 用户输入。
- Agent 调用链。
- 安全等级。
- 执行状态。
- 最终结果。

面试表达：

> 我做网页展示不是为了好看，而是为了让端云协同和 Agent 调用链可观察。这样面试时可以更直观地解释系统行为。

## 6. 演示路径建议

### 6.1 控制台演示

```bash
python main.py
```

如果本机 `python` 不可用：

```bash
C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe main.py
```

### 6.2 网页演示

```bash
python web_demo/server.py
```

访问：

```text
http://127.0.0.1:8000
```

建议演示顺序：

1. `导航去蔚来中心` + ONLINE：展示云端多 Agent 调度。
2. `打开座椅加热` + OFFLINE：展示断网本地执行。
3. `电量低` + ONLINE：展示补能规划。
4. `加速到100km/h` + ONLINE：展示危险指令拦截。

## 7. 简历描述草稿

可以写成：

> 设计并实现车载端云协同 Multi-Agent 原型系统，拆分车载执行层、端云通信层与云端决策层，构建 SafetyAgent、LocalIntentAgent、CarControlAgent、NavAgent、CloudScheduleAgent 等 8 个 Agent；通过本地知识库模拟 RAG 意图识别、用户画像召回和路线规划；实现危险车控指令拦截、断网本地兜底、统一消息协议、网页可视化展示和 17 个核心单元测试。

## 8. 下一步建议

下一步建议不是马上接大模型，而是先把模拟 RAG 升级为可解释的本地检索模块：

```text
rag/
├── documents.py
└── simple_retriever.py
```

目标：

- 让 `LocalIntentAgent` 通过检索识别相似表达。
- 让 `CloudRoutePlanAgent` 展示召回知识。
- 在网页上显示 RAG 召回结果。

面试升级表达：

> 当前版本使用本地数据模拟 RAG。下一步我会抽象 Retriever 接口，用关键词评分实现无依赖检索，再逐步替换为 BM25、embedding、FAISS 或 Milvus。

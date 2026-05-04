# 项目启动方案：车载 Multi-Agent 端云协同系统

## 1. 项目定位

本项目应定位为一个面向 AI 应用工程师求职展示的工程化原型，而不是单纯的课堂 demo。

核心目标是证明以下能力：

- 能把复杂业务场景拆成清晰的 Agent 职责。
- 能设计端云协同链路，而不是只写单点功能。
- 能用 RAG 思想增强意图识别、路线规划和用户画像召回。
- 能处理车载场景中的安全拦截、断网兜底和数据闭环。
- 能写出可运行、可测试、可扩展、可讲清楚的工程项目。

面试表达：

> 我没有把这个项目做成简单聊天机器人，而是选择智能座舱场景，是因为它天然包含意图识别、工具执行、安全边界、端云协同和离线兜底。这些能力更接近真实 AI 应用工程岗位的工作内容。

## 2. 第一版 MVP 边界

第一版只做离线可运行系统，不接真实大模型、向量库、MQTT、Docker 或地图 API。

必须跑通的链路：

```text
用户输入
  -> 本地意图识别
  -> 安全拦截
  -> 统一消息封装
  -> 网络状态判断
  -> ONLINE：云端多 Agent 调度
  -> OFFLINE：车端本地执行
  -> 控制台输出结果
```

第一版包含 8 个 Agent：

- SafetyAgent：危险指令拦截。
- LocalIntentAgent：本地意图识别。
- CarControlAgent：车控执行。
- NavAgent：导航执行。
- CloudScheduleAgent：云端多 Agent 调度。
- CloudRoutePlanAgent：云端路线规划。
- CloudUserProfileAgent：用户画像召回。
- CloudEcologyAgent：外部生态数据模拟。

暂不实现的内容：

- 真实 LLM 调用。
- 真实 embedding 模型。
- 真实向量数据库。
- 真实地图、天气、充电站 API。
- 前端页面。
- 复杂权限系统。

工程思维：

> 第一版不是为了技术堆叠，而是为了稳定验证主链路。AI 应用工程里，先跑通可复现闭环，再替换真实模型和外部服务，比一开始堆复杂依赖更稳。

## 3. 建议目录结构

```text
weilaiAgent/
├── README.md
├── main.py
├── agents/
│   ├── vehicle/
│   │   ├── safety_agent.py
│   │   ├── local_intent_agent.py
│   │   ├── car_control_agent.py
│   │   └── nav_agent.py
│   └── cloud/
│       ├── cloud_schedule_agent.py
│       ├── cloud_route_plan_agent.py
│       ├── cloud_user_profile_agent.py
│       └── cloud_ecology_agent.py
├── core/
│   ├── constants.py
│   ├── message.py
│   └── vehicle_core_service.py
├── data/
│   ├── knowledge_base.py
│   ├── user_profiles.py
│   └── vehicle_state.py
├── docs/
│   ├── project-kickoff.md
│   ├── architecture.md
│   ├── engineering-notes.md
│   └── interview-guide.md
└── tests/
    ├── test_intent_agent.py
    ├── test_safety_agent.py
    └── test_vehicle_core_service.py
```

目录设计逻辑：

- `agents/` 表示智能体能力单元。
- `core/` 放系统主流程、统一消息协议和全局枚举。
- `data/` 放模拟知识库、用户画像和车辆状态。
- `docs/` 放工程说明与面试材料。
- `tests/` 保证核心策略可验证。

面试表达：

> 我把 Agent 和 core 分开，是为了避免所有逻辑堆在一个主程序里。Agent 只负责单一能力，core 负责编排流程。后续无论替换真实模型、真实向量库还是外部 API，都不会破坏主流程。

## 4. 开发顺序

### Step 1：定义核心协议

先定义：

- `CommandType`
- `SafetyLevel`
- `NetworkStatus`
- `Message`

原因：

> 多 Agent 系统最容易混乱的地方是模块之间随意传参。先定义统一消息协议，可以让车端、云端、日志和测试共享同一套数据结构。

### Step 2：实现车端 Agent

先写：

- SafetyAgent
- LocalIntentAgent
- CarControlAgent
- NavAgent

原因：

> 车端是实时执行层，必须优先保证安全和断网可用。即使云端不可用，车辆仍需要完成基础车控和离线导航。

### Step 3：实现云端 Agent

再写：

- CloudScheduleAgent
- CloudRoutePlanAgent
- CloudUserProfileAgent
- CloudEcologyAgent

原因：

> 云端负责复杂决策和外部生态整合。第一版用模拟数据实现接口，后续可以替换成真实 RAG、天气 API、充电站 API 和地图 API。

### Step 4：实现 VehicleCoreService

统一编排：

```text
输入 -> 意图 -> 安全 -> 消息 -> 网络判断 -> 执行
```

原因：

> 编排层不应该承担具体业务能力，而应该负责流程控制。这是工程上常见的“能力模块”和“流程编排”分离。

### Step 5：补充测试

优先测试：

- 危险指令必须被拦截。
- 离线车控必须本地执行。
- 在线导航必须走云端。
- 未知用户必须返回默认画像。

原因：

> 面试时能展示测试，说明这个项目不是只能跑一次的脚本，而是具备基本工程质量。

## 5. RAG 设计思路

第一版使用本地字典和规则模拟 RAG：

- 意图识别：从内置指令知识库匹配命令类型。
- 路线规划：从路线知识中返回高速优先、换电建议等。
- 用户画像：从模拟 profile 数据中召回用户偏好。

后续替换路径：

```text
本地字典
  -> TF-IDF / BM25
  -> embedding 模型
  -> FAISS / Milvus
  -> 云端 RAG 服务
```

面试表达：

> 我第一版没有直接引入向量数据库，是因为项目目标是验证 RAG 在端云协同中的位置。当前实现保留了检索接口，后续可以把底层从字典替换成 embedding 和向量库，而上层 Agent 不需要大改。

## 6. 安全与兜底设计

安全策略：

- 危险关键词包括动力、制动、转向、加速、刹车。
- SafetyAgent 在任何执行前运行。
- 危险指令不进入车控执行，也不上报云端执行。

断网兜底：

- ONLINE：走云端调度。
- OFFLINE：本地执行基础车控和导航。
- 不能本地执行的复杂任务返回明确提示。

面试表达：

> 车载 AI 应用不能只考虑回答是否智能，还必须考虑执行是否安全。我的设计里安全拦截优先级高于 Agent 调度，断网时也能完成基础功能，体现的是车载场景的安全性和可用性要求。

## 7. 文档交付计划

后续会同步维护以下文档：

- `docs/architecture.md`：系统架构、端云三层结构、Agent 调用链。
- `docs/engineering-notes.md`：每一步实现背后的工程思维。
- `docs/interview-guide.md`：简历写法、项目讲解稿、面试问答。

每完成一个核心模块，就补充对应的工程说明和面试表达。

## 8. 第一阶段验收标准

第一阶段完成后，项目应满足：

- `python main.py` 可直接运行。
- 控制台能展示四大业务场景。
- 危险指令能被拦截。
- 断网场景能本地兜底。
- 在线场景能进入云端多 Agent 调度。
- 至少有 3 个核心单元测试。
- README 和 docs 能解释清楚架构与面试讲法。

## 9. 给求职的核心启发

这个项目最终应帮助你证明三件事：

1. 你不是只会调用大模型 API，而是能把 AI 能力嵌入业务流程。
2. 你不是只写 demo，而是知道如何做模块化、测试和可扩展设计。
3. 你理解 AI 应用的边界：模型能力之外，还需要安全、兜底、协议和工程治理。

推荐简历描述：

> 设计并实现车载端云协同 Multi-Agent 原型系统，拆分车载执行层、端云通信层与云端决策层，构建 SafetyAgent、LocalIntentAgent、CloudScheduleAgent 等 8 个 Agent；通过本地知识库模拟 RAG 意图识别、用户画像召回和路线规划；实现危险车控指令拦截、断网本地兜底、统一消息协议和核心单元测试。

# 车载 Multi-Agent 端云协同系统开发（offline）

## 快速开始

本项目使用 Python 标准库实现，无需安装额外依赖。

```bash
python main.py
python web_demo/server.py
python run_offline_eval.py
python -m unittest discover -s tests -v
```

如果本机 `python` 命令不可用，请使用 Python 3.8~3.11 解释器运行。

## 项目文档

- [docs/project-kickoff.md](docs/project-kickoff.md)：项目启动方案
- [docs/architecture.md](docs/architecture.md)：系统架构说明
- [docs/engineering-notes.md](docs/engineering-notes.md)：工程思维记录
- [docs/rag-design.md](docs/rag-design.md)：本地 RAG 检索设计
- [docs/profile-personalization.md](docs/profile-personalization.md)：用户画像检索与个性化决策设计
- [docs/data-feedback-loop.md](docs/data-feedback-loop.md)：数据闭环与用户偏好更新设计
- [docs/agent-runtime-tool-registry.md](docs/agent-runtime-tool-registry.md)：Agent Runtime 与 Tool Registry 设计说明
- [docs/offline-completion.md](docs/offline-completion.md)：离线工程闭环完善说明
- [docs/demo-script.md](docs/demo-script.md)：面试演示脚本
- [docs/architecture-diagram.md](docs/architecture-diagram.md)：架构图与链路图
- [docs/final-implementation-summary.md](docs/final-implementation-summary.md)：阶段实现总结
- [docs/interview-guide.md](docs/interview-guide.md)：面试讲解指南
- [docs/interview-progress-record.md](docs/interview-progress-record.md)：当前成果与面试准备记录
- [docs/web-demo.md](docs/web-demo.md)：网页展示说明
- [docs/superpowers/plans/2026-05-04-vehicle-multi-agent-mvp.md](docs/superpowers/plans/2026-05-04-vehicle-multi-agent-mvp.md)：MVP 实现计划

## 1. 基本信息

### 1.1 项目名称

车载 Multi-Agent 端云协同系统开发（offline）

### 1.2 训练目标

1. 掌握端云协同三层架构：车载执行层 / 端云通信层 / 云端决策层。
2. 掌握 8 大 Agent 职责拆分与模块化开发。
3. 理解并实现 RAG 检索增强生成：本地意图识别 + 云端路线规划。
4. 理解并实现 LangChain 多 Agent 编排调度思想。
5. 掌握车规级安全拦截、断网兜底、数据闭环。
6. 能够使用公开数据集与 API 扩展真实项目能力。

### 1.3 运行环境

- Python 3.8 ~ 3.11
- 无需安装模型、向量库、MQTT、Docker
- 纯 CPU 可运行
- 无环境依赖冲突

### 1.4 交付内容

1. 完整可运行代码文件（`.py`）
2. 控制台运行成功截图
3. 可选：公开 API / 数据集扩展说明

---

## 2. 内置数据集与公开扩展数据源

### 2.1 内置使用数据

#### 2.1.1 用户指令集（意图识别输入）

```text
导航去蔚来中心
我要回家
打开座椅加热
温度调到24度
电量低
我的偏好
加速到100km/h（危险指令）
```

#### 2.1.2 用户画像 / 偏好数据（向量库模拟）

```text
user_001：温度24℃，座椅加热自动开启，路线偏好高速
user_002：温度22℃，音乐音量30%，充电提醒20%
```

#### 2.1.3 RAG 知识库（本地 + 云端）

```text
电量低于20%建议前往换电站
长途优先高速路线
车内舒适温度22~25℃
换电站约3分钟完成换电
断网时自动切换离线导航
危险指令：动力、制动、转向、加速
```

#### 2.1.4 车辆状态数据

```text
车速：60km/h
电量：35%
网络：ONLINE/OFFLINE
GPS：121.48, 31.23
```

### 2.2 公开数据源链接（可自由扩展）

#### 2.2.1 车载对话 / 意图数据集

- [AISHELL-5 智能座舱中文语音数据集](https://aishelltech.com/AISHELL_5)
- [CAR-Bench 车载交互数据集](https://huggingface.co/datasets/johanneskirmayr/car-bench-dataset)

#### 2.2.2 充电站 / 路况开放 API

- [OpenChargeMap 全球充电站 API（免费）](https://api.openchargemap.io/v3/poi/)
- [百度地图开放平台](https://lbsyun.baidu.com/)

#### 2.2.3 天气开放 API

- [Open-Meteo 无 Key 免费天气 API](https://open-meteo.com/)
- [OpenWeatherMap 免费天气 API](https://openweathermap.org/)

#### 2.2.4 车辆行驶开源数据集

- [清华 DAIR-V2X 车路协同数据集](https://air.tsinghua.edu.cn/DAIR.htm)
- [Udacity 自动驾驶公开数据集](https://www.udacity.com/)

---

## 3. 系统设计说明

### 3.1 模拟车载端

- 本地 RAG 意图识别
- 安全校验
- 车控执行
- 导航执行

### 3.2 模拟云端

- LangChain 多 Agent 调度
- 云端 RAG 路线规划
- 用户画像（向量库模拟）
- 外部生态模拟：离线天气 Provider + 离线换电站 Provider
- Tool Schema：工具输入输出协议校验

### 3.3 模拟端云交互

- 联网：走云端
- 断网：走本地
- 使用统一报文格式

### 3.4 模拟业务场景

- 行程启动
- 行驶途中
- 中途补给
- 行程结束

### 3.5 离线评测

- 内置 20 条离线场景样本。
- 评估意图准确率、安全拦截召回率、执行状态准确率和 RAG 命中率。
- 运行命令：

```bash
python run_offline_eval.py
```

---

## 4. 完整可运行代码

建议将以下代码保存为 `vehicle_multi_agent_offline.py`，然后使用 Python 运行：

```bash
python vehicle_multi_agent_offline.py
```

```python
from dataclasses import dataclass
import uuid


# ==========================
# 1. 企业级全局规范
# ==========================
class CommandType:
    NAVIGATION = "NAVIGATION"
    CAR_CONTROL = "CAR_CONTROL"
    CHARGE_PLAN = "CHARGE_PLAN"
    PERSONALIZE = "PERSONALIZE"


class SafetyLevel:
    SAFE = "SAFE"
    DANGEROUS = "DANGEROUS"


class NetworkStatus:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


@dataclass
class Message:
    request_id: str
    user_id: str
    command_type: str
    safety: str
    content: str
    network: str


# ==========================
# 2. 车载端 4 个 Agent
# ==========================
class SafetyAgent:
    def check(self, content):
        dangerous_keywords = ["动力", "制动", "转向", "加速", "刹车"]
        for kw in dangerous_keywords:
            if kw in content:
                return SafetyLevel.DANGEROUS
        return SafetyLevel.SAFE


class LocalIntentAgent:
    def __init__(self):
        self.knowledge_base = {
            "导航去蔚来中心": CommandType.NAVIGATION,
            "我要回家": CommandType.NAVIGATION,
            "打开座椅加热": CommandType.CAR_CONTROL,
            "温度调到24度": CommandType.CAR_CONTROL,
            "电量低": CommandType.CHARGE_PLAN,
            "我的偏好": CommandType.PERSONALIZE,
        }

    def recognize(self, user_input):
        for key, intent in self.knowledge_base.items():
            if user_input in key:
                return intent
        return CommandType.CAR_CONTROL


class CarControlAgent:
    def execute(self, cmd):
        return f"✅ 车控执行成功：{cmd}"


class NavAgent:
    def start(self, destination):
        return f"✅ 导航启动：目的地 {destination}"


# ==========================
# 3. 云端 4 个 Agent
# ==========================
class CloudScheduleAgent:
    def __init__(self):
        self.user_agent = CloudUserProfileAgent()
        self.route_agent = CloudRoutePlanAgent()
        self.ecology_agent = CloudEcologyAgent()

    def dispatch(self, msg: Message):
        print("\n==== 云端LangChain多Agent调度 ====")
        user_pref = self.user_agent.get_profile(msg.user_id)
        ecology = self.ecology_agent.get_data()
        route = self.route_agent.plan(msg.content)
        return f"{user_pref} | {ecology} | {route}"


class CloudRoutePlanAgent:
    def plan(self, content):
        return f"RAG路线结果：{content}，推荐高速优先"


class CloudUserProfileAgent:
    def __init__(self):
        self.profile_db = {
            "user_001": "用户偏好：温度24℃，座椅加热自动开启",
            "user_002": "用户偏好：温度22℃，音乐音量30%",
        }

    def get_profile(self, user_id):
        return self.profile_db.get(user_id, "默认偏好：温度24℃")


class CloudEcologyAgent:
    def get_data(self):
        return "外部生态数据：天气晴，换电站空闲"


# ==========================
# 4. 车载端总入口（端云协同）
# ==========================
class VehicleCoreService:
    def __init__(self):
        self.safety = SafetyAgent()
        self.intent_agent = LocalIntentAgent()
        self.car_control = CarControlAgent()
        self.nav = NavAgent()
        self.cloud = CloudScheduleAgent()

    def run(self, user_input, user_id="user_001", network=NetworkStatus.ONLINE):
        print("\n========================================")
        print(f"用户输入：{user_input}")

        cmd_type = self.intent_agent.recognize(user_input)
        safety = self.safety.check(user_input)

        msg = Message(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            command_type=cmd_type,
            safety=safety,
            content=user_input,
            network=network,
        )

        print(f"解析意图：{cmd_type}")
        print(f"安全等级：{safety}")

        if msg.safety == SafetyLevel.DANGEROUS:
            print("❌ 危险指令，已拦截！")
            return

        if msg.network == NetworkStatus.OFFLINE:
            print("✅ 断网模式，本地执行")
            if cmd_type == CommandType.CAR_CONTROL:
                print(self.car_control.execute(user_input))
            elif cmd_type == CommandType.NAVIGATION:
                print(self.nav.start(user_input))
            return

        print("✅ 联网模式，上报云端")
        result = self.cloud.dispatch(msg)
        print(f"\n✅ 最终执行结果：{result}")


# ==========================
# 5. 四大场景 + 安全测试
# ==========================
if __name__ == "__main__":
    vehicle = VehicleCoreService()

    print("==== 场景1：行程启动（端云协同）====")
    vehicle.run("导航去蔚来中心", network=NetworkStatus.ONLINE)

    print("\n==== 场景2：行驶途中（断网本地执行）====")
    vehicle.run("打开座椅加热", network=NetworkStatus.OFFLINE)

    print("\n==== 场景3：中途补给（充电规划）====")
    vehicle.run("电量低", network=NetworkStatus.ONLINE)

    print("\n==== 场景4：行程结束（数据闭环）====")
    vehicle.run("我的偏好", network=NetworkStatus.ONLINE)

    print("\n==== 安全测试：危险指令拦截 ====")
    vehicle.run("加速到100km/h")
```

---

## 5. 预期运行结果

```text
==== 场景1：行程启动（端云协同）====

========================================
用户输入：导航去蔚来中心
解析意图：NAVIGATION
安全等级：SAFE
✅ 联网模式，上报云端

==== 云端LangChain多Agent调度 ====

✅ 最终执行结果：用户偏好：温度24℃，座椅加热自动开启 | 外部生态数据：天气晴，换电站空闲 | RAG路线结果：导航去蔚来中心，推荐高速优先

==== 场景2：行驶途中（断网本地执行）====

========================================
用户输入：打开座椅加热
解析意图：CAR_CONTROL
安全等级：SAFE
✅ 断网模式，本地执行
✅ 车控执行成功：打开座椅加热

==== 场景3：中途补给（充电规划）====
...

==== 场景4：行程结束（数据闭环）====
...

==== 安全测试：危险指令拦截 ====

========================================
用户输入：加速到100km/h
解析意图：CAR_CONTROL
安全等级：DANGEROUS
❌ 危险指令，已拦截！
```

---

## 6. 可视化展示说明（控制台文字可视化）

### 6.1 端云协同流程可视化

```text
【端云协同全流程】
用户指令
  → 本地RAG意图识别
  → 安全校验
  → 断网/联网判断
  → 联网：云端LangChain多Agent调度
  → 结果返回执行
  → 断网：本地直接执行
  → 结果返回
```

### 6.2 Agent 调用关系可视化

```text
【车载端Agent调用链】
SafetyAgent → LocalIntentAgent → CarControlAgent / NavAgent

【云端Agent调用链】
CloudScheduleAgent(LangChain) → UserProfileAgent → EcologyAgent → RoutePlanAgent(RAG)
```

### 6.3 车辆状态面板可视化

可在程序中自行 `print`：

```text
======== 车辆状态面板 ========
车速：60 km/h
电量：35 %
网络状态：ONLINE
安全状态：正常
==============================
```

---

## 7. 扩展方向（可选做）

1. 接入 Open-Meteo 真实天气 API。
2. 接入 OpenChargeMap 真实充电站数据。
3. 使用 HuggingFace 轻量模型替换本地 RAG。
4. 接入 Milvus 向量库实现真实用户画像。
5. 接入百度地图 API 实现真实导航路线。

---

## 8. 建议项目结构

初始阶段可以保持单文件运行，便于理解端云协同流程：

```text
weilaiAgent/
├── README.md
└── vehicle_multi_agent_offline.py
```

后续扩展时，可逐步拆分为模块化结构：

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
├── data/
│   ├── knowledge_base.py
│   ├── user_profiles.py
│   └── vehicle_state.py
└── tests/
    └── test_vehicle_core_service.py
```

## 9. 学习重点

本项目不是为了接入复杂依赖，而是通过最小可运行系统理解车载智能体协同的核心思想：

- 车载端负责实时性、安全性与断网兜底。
- 云端负责复杂推理、路线规划、用户画像与生态数据聚合。
- RAG 思想可以先用本地字典和规则模拟，再逐步替换为真实向量库。
- LangChain 多 Agent 编排思想可以先用调度类模拟，再逐步替换为真实框架。
- 安全拦截必须优先于执行链路，危险指令不能进入车控执行。

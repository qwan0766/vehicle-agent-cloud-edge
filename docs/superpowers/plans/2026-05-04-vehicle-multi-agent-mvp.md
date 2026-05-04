# Vehicle Multi-Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable offline vehicle Multi-Agent端云协同 MVP with safety interception, local fallback, cloud scheduling, simulated RAG, tests, and interview-oriented documentation.

**Architecture:** The system is split into small Python modules: `core/` owns protocol and orchestration, `agents/` owns vehicle/cloud capabilities, `data/` owns simulated knowledge and state, `tests/` verifies critical behavior, and `docs/` explains engineering thinking. The first version uses standard library only so it runs on Python 3.8~3.11 without dependency conflicts.

**Tech Stack:** Python standard library, `dataclasses`, `enum`, `unittest`, console output.

---

## File Structure

- Create: `main.py`  
  CLI entrypoint that runs four business scenarios and one safety scenario.
- Create: `core/constants.py`  
  Defines command types, safety levels, network status, and execution status.
- Create: `core/message.py`  
  Defines the unified request message used between vehicle and cloud layers.
- Create: `core/vehicle_core_service.py`  
  Orchestrates intent recognition, safety check, network routing, local execution, and cloud dispatch.
- Create: `data/knowledge_base.py`  
  Stores local intent knowledge, route knowledge, dangerous keywords, and ecosystem mock data.
- Create: `data/user_profiles.py`  
  Stores simulated user profile data.
- Create: `data/vehicle_state.py`  
  Defines the default vehicle state panel data.
- Create: `agents/vehicle/safety_agent.py`  
  Blocks dangerous commands before execution.
- Create: `agents/vehicle/local_intent_agent.py`  
  Recognizes local user intent using a lightweight RAG-like knowledge lookup.
- Create: `agents/vehicle/car_control_agent.py`  
  Simulates vehicle control execution.
- Create: `agents/vehicle/nav_agent.py`  
  Simulates local navigation execution.
- Create: `agents/cloud/cloud_schedule_agent.py`  
  Simulates LangChain-style multi-agent cloud orchestration.
- Create: `agents/cloud/cloud_route_plan_agent.py`  
  Simulates cloud RAG route planning.
- Create: `agents/cloud/cloud_user_profile_agent.py`  
  Simulates user profile retrieval.
- Create: `agents/cloud/cloud_ecology_agent.py`  
  Simulates external ecosystem data.
- Create: `tests/test_safety_agent.py`  
  Verifies dangerous command interception.
- Create: `tests/test_intent_agent.py`  
  Verifies command intent recognition.
- Create: `tests/test_vehicle_core_service.py`  
  Verifies online dispatch, offline fallback, and dangerous command blocking.
- Create: `docs/architecture.md`  
  Explains architecture and data flow.
- Create: `docs/engineering-notes.md`  
  Records engineering logic behind each module.
- Create: `docs/interview-guide.md`  
  Provides resume wording and interview answers.

Current workspace is not a git repository, so this plan uses verification checkpoints instead of commit checkpoints.

---

## Task 1: Core Protocol

**Files:**

- Create: `core/constants.py`
- Create: `core/message.py`
- Create: `core/__init__.py`
- Test: `tests/test_core_message.py`

- [ ] **Step 1: Write the failing protocol test**

Create `tests/test_core_message.py`:

```python
import unittest

from core.constants import CommandType, NetworkStatus, SafetyLevel
from core.message import Message


class TestCoreMessage(unittest.TestCase):
    def test_message_carries_unified_request_fields(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去蔚来中心",
            network=NetworkStatus.ONLINE,
        )

        self.assertTrue(msg.request_id)
        self.assertEqual(msg.user_id, "user_001")
        self.assertEqual(msg.command_type, CommandType.NAVIGATION)
        self.assertEqual(msg.safety, SafetyLevel.SAFE)
        self.assertEqual(msg.content, "导航去蔚来中心")
        self.assertEqual(msg.network, NetworkStatus.ONLINE)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_core_message -v
```

Expected: fail because `core.constants` and `core.message` do not exist.

- [ ] **Step 3: Write minimal protocol implementation**

Create `core/__init__.py`:

```python
"""Core protocol and orchestration modules."""
```

Create `core/constants.py`:

```python
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self):
        return self.value


class CommandType(StrEnum):
    NAVIGATION = "NAVIGATION"
    CAR_CONTROL = "CAR_CONTROL"
    CHARGE_PLAN = "CHARGE_PLAN"
    PERSONALIZE = "PERSONALIZE"
    UNKNOWN = "UNKNOWN"


class SafetyLevel(StrEnum):
    SAFE = "SAFE"
    DANGEROUS = "DANGEROUS"


class NetworkStatus(StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class ExecutionStatus(StrEnum):
    EXECUTED = "EXECUTED"
    BLOCKED = "BLOCKED"
    FALLBACK = "FALLBACK"
```

Create `core/message.py`:

```python
from dataclasses import dataclass
import uuid

from core.constants import CommandType, NetworkStatus, SafetyLevel


@dataclass(frozen=True)
class Message:
    request_id: str
    user_id: str
    command_type: CommandType
    safety: SafetyLevel
    content: str
    network: NetworkStatus

    @classmethod
    def create(
        cls,
        user_id: str,
        command_type: CommandType,
        safety: SafetyLevel,
        content: str,
        network: NetworkStatus,
    ):
        return cls(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            command_type=command_type,
            safety=safety,
            content=content,
            network=network,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.test_core_message -v
```

Expected: pass.

---

## Task 2: Simulated Data and RAG Knowledge

**Files:**

- Create: `data/__init__.py`
- Create: `data/knowledge_base.py`
- Create: `data/user_profiles.py`
- Create: `data/vehicle_state.py`
- Test: `tests/test_data_sources.py`

- [ ] **Step 1: Write the failing data source test**

Create `tests/test_data_sources.py`:

```python
import unittest

from core.constants import CommandType
from data.knowledge_base import (
    DANGEROUS_KEYWORDS,
    INTENT_KNOWLEDGE,
    ROUTE_KNOWLEDGE,
)
from data.user_profiles import USER_PROFILES, DEFAULT_PROFILE
from data.vehicle_state import DEFAULT_VEHICLE_STATE


class TestDataSources(unittest.TestCase):
    def test_builtin_intent_knowledge_contains_required_examples(self):
        self.assertEqual(INTENT_KNOWLEDGE["导航去蔚来中心"], CommandType.NAVIGATION)
        self.assertEqual(INTENT_KNOWLEDGE["电量低"], CommandType.CHARGE_PLAN)
        self.assertEqual(INTENT_KNOWLEDGE["我的偏好"], CommandType.PERSONALIZE)

    def test_safety_and_profile_data_are_available(self):
        self.assertIn("加速", DANGEROUS_KEYWORDS)
        self.assertIn("长途优先高速路线", ROUTE_KNOWLEDGE)
        self.assertIn("user_001", USER_PROFILES)
        self.assertIn("温度24", DEFAULT_PROFILE)
        self.assertEqual(DEFAULT_VEHICLE_STATE.speed_kmh, 60)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_data_sources -v
```

Expected: fail because `data` modules do not exist.

- [ ] **Step 3: Write data modules**

Create `data/__init__.py`:

```python
"""Built-in offline data sources."""
```

Create `data/knowledge_base.py`:

```python
from core.constants import CommandType


INTENT_KNOWLEDGE = {
    "导航去蔚来中心": CommandType.NAVIGATION,
    "我要回家": CommandType.NAVIGATION,
    "打开座椅加热": CommandType.CAR_CONTROL,
    "温度调到24度": CommandType.CAR_CONTROL,
    "电量低": CommandType.CHARGE_PLAN,
    "我的偏好": CommandType.PERSONALIZE,
}

ROUTE_KNOWLEDGE = [
    "电量低于20%建议前往换电站",
    "长途优先高速路线",
    "车内舒适温度22~25℃",
    "换电站约3分钟完成换电",
    "断网时自动切换离线导航",
]

DANGEROUS_KEYWORDS = ["动力", "制动", "转向", "加速", "刹车"]

ECOLOGY_DATA = {
    "weather": "天气晴",
    "swap_station": "换电站空闲",
}
```

Create `data/user_profiles.py`:

```python
USER_PROFILES = {
    "user_001": "用户偏好：温度24℃，座椅加热自动开启，路线偏好高速",
    "user_002": "用户偏好：温度22℃，音乐音量30%，充电提醒20%",
}

DEFAULT_PROFILE = "默认偏好：温度24℃，舒适优先"
```

Create `data/vehicle_state.py`:

```python
from dataclasses import dataclass

from core.constants import NetworkStatus


@dataclass(frozen=True)
class VehicleState:
    speed_kmh: int
    battery_percent: int
    network: NetworkStatus
    gps: str


DEFAULT_VEHICLE_STATE = VehicleState(
    speed_kmh=60,
    battery_percent=35,
    network=NetworkStatus.ONLINE,
    gps="121.48, 31.23",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.test_data_sources -v
```

Expected: pass.

---

## Task 3: Vehicle-Side Agents

**Files:**

- Create: `agents/__init__.py`
- Create: `agents/vehicle/__init__.py`
- Create: `agents/vehicle/safety_agent.py`
- Create: `agents/vehicle/local_intent_agent.py`
- Create: `agents/vehicle/car_control_agent.py`
- Create: `agents/vehicle/nav_agent.py`
- Test: `tests/test_safety_agent.py`
- Test: `tests/test_intent_agent.py`

- [ ] **Step 1: Write failing vehicle agent tests**

Create `tests/test_safety_agent.py`:

```python
import unittest

from agents.vehicle.safety_agent import SafetyAgent
from core.constants import SafetyLevel


class TestSafetyAgent(unittest.TestCase):
    def test_blocks_dangerous_acceleration_command(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("加速到100km/h"), SafetyLevel.DANGEROUS)

    def test_allows_safe_comfort_command(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("打开座椅加热"), SafetyLevel.SAFE)


if __name__ == "__main__":
    unittest.main()
```

Create `tests/test_intent_agent.py`:

```python
import unittest

from agents.vehicle.local_intent_agent import LocalIntentAgent
from core.constants import CommandType


class TestLocalIntentAgent(unittest.TestCase):
    def test_recognizes_navigation_intent(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("导航去蔚来中心"), CommandType.NAVIGATION)

    def test_recognizes_charge_plan_intent(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("电量低"), CommandType.CHARGE_PLAN)

    def test_unknown_intent_is_unknown(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("播放一首歌"), CommandType.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m unittest tests.test_safety_agent tests.test_intent_agent -v
```

Expected: fail because `agents.vehicle` modules do not exist.

- [ ] **Step 3: Write vehicle agent modules**

Create `agents/__init__.py`:

```python
"""Vehicle and cloud agents."""
```

Create `agents/vehicle/__init__.py`:

```python
"""Vehicle-side agents."""
```

Create `agents/vehicle/safety_agent.py`:

```python
from core.constants import SafetyLevel
from data.knowledge_base import DANGEROUS_KEYWORDS


class SafetyAgent:
    def check(self, content: str) -> SafetyLevel:
        for keyword in DANGEROUS_KEYWORDS:
            if keyword in content:
                return SafetyLevel.DANGEROUS
        return SafetyLevel.SAFE
```

Create `agents/vehicle/local_intent_agent.py`:

```python
from core.constants import CommandType
from data.knowledge_base import INTENT_KNOWLEDGE


class LocalIntentAgent:
    def recognize(self, user_input: str) -> CommandType:
        for example, command_type in INTENT_KNOWLEDGE.items():
            if user_input == example or user_input in example:
                return command_type
        return CommandType.UNKNOWN
```

Create `agents/vehicle/car_control_agent.py`:

```python
class CarControlAgent:
    def execute(self, command: str) -> str:
        return f"车控执行成功：{command}"
```

Create `agents/vehicle/nav_agent.py`:

```python
class NavAgent:
    def start(self, destination: str) -> str:
        return f"导航启动：目的地 {destination}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m unittest tests.test_safety_agent tests.test_intent_agent -v
```

Expected: pass.

---

## Task 4: Cloud-Side Agents

**Files:**

- Create: `agents/cloud/__init__.py`
- Create: `agents/cloud/cloud_user_profile_agent.py`
- Create: `agents/cloud/cloud_ecology_agent.py`
- Create: `agents/cloud/cloud_route_plan_agent.py`
- Create: `agents/cloud/cloud_schedule_agent.py`
- Test: `tests/test_cloud_agents.py`

- [ ] **Step 1: Write failing cloud agent tests**

Create `tests/test_cloud_agents.py`:

```python
import unittest

from agents.cloud.cloud_schedule_agent import CloudScheduleAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from core.constants import CommandType, NetworkStatus, SafetyLevel
from core.message import Message


class TestCloudAgents(unittest.TestCase):
    def test_profile_agent_returns_default_for_unknown_user(self):
        agent = CloudUserProfileAgent()
        self.assertIn("默认偏好", agent.get_profile("missing_user"))

    def test_cloud_schedule_combines_profile_ecology_and_route(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去蔚来中心",
            network=NetworkStatus.ONLINE,
        )
        result = CloudScheduleAgent().dispatch(msg)

        self.assertIn("用户偏好", result)
        self.assertIn("外部生态数据", result)
        self.assertIn("RAG路线结果", result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_cloud_agents -v
```

Expected: fail because `agents.cloud` modules do not exist.

- [ ] **Step 3: Write cloud agent modules**

Create `agents/cloud/__init__.py`:

```python
"""Cloud-side agents."""
```

Create `agents/cloud/cloud_user_profile_agent.py`:

```python
from data.user_profiles import DEFAULT_PROFILE, USER_PROFILES


class CloudUserProfileAgent:
    def get_profile(self, user_id: str) -> str:
        return USER_PROFILES.get(user_id, DEFAULT_PROFILE)
```

Create `agents/cloud/cloud_ecology_agent.py`:

```python
from data.knowledge_base import ECOLOGY_DATA


class CloudEcologyAgent:
    def get_data(self) -> str:
        return (
            f"外部生态数据：{ECOLOGY_DATA['weather']}，"
            f"{ECOLOGY_DATA['swap_station']}"
        )
```

Create `agents/cloud/cloud_route_plan_agent.py`:

```python
from data.knowledge_base import ROUTE_KNOWLEDGE


class CloudRoutePlanAgent:
    def plan(self, content: str) -> str:
        route_hint = "长途优先高速路线"
        if "电量低" in content:
            route_hint = "电量低于20%建议前往换电站"
        elif route_hint not in ROUTE_KNOWLEDGE:
            route_hint = ROUTE_KNOWLEDGE[0]
        return f"RAG路线结果：{content}，{route_hint}"
```

Create `agents/cloud/cloud_schedule_agent.py`:

```python
from agents.cloud.cloud_ecology_agent import CloudEcologyAgent
from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from core.message import Message


class CloudScheduleAgent:
    def __init__(self):
        self.user_agent = CloudUserProfileAgent()
        self.route_agent = CloudRoutePlanAgent()
        self.ecology_agent = CloudEcologyAgent()

    def dispatch(self, msg: Message) -> str:
        user_pref = self.user_agent.get_profile(msg.user_id)
        ecology = self.ecology_agent.get_data()
        route = self.route_agent.plan(msg.content)
        return f"{user_pref} | {ecology} | {route}"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.test_cloud_agents -v
```

Expected: pass.

---

## Task 5: Vehicle Core Service and Entrypoint

**Files:**

- Create: `core/vehicle_core_service.py`
- Create: `main.py`
- Test: `tests/test_vehicle_core_service.py`

- [ ] **Step 1: Write failing orchestration tests**

Create `tests/test_vehicle_core_service.py`:

```python
import unittest

from core.constants import ExecutionStatus, NetworkStatus
from core.vehicle_core_service import VehicleCoreService


class TestVehicleCoreService(unittest.TestCase):
    def test_online_navigation_goes_to_cloud(self):
        service = VehicleCoreService()
        result = service.run("导航去蔚来中心", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.EXECUTED)
        self.assertIn("RAG路线结果", result.output)

    def test_offline_car_control_uses_local_execution(self):
        service = VehicleCoreService()
        result = service.run("打开座椅加热", network=NetworkStatus.OFFLINE)

        self.assertEqual(result.status, ExecutionStatus.FALLBACK)
        self.assertIn("车控执行成功", result.output)

    def test_dangerous_command_is_blocked_before_execution(self):
        service = VehicleCoreService()
        result = service.run("加速到100km/h", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.BLOCKED)
        self.assertIn("危险指令", result.output)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_vehicle_core_service -v
```

Expected: fail because `core.vehicle_core_service` does not exist.

- [ ] **Step 3: Write core service**

Create `core/vehicle_core_service.py`:

```python
from dataclasses import dataclass

from agents.cloud.cloud_schedule_agent import CloudScheduleAgent
from agents.vehicle.car_control_agent import CarControlAgent
from agents.vehicle.local_intent_agent import LocalIntentAgent
from agents.vehicle.nav_agent import NavAgent
from agents.vehicle.safety_agent import SafetyAgent
from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.message import Message


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    output: str
    message: Message


class VehicleCoreService:
    def __init__(self):
        self.safety_agent = SafetyAgent()
        self.intent_agent = LocalIntentAgent()
        self.car_control_agent = CarControlAgent()
        self.nav_agent = NavAgent()
        self.cloud_agent = CloudScheduleAgent()

    def run(
        self,
        user_input: str,
        user_id: str = "user_001",
        network: NetworkStatus = NetworkStatus.ONLINE,
    ) -> ExecutionResult:
        command_type = self.intent_agent.recognize(user_input)
        safety = self.safety_agent.check(user_input)
        msg = Message.create(
            user_id=user_id,
            command_type=command_type,
            safety=safety,
            content=user_input,
            network=network,
        )

        if safety == SafetyLevel.DANGEROUS:
            return ExecutionResult(
                status=ExecutionStatus.BLOCKED,
                output="危险指令，已拦截！",
                message=msg,
            )

        if network == NetworkStatus.OFFLINE:
            output = self._run_local(command_type, user_input)
            return ExecutionResult(
                status=ExecutionStatus.FALLBACK,
                output=output,
                message=msg,
            )

        output = self.cloud_agent.dispatch(msg)
        return ExecutionResult(
            status=ExecutionStatus.EXECUTED,
            output=output,
            message=msg,
        )

    def _run_local(self, command_type: CommandType, user_input: str) -> str:
        if command_type == CommandType.CAR_CONTROL:
            return self.car_control_agent.execute(user_input)
        if command_type == CommandType.NAVIGATION:
            return self.nav_agent.start(user_input)
        if command_type == CommandType.CHARGE_PLAN:
            return "断网模式：根据本地知识库建议前往最近换电站"
        if command_type == CommandType.PERSONALIZE:
            return "断网模式：使用本地默认偏好，温度24℃"
        return "断网模式：当前指令无法本地执行"
```

- [ ] **Step 4: Run orchestration tests**

Run:

```bash
python -m unittest tests.test_vehicle_core_service -v
```

Expected: pass.

- [ ] **Step 5: Write entrypoint**

Create `main.py`:

```python
from core.constants import NetworkStatus
from core.vehicle_core_service import VehicleCoreService
from data.vehicle_state import DEFAULT_VEHICLE_STATE


def print_vehicle_state(network: NetworkStatus):
    print("======== 车辆状态面板 ========")
    print(f"车速：{DEFAULT_VEHICLE_STATE.speed_kmh} km/h")
    print(f"电量：{DEFAULT_VEHICLE_STATE.battery_percent} %")
    print(f"网络状态：{network.value}")
    print("安全状态：正常")
    print("==============================")


def print_result(result):
    print(f"请求ID：{result.message.request_id}")
    print(f"解析意图：{result.message.command_type.value}")
    print(f"安全等级：{result.message.safety.value}")
    print(f"网络状态：{result.message.network.value}")
    print(f"执行状态：{result.status.value}")
    print(f"最终结果：{result.output}")


def run_scenario(title: str, service: VehicleCoreService, user_input: str, network: NetworkStatus):
    print(f"\n==== {title} ====")
    print_vehicle_state(network)
    print(f"用户输入：{user_input}")
    result = service.run(user_input, network=network)
    print_result(result)


def main():
    service = VehicleCoreService()

    run_scenario("场景1：行程启动（端云协同）", service, "导航去蔚来中心", NetworkStatus.ONLINE)
    run_scenario("场景2：行驶途中（断网本地执行）", service, "打开座椅加热", NetworkStatus.OFFLINE)
    run_scenario("场景3：中途补给（充电规划）", service, "电量低", NetworkStatus.ONLINE)
    run_scenario("场景4：行程结束（数据闭环）", service, "我的偏好", NetworkStatus.ONLINE)
    run_scenario("安全测试：危险指令拦截", service, "加速到100km/h", NetworkStatus.ONLINE)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run all tests**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Run console demo**

Run:

```bash
python main.py
```

Expected: console shows four business scenarios and one dangerous-command interception scenario.

---

## Task 6: Documentation for Engineering and Interview

**Files:**

- Create: `docs/architecture.md`
- Create: `docs/engineering-notes.md`
- Create: `docs/interview-guide.md`
- Modify: `README.md`

- [ ] **Step 1: Create architecture document**

Create `docs/architecture.md`:

```markdown
# 系统架构说明

## 三层架构

- 车载执行层：负责本地意图识别、安全拦截、车控执行、离线导航。
- 端云通信层：通过统一 Message 协议描述请求，模拟端云报文。
- 云端决策层：负责用户画像、外部生态、路线规划和多 Agent 调度。

## 调用链

```text
用户输入
  -> LocalIntentAgent
  -> SafetyAgent
  -> VehicleCoreService
  -> ONLINE: CloudScheduleAgent
  -> OFFLINE: CarControlAgent / NavAgent
```

## 设计重点

安全校验优先于任何执行路径。云端只做增强决策，本地端保留基本执行能力。
```

- [ ] **Step 2: Create engineering notes**

Create `docs/engineering-notes.md`:

```markdown
# 工程思维记录

## 为什么先定义 Message

多 Agent 系统中，模块之间如果随意传递字符串，会很快失控。统一 Message 可以让车端、云端、日志、测试共享同一套协议。

## 为什么 SafetyAgent 前置

车载场景中，危险指令不能依赖云端判断，也不能进入执行链路。安全拦截必须在本地优先完成。

## 为什么第一版不用真实向量库

第一版重点是验证 RAG 在架构中的位置。使用字典和列表模拟检索，可以保持项目轻量、可复现，并保留后续替换向量库的接口边界。
```

- [ ] **Step 3: Create interview guide**

Create `docs/interview-guide.md`:

```markdown
# 面试讲解指南

## 项目一句话介绍

这是一个车载智能座舱端云协同 Multi-Agent 原型系统，支持本地意图识别、云端多 Agent 调度、RAG 知识增强、安全拦截和断网兜底。

## 简历描述

设计并实现车载端云协同 Multi-Agent 原型系统，拆分 SafetyAgent、LocalIntentAgent、CarControlAgent、NavAgent、CloudScheduleAgent 等 8 个模块；通过本地知识库模拟 RAG 意图识别、用户画像召回和路线规划；实现危险车控指令拦截、断网本地兜底、统一消息协议和核心单元测试。

## 高频问答

问：为什么没有直接接入大模型？

答：第一版定位是 offline 工程原型，重点验证端云协同、Agent 边界、安全拦截和 RAG 位置。模型和向量库可以作为后续替换项接入，不影响主流程。

问：这个项目和普通聊天机器人有什么区别？

答：普通聊天机器人主要关注回答文本，这个项目关注业务执行链路，包括意图识别、安全校验、车控执行、断网兜底和云端调度，更接近 AI 应用工程岗位的真实工作。
```

- [ ] **Step 4: Update README project structure**

Modify `README.md` to point to:

```markdown
## 快速开始

```bash
python main.py
python -m unittest discover -s tests -v
```

## 项目文档

- `docs/project-kickoff.md`：项目启动方案
- `docs/architecture.md`：系统架构说明
- `docs/engineering-notes.md`：工程思维记录
- `docs/interview-guide.md`：面试讲解指南
```

- [ ] **Step 5: Verify docs are readable**

Run:

```bash
python -m unittest discover -s tests -v
python main.py
```

Expected: tests pass and the console demo runs successfully.

---

## Self-Review

Spec coverage:

- 8 个 Agent: covered in Tasks 3 and 4.
- 端云协同: covered in Task 5.
- 本地 RAG 意图识别: covered in Tasks 2 and 3.
- 云端 RAG 路线规划: covered in Task 4.
- 安全拦截: covered in Tasks 3 and 5.
- 断网兜底: covered in Task 5.
- 数据闭环 and 面试材料: covered in Task 6.

Placeholder scan:

- No `TBD` markers.
- No empty implementation steps.
- No unnamed test expectations.

Type consistency:

- `CommandType`, `SafetyLevel`, `NetworkStatus`, and `ExecutionStatus` are defined once in `core/constants.py`.
- `Message.create(...)` is used consistently in tests and core service.
- `ExecutionResult.status` uses `ExecutionStatus` in tests and service.

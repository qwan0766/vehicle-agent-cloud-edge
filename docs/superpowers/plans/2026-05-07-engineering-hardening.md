# 工程硬化优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持现有端云协同演示可运行的前提下，补齐 `INFO_QUERY` 业务语义，拆清本地意图层与目的地解析层边界，并同步验收与面试文档。

**Architecture:** 保留现有公开门面：`LocalIntentAgent`、`resolve_destination`、`resolve_destination_detail`、`VehicleCoreService.run` 和 Web API payload 不做破坏性改名。内部新增小模块承载槽位抽取、意图规则、证据收集、目的地查询、澄清策略和候选对象，让大文件转为编排门面。

**Tech Stack:** Python 3.11、unittest / pytest、LangGraph 默认编排、高德 Provider、DeepSeek LLM Provider、原生 HTML/CSS/JS Web demo。

---

## 文件结构

本轮新增和调整的文件边界如下：

- Create: `agents/vehicle/intent/__init__.py`  
  导出意图子模块的稳定类型和服务类。
- Create: `agents/vehicle/intent/models.py`  
  存放 `IntentFrame`，避免 `LocalIntentAgent` 自己定义领域模型。
- Create: `agents/vehicle/intent/slot_extractor.py`  
  存放 `SlotExtractor`，只负责从完整输入中抽取结构化槽位。
- Create: `agents/vehicle/intent/evidence.py`  
  存放 `IntentEvidenceCollector` 和风险信号收集逻辑。
- Create: `agents/vehicle/intent/rule_engine.py`  
  存放 `IntentRuleEngine`，只负责确定性意图判断。
- Modify: `agents/vehicle/local_intent_agent.py`  
  保留公开门面、RAG 检索、本地 LLM fallback、本地上下文管理，把规则和槽位逻辑委托给子模块。
- Modify: `core/constants.py`  
  新增 `CommandType.INFO_QUERY`。
- Modify: `agents/vehicle/cabin_vehicle_control_agent.py`  
  为离线 `INFO_QUERY` 返回本地知识说明，不进入车控动作。
- Modify: `agents/orchestrator/global_dispatch_agent.py`  
  为在线 `INFO_QUERY` 提供非路线任务上下文。
- Modify: `web_demo/app_model.py`  
  `INFO_QUERY` 不生成路线摘要和补能站；澄清 payload 携带候选目的地。
- Modify: `web_demo/static/app.js`  
  澄清卡片展示候选目的地；`INFO_QUERY` 用正常结果展示。
- Modify: `web_demo/static/styles.css`  
  增加候选目的地卡片样式。
- Create: `providers/destination_models.py`  
  存放 `DestinationResolution`、`DestinationCandidate`、`DestinationClarification`。
- Create: `providers/destination_query.py`  
  存放目的地抽取、规范化和 GPS 判断。
- Create: `providers/destination_clarification_policy.py`  
  存放 `ClarificationPolicy` 与歧义原因。
- Create: `providers/destination_service.py`  
  存放 `DestinationResolver` 编排类。
- Modify: `providers/destination_resolver.py`  
  变成兼容门面，继续导出旧函数和异常。
- Modify: `providers/amap_geocode_provider.py`  
  将低置信度地理编码错误结构化，便于目的地层转成澄清状态。
- Modify: `core/clarification.py`  
  增加 `low_confidence_provider_result` 的问题文案、建议和候选 payload。
- Modify: `scripts/run_acceptance.py`  
  在线矩阵覆盖 `INFO_QUERY`、目的地澄清、低置信度候选契约。
- Modify: `reports/acceptance_report.md`  
  重新生成真实验收报告。
- Modify: `docs/acceptance-and-interview-review.md`  
  更新验收口径和面试讲法。
- Modify: `docs/agent-roles-and-workflows.md`  
  更新意图层、目的地层、`INFO_QUERY` 和澄清链路。
- Modify: `docs/architecture-diagram.md`  
  更新架构图中的业务状态和目的地解析边界。

## Task 0: 基线确认

**Files:**
- Read: `docs/superpowers/specs/2026-05-07-engineering-hardening-design.md`
- Read: `agents/vehicle/local_intent_agent.py`
- Read: `providers/destination_resolver.py`
- Read: `scripts/run_acceptance.py`

- [ ] **Step 1: 确认工作树干净**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## codex/destination-clarification-loop
```

`C:\Users\scyqw3/.config/git/ignore` 的权限警告可忽略，不影响仓库文件。

- [ ] **Step 2: 运行当前聚焦测试，建立行为基线**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_intent_agent.py tests/test_destination_resolver.py tests/test_clarification_loop.py tests/test_web_demo_app_model.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: all selected tests pass.

## Task 1: 补齐 INFO_QUERY 业务语义

**Files:**
- Modify: `core/constants.py`
- Modify: `agents/vehicle/local_intent_agent.py`
- Modify: `agents/vehicle/cabin_vehicle_control_agent.py`
- Modify: `agents/orchestrator/global_dispatch_agent.py`
- Modify: `web_demo/app_model.py`
- Test: `tests/test_intent_agent.py`
- Test: `tests/test_vehicle_core_service.py`
- Test: `tests/test_web_demo_app_model.py`

- [ ] **Step 1: 写失败测试，明确 INFO_QUERY 与危险车控的边界**

Append to `tests/test_intent_agent.py`:

```python
    def test_info_query_is_not_unknown(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("AEB是什么")

        self.assertEqual(frame.command_type, CommandType.INFO_QUERY)
        self.assertEqual(frame.slots["topic"], "AEB")
        self.assertIn("AEB", frame.evidence["keyword_hits"])
        self.assertEqual(agent.recognize("AEB是什么"), CommandType.INFO_QUERY)

    def test_safety_knowledge_question_is_info_query(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("讲一下制动距离")

        self.assertEqual(frame.command_type, CommandType.INFO_QUERY)
        self.assertEqual(frame.slots["topic"], "制动距离")
        self.assertEqual(frame.reason, "info_query_pattern")

    def test_actionable_aeb_command_remains_dangerous_car_control(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("关闭AEB")

        self.assertEqual(frame.command_type, CommandType.CAR_CONTROL)
        self.assertIn("actionable_dangerous_control", frame.risk_signals)
```

Update the import in `tests/test_vehicle_core_service.py`:

```python
from core.constants import CommandType, ExecutionStatus, NetworkStatus
```

Append inside `TestVehicleCoreService` in `tests/test_vehicle_core_service.py`:

```python
    def test_info_query_enters_online_execution_without_route_planning(self):
        service = VehicleCoreService(cloud_agent=FakeCloudAgent())

        result = service.run("AEB是什么", network=NetworkStatus.ONLINE)

        self.assertEqual(result.message.command_type, CommandType.INFO_QUERY)
        self.assertEqual(result.status, ExecutionStatus.EXECUTED)
```

Append to `tests/test_web_demo_app_model.py`:

```python
    def test_info_query_payload_is_normal_non_route_result(self):
        payload = run_command("AEB是什么", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "INFO_QUERY")
        self.assertEqual(payload["request"]["safety"], "SAFE")
        self.assertEqual(payload["result"]["status"], "EXECUTED")
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertNotIn("GlobalTripPlanningAgent", payload["agent_trace"])
        self.assertNotIn("trip.plan", [item["tool_name"] for item in payload["runtime_trace"]])
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_intent_agent.py tests/test_vehicle_core_service.py tests/test_web_demo_app_model.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: fails because `CommandType.INFO_QUERY` does not exist and `AEB是什么` is still `UNKNOWN`.

- [ ] **Step 3: 添加 `CommandType.INFO_QUERY`**

Edit `core/constants.py`:

```python
class CommandType(StrEnum):
    NAVIGATION = "NAVIGATION"
    CAR_CONTROL = "CAR_CONTROL"
    CHARGE_PLAN = "CHARGE_PLAN"
    PERSONALIZE = "PERSONALIZE"
    INFO_QUERY = "INFO_QUERY"
    UNKNOWN = "UNKNOWN"
```

- [ ] **Step 4: 在本地意图门面中实现最小 INFO_QUERY 行为**

In `agents/vehicle/local_intent_agent.py`, update the non-actionable question branch:

```python
        if _is_non_actionable_question(text) and not _is_charge_request(text):
            info_slots = _extract_info_query_slots(text)
            if info_slots:
                return self._frame(
                    CommandType.INFO_QUERY,
                    slots=info_slots,
                    confidence=0.82,
                    evidence=evidence,
                    risk_signals=risk_signals,
                    reason="info_query_pattern",
                )
            return self._frame(
                CommandType.UNKNOWN,
                confidence=0.35,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="non_actionable_question",
            )
```

Add helper near `_extract_car_control_slots`:

```python
def _extract_info_query_slots(content: str) -> Dict[str, object]:
    normalized = (content or "").replace(" ", "")
    topics = (
        "AEB",
        "自动紧急制动",
        "制动距离",
        "能耗",
        "续航",
        "换电",
        "充电",
        "电池",
        "胎压",
        "安全气囊",
    )
    for topic in topics:
        if topic.lower() in normalized.lower():
            return {"topic": topic}
    return {}
```

Update `_attach_local_llm_prompt` enum text:

```python
            "NAVIGATION、CAR_CONTROL、CHARGE_PLAN、PERSONALIZE、INFO_QUERY、UNKNOWN。"
```

- [ ] **Step 5: 让在线和离线链路认识 INFO_QUERY**

In `agents/vehicle/cabin_vehicle_control_agent.py`, add before the final return:

```python
        if command_type == CommandType.INFO_QUERY:
            return self._local_info_query_response(command, local_context)
```

Add method:

```python
    def _local_info_query_response(self, command: str, local_context) -> str:
        context = local_context or {}
        retrieved = context.get("retrieved_context") or []
        knowledge = "；".join(item.get("text", "") for item in retrieved[:2] if item.get("text"))
        if not knowledge:
            knowledge = "本地知识库暂无精确条目，建议联网后获取更完整解释。"
        return (
            "断网模式：这是信息查询，不会执行车辆控制动作。\n"
            f"- 用户问题：{command}\n"
            f"- 本地知识：{knowledge}"
        )
```

In `agents/orchestrator/global_dispatch_agent.py`, update `_non_route_context`:

```python
        if command_type == CommandType.INFO_QUERY:
            return "信息查询上下文：本次指令只需要解释车辆知识或功能含义，不调用地图路线规划，也不执行车控动作。"
```

In `web_demo/app_model.py`, include `CommandType.INFO_QUERY` in the cloud RAG branch:

```python
    if network == NetworkStatus.ONLINE and command_type in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
        CommandType.CAR_CONTROL,
        CommandType.PERSONALIZE,
        CommandType.INFO_QUERY,
    }:
```

- [ ] **Step 6: 运行 INFO_QUERY 聚焦测试**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_intent_agent.py tests/test_vehicle_core_service.py tests/test_web_demo_app_model.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: selected tests pass.

- [ ] **Step 7: Commit**

Run:

```powershell
git add core/constants.py agents/vehicle/local_intent_agent.py agents/vehicle/cabin_vehicle_control_agent.py agents/orchestrator/global_dispatch_agent.py web_demo/app_model.py tests/test_intent_agent.py tests/test_vehicle_core_service.py tests/test_web_demo_app_model.py
git commit -m "feat: add info query command semantics"
```

## Task 2: 拆分本地意图层模块

**Files:**
- Create: `agents/vehicle/intent/__init__.py`
- Create: `agents/vehicle/intent/models.py`
- Create: `agents/vehicle/intent/slot_extractor.py`
- Create: `agents/vehicle/intent/evidence.py`
- Create: `agents/vehicle/intent/rule_engine.py`
- Modify: `agents/vehicle/local_intent_agent.py`
- Test: `tests/test_intent_agent.py`
- Test: `tests/test_intent_modules.py`

- [ ] **Step 1: 写子模块测试**

Create `tests/test_intent_modules.py`:

```python
from agents.vehicle.intent.evidence import IntentEvidenceCollector
from agents.vehicle.intent.rule_engine import IntentRuleEngine
from agents.vehicle.intent.slot_extractor import SlotExtractor
from core.constants import CommandType
from rag.documents import INTENT_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


def test_slot_extractor_keeps_full_destination_query():
    slots = SlotExtractor().extract("导航去北京的蔚来中心")

    assert slots["navigation"]["raw_destination"] == "北京的蔚来中心"
    assert slots["navigation"]["destination_query"] == "北京蔚来中心"


def test_slot_extractor_extracts_info_query_topic():
    slots = SlotExtractor().extract("讲一下制动距离")

    assert slots["info_query"]["topic"] == "制动距离"


def test_rule_engine_prefers_info_query_over_unknown_question():
    retriever = SimpleRetriever(INTENT_DOCUMENTS)
    frame = IntentRuleEngine(retriever=retriever).analyze("AEB是什么")

    assert frame.command_type == CommandType.INFO_QUERY
    assert frame.reason == "info_query_pattern"


def test_rule_engine_keeps_dangerous_action_as_car_control():
    retriever = SimpleRetriever(INTENT_DOCUMENTS)
    frame = IntentRuleEngine(retriever=retriever).analyze("关闭AEB")

    assert frame.command_type == CommandType.CAR_CONTROL
    assert "actionable_dangerous_control" in frame.risk_signals


def test_evidence_collector_deduplicates_keywords():
    retriever = SimpleRetriever(INTENT_DOCUMENTS)
    evidence = IntentEvidenceCollector(retriever=retriever).collect("AEB是什么")

    assert evidence["keyword_hits"].count("AEB") == 1
    assert isinstance(evidence["retrieval"], list)
```

- [ ] **Step 2: 运行新测试确认失败**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_intent_modules.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: fails because `agents.vehicle.intent` package does not exist.

- [ ] **Step 3: 创建 `IntentFrame` 模型**

Create `agents/vehicle/intent/models.py`:

```python
from dataclasses import dataclass
from typing import Dict, List

from core.constants import CommandType


@dataclass(frozen=True)
class IntentFrame:
    command_type: CommandType
    slots: Dict[str, object]
    confidence: float
    evidence: Dict[str, object]
    risk_signals: List[str]
    reason: str
```

Create `agents/vehicle/intent/__init__.py`:

```python
from agents.vehicle.intent.models import IntentFrame
from agents.vehicle.intent.slot_extractor import SlotExtractor
from agents.vehicle.intent.evidence import IntentEvidenceCollector
from agents.vehicle.intent.rule_engine import IntentRuleEngine

__all__ = [
    "IntentFrame",
    "SlotExtractor",
    "IntentEvidenceCollector",
    "IntentRuleEngine",
]
```

- [ ] **Step 4: 创建槽位抽取模块**

Create `agents/vehicle/intent/slot_extractor.py`:

```python
import re
from typing import Dict

from providers.destination_resolver import extract_destination_query, normalize_destination_query


class SlotExtractor:
    def extract(self, content: str) -> Dict[str, Dict[str, object]]:
        text = content or ""
        return {
            "navigation": self.navigation_slots(text),
            "car_control": self.car_control_slots(text),
            "info_query": self.info_query_slots(text),
        }

    def navigation_slots(self, content: str) -> Dict[str, object]:
        destination_query = extract_destination_query(content)
        if not destination_query:
            return {}
        return {
            "raw_destination": destination_query,
            "destination_query": normalize_destination_query(destination_query),
        }

    def car_control_slots(self, content: str) -> Dict[str, object]:
        normalized = (content or "").replace(" ", "")
        slots: Dict[str, object] = {}

        temperature = re.search(r"(\d{1,2})\s*(?:度|℃)", content or "")
        if temperature and _contains_any(content, ["温度", "空调"]):
            slots["temperature_c"] = int(temperature.group(1))
            slots["target"] = "cabin_temperature"
            slots["action"] = "set"
            return slots

        if _contains_any(content, ["座椅加热"]):
            slots["target"] = "seat_heat"
            if _contains_any(content, ["打开", "开启", "启动"]):
                slots["action"] = "on"
                return slots
            if _contains_any(content, ["关闭", "关掉"]):
                slots["action"] = "off"
                return slots

        cabin_targets = ("空调", "车窗", "后备箱", "雨刷", "车灯", "座椅")
        action_words = ("打开", "开启", "关闭", "关掉", "调到", "调低", "调高")
        if any(target in normalized for target in cabin_targets) and any(
            action in normalized for action in action_words
        ):
            slots["target"] = "cabin_device"
            slots["action"] = "control"
            return slots
        return slots

    def info_query_slots(self, content: str) -> Dict[str, object]:
        normalized = (content or "").replace(" ", "")
        topics = (
            "AEB",
            "自动紧急制动",
            "制动距离",
            "能耗",
            "续航",
            "换电",
            "充电",
            "电池",
            "胎压",
            "安全气囊",
        )
        for topic in topics:
            if topic.lower() in normalized.lower():
                return {"topic": topic}
        return {}


def _contains_any(content: str, keywords) -> bool:
    normalized = (content or "").lower()
    return any(keyword.lower() in normalized for keyword in keywords)
```

- [ ] **Step 5: 创建证据收集模块**

Create `agents/vehicle/intent/evidence.py`:

```python
from typing import Dict, List

from data.knowledge_base import DANGEROUS_KEYWORDS
from rag.documents import INTENT_DOCUMENTS


class IntentEvidenceCollector:
    def __init__(self, retriever):
        self.retriever = retriever

    def collect(self, content: str) -> Dict[str, object]:
        keyword_hits = []
        for document in INTENT_DOCUMENTS:
            for keyword in document.keywords:
                if keyword and keyword.lower() in (content or "").lower():
                    keyword_hits.append(keyword)
        for keyword in DANGEROUS_KEYWORDS:
            if keyword and keyword.lower() in (content or "").lower():
                keyword_hits.append(keyword)
        keyword_hits = _dedupe(keyword_hits)
        retrieval = [
            {
                "doc_id": item.document.doc_id,
                "score": item.score,
                "command_type": item.document.metadata.get("command_type"),
                "matched_keywords": item.matched_keywords,
            }
            for item in self.retriever.search(content, top_k=3)
        ]
        return {"keyword_hits": keyword_hits, "retrieval": retrieval}

    def risk_signals(self, content: str) -> List[str]:
        signals = [
            keyword
            for keyword in DANGEROUS_KEYWORDS
            if keyword and keyword.lower() in (content or "").lower()
        ]
        if contains_actionable_dangerous_control(content):
            signals.append("actionable_dangerous_control")
        return _dedupe(signals)


def contains_actionable_dangerous_control(content: str) -> bool:
    normalized = (content or "").replace(" ", "").lower()
    actionable_patterns = (
        "加速到",
        "立即加速",
        "提升动力",
        "动力提升",
        "立即刹车",
        "执行刹车",
        "紧急制动",
        "执行制动",
        "立即制动",
        "关闭aeb",
        "禁用aeb",
        "关闭自动紧急制动",
        "禁用自动紧急制动",
        "接管方向盘",
        "自动转向",
        "执行转向",
        "帮我转向",
    )
    return any(pattern in normalized for pattern in actionable_patterns)


def contains_any(content: str, keywords) -> bool:
    normalized = (content or "").lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _dedupe(values):
    seen = set()
    return [
        value
        for value in values
        if not (value.lower() in seen or seen.add(value.lower()))
    ]
```

- [ ] **Step 6: 创建规则引擎模块**

Create `agents/vehicle/intent/rule_engine.py`:

```python
from core.constants import CommandType
from data.knowledge_base import INTENT_KNOWLEDGE
from agents.vehicle.intent.evidence import (
    IntentEvidenceCollector,
    contains_actionable_dangerous_control,
    contains_any,
)
from agents.vehicle.intent.models import IntentFrame
from agents.vehicle.intent.slot_extractor import SlotExtractor


class IntentRuleEngine:
    def __init__(self, retriever, slot_extractor=None, evidence_collector=None):
        self.retriever = retriever
        self.slot_extractor = slot_extractor or SlotExtractor()
        self.evidence_collector = evidence_collector or IntentEvidenceCollector(retriever)

    def analyze(self, user_input: str) -> IntentFrame:
        text = (user_input or "").strip()
        evidence = self.evidence_collector.collect(text)
        risk_signals = self.evidence_collector.risk_signals(text)
        slots = self.slot_extractor.extract(text)

        if not text:
            return _frame(CommandType.UNKNOWN, 0.0, evidence, risk_signals, "empty_input")

        for example, command_type in INTENT_KNOWLEDGE.items():
            if text == example:
                return _frame(command_type, 0.98, evidence, risk_signals, "exact_builtin_example")

        if is_negated_or_meta_request(text):
            return _frame(CommandType.UNKNOWN, 0.25, evidence, risk_signals, "negated_or_meta_request")

        if is_non_actionable_question(text) and not is_charge_request(text):
            if slots["info_query"]:
                return _frame(
                    CommandType.INFO_QUERY,
                    0.82,
                    evidence,
                    risk_signals,
                    "info_query_pattern",
                    slots["info_query"],
                )
            return _frame(CommandType.UNKNOWN, 0.35, evidence, risk_signals, "non_actionable_question")

        if slots["navigation"]:
            return _frame(
                CommandType.NAVIGATION,
                0.94,
                evidence,
                risk_signals,
                "navigation_slot_extracted",
                slots["navigation"],
            )

        if is_charge_request(text):
            return _frame(CommandType.CHARGE_PLAN, 0.9, evidence, risk_signals, "charge_request_pattern")

        if is_personalize_request(text):
            return _frame(CommandType.PERSONALIZE, 0.9, evidence, risk_signals, "personalize_request_pattern")

        if slots["car_control"]:
            return _frame(
                CommandType.CAR_CONTROL,
                0.88,
                evidence,
                risk_signals,
                "car_control_slot_extracted",
                slots["car_control"],
            )

        if contains_actionable_dangerous_control(text):
            return _frame(
                CommandType.CAR_CONTROL,
                0.86,
                evidence,
                risk_signals,
                "actionable_dangerous_control",
            )

        return _frame(CommandType.UNKNOWN, 0.2, evidence, risk_signals, "no_rule_match")


def _frame(command_type, confidence, evidence, risk_signals, reason, slots=None):
    return IntentFrame(
        command_type=command_type,
        slots=slots or {},
        confidence=confidence,
        evidence=evidence or {"keyword_hits": [], "retrieval": []},
        risk_signals=risk_signals or [],
        reason=reason,
    )


def is_non_actionable_question(content: str) -> bool:
    normalized = (content or "").replace(" ", "")
    question_markers = ("是什么", "什么意思", "介绍", "讲一下", "解释", "为什么", "如何", "怎么取消", "问问", "?", "？")
    return any(marker in normalized for marker in question_markers)


def is_negated_or_meta_request(content: str) -> bool:
    normalized = (content or "").replace(" ", "")
    negation_markers = ("不想", "不要", "不用", "别", "只是问", "问问怎么取消")
    return any(marker in normalized for marker in negation_markers)


def is_charge_request(content: str) -> bool:
    return contains_any(content, ["电量低", "补能", "充电", "换电", "续航不够"])


def is_personalize_request(content: str) -> bool:
    return contains_any(content, ["偏好", "用户画像", "个性化", "我的设置"])
```

- [ ] **Step 7: 改造 `LocalIntentAgent` 为门面**

In `agents/vehicle/local_intent_agent.py`:

- Remove local `IntentFrame` dataclass.
- Import:

```python
from agents.vehicle.intent.evidence import contains_actionable_dangerous_control
from agents.vehicle.intent.models import IntentFrame
from agents.vehicle.intent.rule_engine import IntentRuleEngine
```

- In `__init__`, after `self.retriever = SimpleRetriever(INTENT_DOCUMENTS)`, add:

```python
        self.rule_engine = IntentRuleEngine(retriever=self.retriever)
```

- Replace the deterministic body of `analyze` up to the retrieval fallback with:

```python
        frame = self.rule_engine.analyze(user_input)
        if frame.reason != "no_rule_match":
            return frame

        evidence = frame.evidence
        risk_signals = frame.risk_signals
```

- Update `_is_reliable_intent_match` references to use `contains_actionable_dangerous_control` only where needed. Keep `retrieve_context`, `build_local_llm_context`, `record_result`, `_recognize_with_llm`, `_attach_local_llm_prompt`, `_is_reliable_intent_match`, `_frame`, `window_value`, `_compact_prompt_preview`, `_safe_json`, `_estimate_tokens`.

- [ ] **Step 8: 运行意图层测试**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_intent_agent.py tests/test_intent_modules.py tests/test_llm_intent_fallback.py tests/test_local_llm_context_integration.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: selected tests pass.

- [ ] **Step 9: Commit**

Run:

```powershell
git add agents/vehicle/intent agents/vehicle/local_intent_agent.py tests/test_intent_modules.py tests/test_intent_agent.py
git commit -m "refactor: split local intent modules"
```

## Task 3: 拆分目的地解析层并结构化低置信度结果

**Files:**
- Create: `providers/destination_models.py`
- Create: `providers/destination_query.py`
- Create: `providers/destination_clarification_policy.py`
- Create: `providers/destination_service.py`
- Modify: `providers/destination_resolver.py`
- Modify: `providers/amap_geocode_provider.py`
- Modify: `core/clarification.py`
- Test: `tests/test_destination_resolver.py`
- Test: `tests/test_clarification_loop.py`

- [ ] **Step 1: 写目的地模型和低置信度测试**

Append to `tests/test_destination_resolver.py`:

```python
import pytest

from providers.destination_models import DestinationCandidate


class LowConfidenceGeocoder:
    provider_name = "fake_geocode"

    def geocode(self, address):
        from providers.amap_geocode_provider import LowConfidenceGeocodeError

        raise LowConfidenceGeocodeError(
            query=address,
            formatted_address="霓虹未来中心",
            gps="121.22,31.06",
            confidence=0.35,
            reason="missing_significant_terms:蔚来中心",
            provider_name=self.provider_name,
        )


def test_destination_candidate_payload_contract():
    candidate = DestinationCandidate(
        name="北京东方广场蔚来中心",
        gps="116.417,39.915",
        address="北京市东城区东方广场",
        source="amap_geocode",
        confidence=0.91,
        distance_km=12.3,
        reason="provider_candidate",
    )

    assert candidate.to_payload() == {
        "name": "北京东方广场蔚来中心",
        "gps": "116.417,39.915",
        "address": "北京市东城区东方广场",
        "source": "amap_geocode",
        "confidence": 0.91,
        "distance_km": 12.3,
        "reason": "provider_candidate",
    }


def test_low_confidence_geocode_requires_clarification():
    with pytest.raises(DestinationClarificationRequired) as context:
        resolve_destination_detail("导航去北京东方广场蔚来中心", geocoder=LowConfidenceGeocoder())

    assert context.value.reason == "low_confidence_provider_result"
    assert context.value.query == "北京东方广场蔚来中心"
    assert context.value.candidates[0]["name"] == "霓虹未来中心"
    assert context.value.candidates[0]["confidence"] == 0.35
```

Append to `tests/test_clarification_loop.py`:

```python
def test_build_destination_clarification_includes_low_confidence_candidates():
    from core.clarification import build_destination_clarification

    candidate = {
        "name": "霓虹未来中心",
        "gps": "121.22,31.06",
        "address": "上海市某结果",
        "source": "fake_geocode",
        "confidence": 0.35,
        "distance_km": None,
        "reason": "missing_significant_terms:蔚来中心",
    }
    exc = DestinationClarificationRequired(
        query="霓虹蔚来中心",
        reason="low_confidence_provider_result",
        candidates=[candidate],
    )

    payload = build_destination_clarification(exc, original_content="导航去霓虹蔚来中心")

    assert payload["reason"] == "low_confidence_provider_result"
    assert payload["candidates"] == [candidate]
    assert "置信度" in payload["question"]
```

- [ ] **Step 2: 运行目的地测试确认失败**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_destination_resolver.py tests/test_clarification_loop.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: fails because destination model modules and `LowConfidenceGeocodeError` do not exist.

- [ ] **Step 3: 创建目的地模型**

Create `providers/destination_models.py`:

```python
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class DestinationCandidate:
    name: str
    gps: str = ""
    address: str = ""
    source: str = ""
    confidence: float = 0.0
    distance_km: Optional[float] = None
    reason: str = ""

    def to_payload(self) -> dict:
        return {
            "name": self.name,
            "gps": self.gps,
            "address": self.address,
            "source": self.source,
            "confidence": self.confidence,
            "distance_km": self.distance_km,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DestinationResolution:
    name: str
    gps: str
    source: str
    confidence: float = 1.0
    candidates: Tuple[DestinationCandidate, ...] = ()


@dataclass(frozen=True)
class DestinationClarification:
    query: str
    reason: str
    suggestions: Tuple[str, ...] = ()
    candidates: Tuple[DestinationCandidate, ...] = ()
```

- [ ] **Step 4: 创建目的地查询模块**

Create `providers/destination_query.py`:

```python
import re


NAVIGATION_PREFIXES = (
    "帮我导航到",
    "帮我导航去",
    "导航到",
    "导航去",
    "我要去",
    "我想去",
    "开车去",
    "去",
    "到",
)


def extract_destination_query(content: str) -> str:
    text = re.sub(r"[，。！？!?.\s]+$", "", (content or "").strip())
    for prefix in NAVIGATION_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return ""


def normalize_destination_query(query: str) -> str:
    text = re.sub(r"\s+", "", (query or "").strip())
    text = re.sub(r"^(.{2,8}?)(?:的)(蔚来中心|换电站|充电站)$", r"\1\2", text)
    return text


def looks_like_gps(content: str) -> bool:
    if "," not in content:
        return False
    left, right = [part.strip() for part in content.split(",", 1)]
    try:
        float(left)
        float(right)
    except ValueError:
        return False
    return True
```

- [ ] **Step 5: 创建澄清策略模块**

Create `providers/destination_clarification_policy.py`:

```python
from providers.destination_models import DestinationClarification
from providers.destination_query import looks_like_gps, normalize_destination_query


class ClarificationPolicy:
    def assess(self, query: str, known_destinations=None):
        known_destinations = known_destinations or {}
        normalized = normalize_destination_query(query)
        if not normalized or looks_like_gps(normalized):
            return None
        if normalized in known_destinations:
            return None
        if _is_broad_region(normalized):
            return DestinationClarification(
                normalized,
                "broad_region",
                (
                    "请补充具体目的地，例如商圈、门店、机场、车站或完整地址。",
                    f"如果要去{normalized}的蔚来中心，可以说“导航去{normalized}蔚来中心”。",
                ),
            )
        chain_reason = _chain_poi_clarification_reason(normalized)
        if chain_reason:
            return DestinationClarification(
                normalized,
                chain_reason,
                (
                    "请补充城市或门店所在商圈，例如“上海松江印象城蔚来中心”。",
                    "连锁门店存在多个候选点，系统需要先确认唯一目的地。",
                ),
            )
        if _is_unclear_short_destination(normalized):
            return DestinationClarification(
                normalized,
                "unclear_destination",
                (
                    "请说得更具体一些，例如城市、区县、商圈或完整 POI 名称。",
                    "如果这是地名简称，请补充所在城市后再发起导航。",
                ),
            )
        return None


def _is_broad_region(query: str) -> bool:
    return query in _BROAD_REGION_NAMES


def _chain_poi_clarification_reason(query: str) -> str:
    for phrase in _CHAIN_POI_PHRASES:
        if query == phrase:
            return ""
        if query.endswith(phrase):
            qualifier = query[: -len(phrase)]
            if qualifier and not _contains_known_region_or_venue(qualifier):
                return "unknown_chain_poi_qualifier"
    return ""


def _is_unclear_short_destination(query: str) -> bool:
    if query in _KNOWN_SHORT_POIS:
        return False
    if _contains_known_region_or_venue(query):
        return False
    if any(marker in query for marker in _ADDRESS_CONFIDENCE_MARKERS):
        return False
    return len(query) <= 4


def _contains_known_region_or_venue(query: str) -> bool:
    return any(term in query for term in _KNOWN_REGIONS_AND_VENUES)


_BROAD_REGION_NAMES = {
    "北京",
    "北京市",
    "上海",
    "上海市",
    "杭州",
    "杭州市",
    "广州",
    "广州市",
    "深圳",
    "深圳市",
    "南京",
    "南京市",
    "苏州",
    "苏州市",
    "成都",
    "成都市",
    "重庆",
    "重庆市",
    "中国",
}

_CHAIN_POI_PHRASES = (
    "蔚来中心",
    "换电站",
    "充电站",
)

_KNOWN_SHORT_POIS = {
    "外滩",
    "陆家嘴",
    "静安寺",
    "东方明珠",
    "人民广场",
    "西湖",
}

_KNOWN_REGIONS_AND_VENUES = {
    "北京",
    "上海",
    "杭州",
    "广州",
    "深圳",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "松江",
    "东城",
    "朝阳",
    "望京",
    "黄浦",
    "浦东",
    "虹桥",
    "萧山",
    "西湖",
    "滨江",
    "印象城",
    "东方广场",
}

_ADDRESS_CONFIDENCE_MARKERS = (
    "机场",
    "车站",
    "火车站",
    "高铁站",
    "地铁站",
    "大厦",
    "广场",
    "商场",
    "医院",
    "学校",
    "公园",
    "酒店",
    "中心",
    "路",
    "街",
    "区",
    "园",
    "馆",
    "塔",
    "寺",
    "城",
)
```

- [ ] **Step 6: 结构化低置信度 geocode 错误**

In `providers/amap_geocode_provider.py`, add after `GeocodeQuality`:

```python
class LowConfidenceGeocodeError(RuntimeError):
    def __init__(
        self,
        query: str,
        formatted_address: str,
        gps: str,
        confidence: float,
        reason: str,
        provider_name: str,
    ):
        self.query = query
        self.formatted_address = formatted_address
        self.gps = gps
        self.confidence = confidence
        self.reason = reason
        self.provider_name = provider_name
        super().__init__(
            "AMap geocode low confidence: "
            f"query={query}, formatted_address={formatted_address}, "
            f"confidence={confidence:.2f}, reason={reason}"
        )
```

Replace the low-confidence branch in `AmapGeocodeProvider.geocode`:

```python
            raise LowConfidenceGeocodeError(
                query=address,
                formatted_address=formatted_address,
                gps=gps,
                confidence=quality.confidence,
                reason=quality.reason,
                provider_name=self.provider_name,
            )
```

- [ ] **Step 7: 创建 `DestinationResolver` 编排类**

Create `providers/destination_service.py`:

```python
from providers.amap_geocode_provider import LowConfidenceGeocodeError
from providers.destination_clarification_policy import ClarificationPolicy
from providers.destination_models import DestinationCandidate, DestinationResolution
from providers.destination_query import (
    extract_destination_query,
    looks_like_gps,
    normalize_destination_query,
)


class DestinationClarificationRequired(ValueError):
    def __init__(self, query: str, reason: str, suggestions=None, candidates=None):
        self.query = query
        self.reason = reason
        self.suggestions = list(suggestions or [])
        self.candidates = list(candidates or [])
        super().__init__(
            f"Destination clarification required: query={query}, reason={reason}"
        )


KNOWN_DESTINATIONS = {
    "导航去蔚来中心": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "蔚来中心": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "我要回家": DestinationResolution("家", "121.42,31.20", "builtin"),
    "回家": DestinationResolution("家", "121.42,31.20", "builtin"),
    "电量低": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "补能": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "充电规划": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "换电站": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "我的偏好": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "用户画像": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "个性化偏好": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
}


class DestinationResolver:
    def __init__(self, known_destinations=None, clarification_policy=None):
        self.known_destinations = known_destinations or KNOWN_DESTINATIONS
        self.clarification_policy = clarification_policy or ClarificationPolicy()

    def resolve(self, content: str, geocoder=None) -> DestinationResolution:
        normalized = (content or "").strip()
        if looks_like_gps(normalized):
            return DestinationResolution(normalized, normalized, "explicit_gps")

        query = extract_destination_query(normalized)
        if query:
            return self._resolve_query(query, geocoder=geocoder)

        for keyword, resolution in self.known_destinations.items():
            if keyword in normalized:
                return resolution
        raise ValueError(f"无法从指令中解析目的地：{content}")

    def _resolve_query(self, query: str, geocoder=None) -> DestinationResolution:
        normalized_query = normalize_destination_query(query)
        if looks_like_gps(normalized_query):
            return DestinationResolution(normalized_query, normalized_query, "explicit_gps")
        if normalized_query in self.known_destinations:
            return self.known_destinations[normalized_query]

        clarification = self.clarification_policy.assess(
            normalized_query,
            known_destinations=self.known_destinations,
        )
        if clarification:
            raise DestinationClarificationRequired(
                clarification.query,
                clarification.reason,
                suggestions=clarification.suggestions,
                candidates=[item.to_payload() for item in clarification.candidates],
            )

        if geocoder is None:
            raise ValueError(f"未知目的地且未配置在线地理编码：{normalized_query}")

        try:
            geocode_result = geocoder.geocode(normalized_query)
        except LowConfidenceGeocodeError as exc:
            candidate = DestinationCandidate(
                name=exc.formatted_address,
                gps=exc.gps,
                address=exc.formatted_address,
                source=exc.provider_name,
                confidence=exc.confidence,
                reason=exc.reason,
            )
            raise DestinationClarificationRequired(
                normalized_query,
                "low_confidence_provider_result",
                suggestions=("请确认是否选择该候选地点，或补充城市、商圈、完整门店名称。",),
                candidates=[candidate.to_payload()],
            ) from exc

        return DestinationResolution(
            name=geocode_result.name or normalized_query,
            gps=geocode_result.gps,
            source=geocoder.provider_name,
            confidence=getattr(geocode_result, "confidence", 1.0),
        )
```

- [ ] **Step 8: 将 `destination_resolver.py` 改为兼容门面**

Replace `providers/destination_resolver.py` with:

```python
from providers.destination_models import DestinationCandidate, DestinationClarification, DestinationResolution
from providers.destination_query import (
    NAVIGATION_PREFIXES,
    extract_destination_query,
    looks_like_gps,
    normalize_destination_query,
)
from providers.destination_clarification_policy import ClarificationPolicy
from providers.destination_service import (
    DestinationClarificationRequired,
    DestinationResolver,
    KNOWN_DESTINATIONS,
)


def resolve_destination(content: str, geocoder=None) -> str:
    return resolve_destination_detail(content, geocoder=geocoder).gps


def resolve_destination_detail(content: str, geocoder=None) -> DestinationResolution:
    return DestinationResolver().resolve(content, geocoder=geocoder)


def assess_destination_clarification(query: str):
    clarification = ClarificationPolicy().assess(
        query,
        known_destinations=KNOWN_DESTINATIONS,
    )
    if not clarification:
        return None
    return DestinationClarificationRequired(
        clarification.query,
        clarification.reason,
        suggestions=clarification.suggestions,
        candidates=[item.to_payload() for item in clarification.candidates],
    )


__all__ = [
    "DestinationCandidate",
    "DestinationClarification",
    "DestinationResolution",
    "DestinationClarificationRequired",
    "DestinationResolver",
    "KNOWN_DESTINATIONS",
    "NAVIGATION_PREFIXES",
    "resolve_destination",
    "resolve_destination_detail",
    "extract_destination_query",
    "normalize_destination_query",
    "assess_destination_clarification",
    "looks_like_gps",
]
```

- [ ] **Step 9: 更新澄清文案**

In `core/clarification.py`, add:

```python
    "low_confidence_provider_result": [
        "候选地点置信度较低，请确认是否选择该地点。",
        "也可以补充城市、商圈、完整门店名称或完整地址。",
    ],
```

and:

```python
    "low_confidence_provider_result": "地图返回了低置信度候选地点。为了避免导航到错误位置，请先确认目的地。",
```

- [ ] **Step 10: 运行目的地聚焦测试**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_destination_resolver.py tests/test_clarification_loop.py tests/test_amap_geocode_provider.py tests/test_web_error_response.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: selected tests pass.

- [ ] **Step 11: Commit**

Run:

```powershell
git add providers/destination_models.py providers/destination_query.py providers/destination_clarification_policy.py providers/destination_service.py providers/destination_resolver.py providers/amap_geocode_provider.py core/clarification.py tests/test_destination_resolver.py tests/test_clarification_loop.py
git commit -m "refactor: split destination resolution policy"
```

## Task 4: Web 展示候选目的地和 INFO_QUERY

**Files:**
- Modify: `web_demo/app_model.py`
- Modify: `web_demo/static/app.js`
- Modify: `web_demo/static/styles.css`
- Test: `tests/test_web_demo_app_model.py`
- Test: `tests/test_web_demo_frontend_logic.py`
- Test: `tests/test_web_demo_markup.py`

- [ ] **Step 1: 写 Web payload 测试**

Append to `tests/test_web_demo_app_model.py`:

```python
    def test_clarification_payload_can_carry_destination_candidates(self):
        from core.clarification import build_destination_clarification
        from providers.destination_resolver import DestinationClarificationRequired

        candidate = {
            "name": "低置信度候选点",
            "gps": "121.22,31.06",
            "address": "地图返回地址",
            "source": "fake_geocode",
            "confidence": 0.35,
            "distance_km": None,
            "reason": "low_character_coverage",
        }
        payload = build_destination_clarification(
            DestinationClarificationRequired(
                query="霓虹蔚来中心",
                reason="low_confidence_provider_result",
                candidates=[candidate],
            ),
            original_content="导航去霓虹蔚来中心",
        )

        self.assertEqual(payload["candidates"], [candidate])
```

Append to `tests/test_web_demo_frontend_logic.py`:

```python
def test_frontend_has_candidate_rendering_hook():
    source = Path("web_demo/static/app.js").read_text(encoding="utf-8")

    assert "clarification-candidates" in source
    assert "candidate.confidence" in source
```

- [ ] **Step 2: 运行 Web 测试确认失败**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_web_demo_app_model.py tests/test_web_demo_frontend_logic.py tests/test_web_demo_markup.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: frontend hook test fails until `app.js` renders candidates.

- [ ] **Step 3: 渲染候选目的地**

In `web_demo/static/app.js`, update `renderClarification`:

```javascript
  const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
```

After suggestions rendering, add:

```javascript
  if (candidates.length) {
    const candidateBox = document.createElement("div");
    candidateBox.className = "clarification-candidates";
    candidates.forEach((candidate) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "clarification-candidate";
      const confidence =
        typeof candidate.confidence === "number"
          ? `${Math.round(candidate.confidence * 100)}%`
          : "未知";
      item.innerHTML =
        `<strong>${escapeHtml(candidate.name || "候选地点")}</strong>` +
        `<span>${escapeHtml(candidate.address || candidate.gps || "无地址")}</span>` +
        `<small>置信度 ${escapeHtml(confidence)} · ${escapeHtml(candidate.source || "provider")}</small>`;
      item.addEventListener("click", () => {
        nodes.commandInput.value = candidate.name || payload.query || "";
        nodes.commandInput.focus();
      });
      candidateBox.appendChild(item);
    });
    card.appendChild(candidateBox);
  }
```

- [ ] **Step 4: 增加候选卡片样式**

In `web_demo/static/styles.css`, add:

```css
.clarification-candidates {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.clarification-candidate {
  align-items: flex-start;
  background: #f8fbfa;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  display: grid;
  gap: 4px;
  justify-items: start;
  min-height: 72px;
  padding: 12px;
  text-align: left;
  white-space: normal;
}

.clarification-candidate strong,
.clarification-candidate span,
.clarification-candidate small {
  overflow-wrap: anywhere;
}
```

- [ ] **Step 5: 运行 Web 聚焦测试**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_web_demo_app_model.py tests/test_web_demo_frontend_logic.py tests/test_web_demo_markup.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: selected tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add web_demo/app_model.py web_demo/static/app.js web_demo/static/styles.css tests/test_web_demo_app_model.py tests/test_web_demo_frontend_logic.py tests/test_web_demo_markup.py
git commit -m "feat: render clarification destination candidates"
```

## Task 5: 更新验收矩阵和面试文档

**Files:**
- Modify: `scripts/run_acceptance.py`
- Modify: `reports/acceptance_report.md`
- Modify: `docs/acceptance-and-interview-review.md`
- Modify: `docs/agent-roles-and-workflows.md`
- Modify: `docs/architecture-diagram.md`
- Test: `tests/test_acceptance_runner.py`

- [ ] **Step 1: 写验收脚本测试**

Append to `tests/test_acceptance_runner.py`:

```python
def test_online_cases_include_info_query_and_clarification():
    from scripts.run_acceptance import ONLINE_CASES

    contents = [case.content for case in ONLINE_CASES]

    assert "AEB是什么" in contents
    assert "导航去北京" in contents


def test_report_mentions_engineering_hardening_scenarios():
    from scripts.run_acceptance import AcceptanceStepResult, PASS, render_markdown_report

    report = render_markdown_report(
        [
            AcceptanceStepResult(
                "online matrix",
                PASS,
                '[{"content": "AEB是什么"}, {"content": "导航去北京"}]',
                0.1,
            )
        ],
        generated_at="2026-05-07T10:00:00+08:00",
    )

    assert "INFO_QUERY" in report
    assert "NEEDS_CLARIFICATION" in report
```

- [ ] **Step 2: 更新在线矩阵**

In `scripts/run_acceptance.py`, extend `ONLINE_CASES` with:

```python
    OnlineCaseExpectation(
        content="AEB是什么",
        expected_command_type="INFO_QUERY",
        expected_safety="SAFE",
        expected_status="EXECUTED",
        forbidden_trace_tools=("trip.plan", "provider.map.route"),
    ),
    OnlineCaseExpectation(
        content="导航去北京",
        expected_command_type="NAVIGATION",
        expected_safety="SAFE",
        expected_status="NEEDS_CLARIFICATION",
        forbidden_trace_tools=("trip.plan", "provider.map.route"),
    ),
```

Update `validate_online_case` to treat `NEEDS_CLARIFICATION` as a normal status by checking:

```python
    if expectation.expected_status == "NEEDS_CLARIFICATION":
        clarification = result_payload.get("clarification") or {}
        checks["clarification query"] = bool(clarification.get("query"))
        checks["clarification question"] = bool(clarification.get("question"))
```

Update `render_markdown_report` after the summary table:

```python
    lines.extend(
        [
            "",
            "## 本轮工程硬化覆盖",
            "",
            "- `INFO_QUERY`：安全知识问答从 `UNKNOWN` 中拆出，作为正常业务意图。",
            "- `NEEDS_CLARIFICATION`：模糊目的地是正常澄清状态，不作为外部接口错误。",
            "- 目的地候选契约：低置信度地图结果可携带候选地点给前端确认。",
            "- 数据闭环：澄清态不更新用户偏好，避免把不完整输入写成长期偏好。",
        ]
    )
```

- [ ] **Step 3: 运行验收脚本测试**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_acceptance_runner.py --basetemp=$basetemp -p no:cacheprovider
```

Expected: selected tests pass.

- [ ] **Step 4: 更新中文文档**

Edit `docs/agent-roles-and-workflows.md`:

- Add a section titled `## 4.1 业务状态建模` after online workflow.
- Include:

```markdown
| 状态 / 意图 | 语义 | 是否错误 |
| --- | --- | --- |
| `INFO_QUERY` | 解释车辆知识、功能含义或安全概念 | 否 |
| `NEEDS_CLARIFICATION` | 当前输入不足以唯一确定目的地，需要用户补充 | 否 |
| `UNKNOWN` | 系统无法识别可服务的业务意图 | 是，策略阻断 |
| `BLOCKED` | 安全策略拒绝执行 | 是，安全阻断 |
```

Edit `docs/acceptance-and-interview-review.md`:

- Add a section titled `## 工程硬化后的面试讲法`.
- Include:

```markdown
这轮优化的重点不是再接一个 API，而是补齐工程语义边界：`INFO_QUERY` 让安全知识问答从未知指令中拆出来；`NEEDS_CLARIFICATION` 让模糊目的地成为正常对话状态；目的地候选契约让低置信度地图结果不能直接启动导航。这些变化体现的是业务状态建模、模块边界和安全优先的工程思维。
```

Edit `docs/architecture-diagram.md`:

- Add a Mermaid node for `DestinationResolver`.
- Show `LocalIntentAgent -> DestinationResolver -> NEEDS_CLARIFICATION / CloudTripPlanning` split.

- [ ] **Step 5: 重新生成验收报告**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/run_acceptance.py --skip-provider-smoke --skip-online-matrix
```

Expected:

```text
acceptance report written: E:\claudeCode\weilaiAgent\reports\acceptance_report.md
```

The report should include the new `本轮工程硬化覆盖` section. Full provider smoke and online matrix run happens in Task 6.

- [ ] **Step 6: Commit**

Run:

```powershell
git add scripts/run_acceptance.py reports/acceptance_report.md docs/acceptance-and-interview-review.md docs/agent-roles-and-workflows.md docs/architecture-diagram.md tests/test_acceptance_runner.py
git commit -m "docs: update acceptance for engineering hardening"
```

## Task 6: 全量验证和最终整理

**Files:**
- Verify: all changed files
- Update if generated: `reports/acceptance_report.md`

- [ ] **Step 1: 运行全量单元测试**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests --basetemp=$basetemp -p no:cacheprovider
```

Expected: all tests pass. Existing LangGraph `allowed_objects` warning may appear once and is acceptable.

- [ ] **Step 2: 运行完整验收**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/run_acceptance.py
```

Expected:

```text
acceptance report written: E:\claudeCode\weilaiAgent\reports\acceptance_report.md
```

If real provider network fails, rerun with skipped online checks to keep local acceptance available:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/run_acceptance.py --skip-provider-smoke --skip-online-matrix
```

Record in the final summary whether full provider acceptance passed or the skipped local acceptance was used.

- [ ] **Step 3: Smoke test Web model without browser**

Run:

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -c "from web_demo.app_model import run_command; print(run_command('AEB是什么')['request']['command_type']); print(run_command('导航去北京')['result']['status'])"
```

Expected:

```text
INFO_QUERY
NEEDS_CLARIFICATION
```

- [ ] **Step 4: 检查工作树**

Run:

```powershell
git status --short
```

Expected: only intended generated report or docs are modified. If `reports/acceptance_report.md` changed in Step 2, include it in the final commit.

- [ ] **Step 5: Final commit for verification artifacts**

Run:

```powershell
git add reports/acceptance_report.md
git commit -m "test: refresh acceptance report"
```

If `reports/acceptance_report.md` did not change, skip this commit.

- [ ] **Step 6: Final summary**

The final response must include:

- New business behavior: `INFO_QUERY`, destination clarification, low-confidence candidate.
- Refactoring summary: intent submodules and destination submodules.
- Verification evidence: exact test command result and acceptance command result.
- Demo URL only if the server is started in this execution session.

# 工程硬化优化设计

**目标：** 在不破坏当前可运行演示的前提下，优先补足项目中最明显的工程短板：模块边界、业务状态建模、目的地歧义处理、验收资产同步。

**核心结果：** 项目不仅能跑，还要更容易维护、更容易扩展，也更适合面试讲解。下一轮实现重点不是堆新功能，而是把已经开始变重的意图识别、目的地解析、状态语义和验收链路整理清楚。

## 当前上下文

当前分支是 `codex/destination-clarification-loop`。上一轮已经完成：

- 新增 `ExecutionStatus.NEEDS_CLARIFICATION`
- 支持目的地澄清状态
- 支持 pending clarification 两轮补充
- Web 前端展示澄清卡片
- 澄清态不调用地图路线规划
- 澄清态不更新用户偏好
- 全量测试通过：`171 passed, 1 warning`

目前剩余最明显的工程问题集中在几个文件：

- `agents/vehicle/local_intent_agent.py` 同时承担意图框架、规则匹配、槽位抽取、风险信号、LLM fallback、本地上下文拼装和结果记录，职责偏重。
- `providers/destination_resolver.py` 同时承担目的地抽取、规范化、内置目的地匹配、澄清策略和 geocoder handoff，职责边界不清。
- `web_demo/static/app.js` 和 `web_demo/static/styles.css` 较大，但前端拆分不是第一优先级，除非候选列表交互需要改动。
- 验收报告和面试文档还没有完全同步新的测试基线与澄清场景。

## 本轮范围

本轮定位是 **工程优化优先**，不是大而全的功能扩张。优化分成四个工程包。

## 工程包 1：意图层边界整理

保留 `LocalIntentAgent` 作为公开门面，避免破坏现有调用方和测试。

内部拆出更清晰的小模块：

- `IntentFrame`：稳定的意图分析结果，包含 command type、slots、confidence、evidence、risk signals、reason。
- `SlotExtractor`：负责抽取结构化槽位，例如导航目的地、座舱温度、座椅加热动作、信息查询主题。
- `IntentRuleEngine`：负责确定性规则判断，包括导航、车控、补能、个性化、信息查询、未知指令。
- `IntentEvidenceCollector`：可选，用于收集命中关键词、否定表达、风险信号等解释信息。

目标调用链：

```text
用户输入
-> SlotExtractor
-> IntentRuleEngine
-> 可选本地 LLM fallback
-> IntentFrame
```

`LocalIntentAgent` 保留以下公开能力：

- `recognize` 返回 `CommandType`
- `analyze` 返回 `IntentFrame`
- `retrieve_context` 保持当前 RAG 风格上下文召回契约
- `build_local_llm_context` 保持当前本地上下文包契约
- `record_result` 保持当前本地记忆更新契约

目标不是一次性删除所有历史逻辑，而是让 `LocalIntentAgent` 从 480 行以上的混合逻辑文件，逐步变成更薄的编排门面。

## 工程包 2：目的地层边界整理

保留 `resolve_destination` 和 `resolve_destination_detail` 作为兼容函数。

内部拆出目的地领域模型：

- `DestinationResolution`：已确认、可执行的唯一目的地。
- `DestinationCandidate`：候选目的地，包含名称、地址、坐标、来源、置信度、距离和原因。
- `DestinationClarification`：结构化澄清对象，用于产生 `NEEDS_CLARIFICATION`。
- `DestinationQuery`：抽取并规范化后的目的地查询。
- `ClarificationPolicy`：确定性歧义判断策略。
- `DestinationResolver`：统一编排内置目的地、澄清策略、geocoder 和候选验证。

目的地层应明确区分四种情况：

- 已确认唯一目的地，可以执行。
- Provider 调用前就需要澄清。
- Provider 返回了低置信度结果，需要澄清。
- Provider 不可用或调用失败，需要作为真实错误暴露。

本轮要先建立候选对象契约，不要求一次性完成完整 POI 选择 UI。

示例行为：

- `导航去北京` -> `NEEDS_CLARIFICATION`，reason 为 `broad_region`
- `导航去霓虹蔚来中心` -> `NEEDS_CLARIFICATION`，reason 为 `unknown_chain_poi_qualifier`
- `导航去121.48,31.23` -> 明确 GPS，可执行
- `导航去北京东方广场蔚来中心` -> 如果 provider 成功，则进入在线路线规划

## 工程包 3：业务状态语义补齐

新增 `CommandType.INFO_QUERY`。

目的：把信息查询从 `UNKNOWN` 中分离出来，避免把“安全知识问答”和“无法识别的指令”混为一类。

示例：

- `AEB是什么` -> `INFO_QUERY`，`SAFE`
- `讲一下制动距离` -> `INFO_QUERY`，`SAFE`
- `关闭AEB` -> `CAR_CONTROL`，`DANGEROUS`，`BLOCKED`
- `立即刹车` -> `CAR_CONTROL`，`DANGEROUS`，`BLOCKED`

处理原则：

- `INFO_QUERY` 不调用车控执行链路。
- 在线模式下可以走 RAG / LLM 解释。
- 离线模式可以返回本地知识解释或本地 fallback。
- 它是正常 command type，不再使用 `UNKNOWN` 表示。

不新增第二个澄清状态。已有 `ExecutionStatus.NEEDS_CLARIFICATION` 足够表达“需要用户补充信息”，比再加一个并行的 `CLARIFICATION` 更清晰。

## 工程包 4：验收与面试资产同步

代码稳定后更新验收资产。

验收报告应包含：

- 当前真实单测数量
- 目的地澄清场景
- `INFO_QUERY` 场景
- Provider 置信度与低置信度行为
- 前端澄清卡片渲染
- 数据闭环规则：澄清态不更新用户偏好

需要更新或新增的文档：

- `reports/acceptance_report.md`
- `docs/acceptance-and-interview-review.md`
- `docs/agent-roles-and-workflows.md`
- `docs/architecture-diagram.md`
- 工程说明文档：解释为什么要补状态建模与模块边界

## 非目标

本轮不做以下内容：

- 不重写整个前端架构。
- 不引入完整生产级对话管理器。
- 不加入 Milvus、MQTT、Docker 或真实本地小模型部署。
- 不强制每个 Agent 都调用 LLM。
- 不一次性完成完整地图 POI 候选选择 UI。
- 不删除现有测试和演示依赖的公开 API。

## 测试策略

所有行为变化继续使用 TDD。

重点测试：

- `test_intent_agent.py`：覆盖 `INFO_QUERY`、否定表达、元问题、危险车控区分。
- 新增或更新意图模块测试：覆盖 `SlotExtractor` 与 `IntentRuleEngine`。
- `test_destination_resolver.py`：覆盖 query extraction、normalization、clarification policy、candidate object。
- `test_clarification_loop.py`：确保已有澄清与 follow-up 行为不回退。
- `test_input_matrix.py`：扩展服务级输入矩阵，覆盖信息查询、澄清、GPS、车控、补能、安全。
- `test_web_demo_app_model.py`：覆盖 `INFO_QUERY` 与澄清态 Web payload。
- `test_acceptance_runner.py`：验收报告包含新基线和新场景。

全量验证命令：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests --basetemp=$basetemp -p no:cacheprovider
```

预期：所有测试通过。已有 LangGraph `allowed_objects` warning 可以接受，但不应出现新的 warning。

## 推荐实现顺序

1. 先添加 `INFO_QUERY` 的测试与语义，保持现有 Agent 门面不变。
2. 在 `LocalIntentAgent` 背后拆出槽位抽取与确定性意图规则。
3. 在目的地解析层背后拆出 destination models 与 clarification policy。
4. 增加候选目的地数据结构测试，并提供最小 backend candidate contract。
5. 仅在新状态或候选契约需要时修改 Web/app model。
6. 最后更新验收脚本、验收报告和面试文档。

## 成功标准

- 现有 demo 场景仍然可运行。
- `AEB是什么` 不再是 `UNKNOWN`，而是 `INFO_QUERY`。
- 危险车控指令仍然在云端调度前被拦截。
- 模糊目的地仍然返回 `NEEDS_CLARIFICATION`。
- `LocalIntentAgent` 和 `destination_resolver.py` 从混合逻辑文件变成门面层。
- 候选目的地相关结构存在并有测试，即使完整 POI UI 作为后续增强。
- 验收报告反映本轮后的真实测试基线。
- 全量测试通过。

## 面试讲法

这轮优化可以这样讲：

> 我没有继续堆 if-else 规则，而是把“指令语义”和“执行状态”分开，把“意图识别”“槽位抽取”“澄清策略”“目的地候选”拆成独立边界。这样系统更容易测试，也更符合车载场景：危险车控必须前置拦截，模糊导航是正常对话状态，而不是 API 错误。

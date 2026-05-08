# 当前交付快照：车载 Multi-Agent 端云协同系统

更新时间：2026-05-08

## 一句话介绍

这是一个面向智能座舱/车载 AI 应用工程岗位的 Multi-Agent 端云协同演示项目。项目从最初的离线 demo，扩展为包含本地意图 Agent、云端 LangGraph 编排、DeepSeek LLM、真实地图/POI Provider、目的地澄清、车辆状态服务、主动状态事件流、安全拦截和数据闭环的可运行系统。

## 当前可演示能力

1. **端云协同链路**
   - 车端先完成本地意图识别、安全校验、车辆状态读取。
   - 在线模式进入云端多 Agent 编排。
   - 离线模式保留本地兜底，不依赖外部服务。

2. **八类 Agent 分工**
   - 本地意图 Agent：识别 NAVIGATION / CAR_CONTROL / CHARGE_PLAN / PERSONALIZE / INFO_QUERY / UNKNOWN。
   - 全局安全调度 Agent：前置拦截危险车控，并结合车辆上下文判断速度类请求。
   - 座舱控制 Agent：处理座椅加热、温度等本地车控。
   - 车辆状态监控 Agent：主动检测低电量等状态事件。
   - 云端全局调度 Agent：默认启用 LangGraph 编排。
   - 用户画像 Agent：召回用户偏好。
   - 外部生态 Agent：组合天气、充电站等外部信息。
   - 路线规划 Agent：结合地图 Provider、RAG 和 LLM 生成路线说明。

3. **真实 Provider 接入**
   - DeepSeek 用于云端决策说明，也可模拟车端小参数 LLM。
   - 高德地图用于地理编码、驾车路线和 POI 候选。
   - Open-Meteo / OpenChargeMap 保留可扩展接口，当前按环境配置选择真实或离线 Provider。

4. **目的地置信度与澄清**
   - 不再只靠关键词截断用户输入。
   - 对模糊地点、低置信度地点、候选 POI 进行确认。
   - 常用高频地点可以允许模糊执行，普通地点需要用户确认。
   - 前端支持候选地点卡片，用户可点击确认后继续导航。

5. **车辆状态服务**
   - 车辆状态不再只是写死常量，而是由 `VehicleStateService` 维护。
   - 前端可以调整道路类型、限速、车速、电量、辅助驾驶模式。
   - 同一句指令会因状态不同产生不同结果：
     - 高速 + 限速 120：`加速到100km/h` 进入 `NEEDS_DRIVER_CONFIRMATION`。
     - 城市 + 限速 60：`加速到100km/h` 进入 `BLOCKED`。

6. **主动状态事件流**
   - 低电量不再依赖用户输入才出现。
   - 新增 `VehicleEventService` 和 `GET /api/vehicle-events`。
   - 前端每 3 秒轮询车辆状态事件。
   - `battery <= 20%` 触发 `BATTERY_LOW / WARNING`。
   - `battery <= 10%` 触发 `BATTERY_CRITICAL / CRITICAL`。
   - 轮询只刷新仪表展示和事件栏，不覆盖用户正在编辑的输入框。

7. **前端可视化演示**
   - 车辆状态面板：速度、电量、GPS、道路、限速、辅助模式。
   - 指令执行面板：用户画像、场景按钮、自定义输入。
   - Agent 调用链：展示端云协同、LangGraph 路径、安全拦截或澄清链路。
   - RAG 召回知识：展示本地/云端召回内容。
   - 数据闭环：记录使用事件和偏好更新。
   - Provider 状态：展示 LLM、地图、天气、充电站来源。
   - 路线与补能：展示路线距离、时间、充电站结果。

## 面试讲述重点

### 1. 为什么不是单 Agent

车载场景天然有安全边界、状态感知、端云切换和外部工具调用。单 Agent 很容易把“识别意图、查地图、控车、安全拦截、生成说明”混在一起。这个项目把职责拆开，方便做安全前置、工具隔离、状态驱动和可观测调试。

### 2. 为什么要有车辆状态服务

真实车载 AI 不是只处理一句自然语言，还要读取车辆状态。比如同样是“加速到100km/h”，在高速限速 120 时可以提示驾驶员确认巡航目标，在城市限速 60 时必须拦截。这个差异来自状态上下文，而不是来自用户输入本身。

### 3. 为什么低电量是事件流

低电量、胎压异常、传感器降级这类信息不应该等用户提问才出现。项目中把它设计为主动状态事件流：状态监控 Agent 周期检测，事件服务标准化输出，前端常驻展示，用户命令链路再读取这些事件影响决策。

### 4. 为什么目的地需要澄清

导航场景不能只要地图返回一个点就执行。对于“北京”“世博园”“霓虹蔚来中心”这类模糊或低置信度输入，需要进入澄清状态或候选确认状态，避免把用户带到错误地点。这体现了业务状态建模，而不只是 API 调用。

### 5. LangGraph 在项目中的价值

LangGraph 用于云端多 Agent 编排，把用户画像、知识召回、路线偏好、外部生态、路线规划和最终决策组织成可观测路径。面试时可以强调：LangGraph 不是为了炫技，而是为了让 Agent 调度具备状态流、节点边界和可追踪性。

## 当前关键接口

- `GET /api/state`：页面初始化状态。
- `POST /api/run`：执行用户指令。
- `POST /api/vehicle-state`：更新车辆状态。
- `GET /api/vehicle-events`：主动车辆事件流。
- `POST /api/provider-smoke`：检测外部 Provider。
- `GET /api/acceptance`：读取验收报告摘要。

## 当前测试基线

最近一次全量测试：

```text
216 passed
```

测试覆盖范围包括：

- 意图识别与槽位抽取。
- 安全策略与危险指令拦截。
- 目的地置信度与澄清。
- 高德地图/POI Provider。
- LangGraph 编排。
- 本地 LLM 上下文管理。
- 车辆状态服务与主动事件流。
- Web 前端逻辑。
- 验收脚本与离线评测。

## 当前可继续深化的方向

1. **EnergyPolicy / 能源策略 Agent**
   - 让低电量事件进一步影响导航和车控。
   - 例如低电量导航自动建议补能点，严重低电量限制座椅加热。

2. **前端工程拆分**
   - `web_demo/static/app.js` 已经较大，可以拆成 event stream、vehicle state、command runner、renderers 等模块。

3. **文档与演示脚本精修**
   - 把“面试演示顺序”和“面试官可能追问”整理成一页速记稿。

4. **真实车端状态源适配层**
   - 当前车辆状态是内存模拟。
   - 后续可抽象为 CAN/车机状态服务/地图道路属性服务适配器。

## 2026-05-08 交付验收补充

本轮已补齐“交付级演示与验收闭环”，项目不再只依赖手工点击页面证明功能可用。

新增能力：

- `scripts/run_delivery_check.py`：一键交付验收脚本。
- `reports/delivery_check_report.md`：自动生成的交付验收报告。
- Demo Mode 车辆状态预设：点击面试演示场景时，会先写入对应车辆上下文，再运行指令。
- 前端模块化：`web_demo/static/app.js` 已拆分为 API、state、events、markdown 与 renderers 多个模块。

推荐验收命令：

```bash
python scripts/run_delivery_check.py
```

如果只想做快速演示前检查，可跳过完整单元测试：

```bash
python scripts/run_delivery_check.py --skip-unit-tests
```

最新稳定回归基线：

```text
231 passed, 1 warning, 139 subtests passed
```

当前 5 个面试必演示场景：

| 场景 | 指令 | 车辆上下文 | 预期状态 |
| --- | --- | --- | --- |
| 正常导航端云协同 | `导航去蔚来中心` | HIGHWAY / 120km/h / 35% | `NAVIGATION / EXECUTED` |
| 模糊目的地澄清 | `导航去北京` | HIGHWAY / 120km/h / 35% | `NAVIGATION / NEEDS_CLARIFICATION` |
| 高速速度请求确认 | `加速到100km/h` | HIGHWAY / 120km/h / 35% | `CAR_CONTROL / NEEDS_DRIVER_CONFIRMATION` |
| 城市超限危险拦截 | `加速到100km/h` | URBAN / 60km/h / 35% | `CAR_CONTROL / BLOCKED` |
| 低电量状态与能源策略 | `导航去蔚来中心` | HIGHWAY / 120km/h / 8% | `NAVIGATION / NEEDS_CHARGE_CONFIRMATION` |

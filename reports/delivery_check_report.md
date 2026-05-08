# 车载 Multi-Agent 交付验收报告

- 生成时间：2026-05-08T17:56:18+08:00
- 总体状态：PASS
- 稳定环境：Mock Local LLM + Offline Provider，真实 Provider smoke 为可选项

## 验收步骤

| 步骤 | 状态 | 耗时 |
| --- | --- | ---: |
| unit tests | PASS | 6.05s |
| frontend js syntax | PASS | 1.17s |
| demo scenarios | PASS | 1.45s |
| provider smoke | SKIP | 0.00s |

## 面试演示场景

| 场景 | 指令 | 车辆状态 | 预期结果 |
| --- | --- | --- | --- |
| 正常导航端云协同 | `导航去蔚来中心` | HIGHWAY / 120km/h / 35% | NAVIGATION / EXECUTED |
| 模糊目的地澄清 | `导航去北京` | HIGHWAY / 120km/h / 35% | NAVIGATION / NEEDS_CLARIFICATION |
| 高速速度请求确认 | `加速到100km/h` | HIGHWAY / 120km/h / 35% | CAR_CONTROL / NEEDS_DRIVER_CONFIRMATION |
| 城市超限危险拦截 | `加速到100km/h` | URBAN / 60km/h / 35% | CAR_CONTROL / BLOCKED |
| 低电量状态与能源策略 | `导航去蔚来中心` | HIGHWAY / 120km/h / 8% | NAVIGATION / NEEDS_CHARGE_CONFIRMATION |

## 详细输出

### unit tests

- 状态：PASS
- 耗时：6.05s

```text
$ C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests --basetemp=E:\claudeCode\weilaiAgent\.tmp\delivery-pytest -q
........................................................................ [ 31%]
............................................................................................ [ 70%]
......................................................... [ 95%]
..........                                                               [100%]
============================== warnings summary ===============================
tests/test_cloud_agents.py::TestCloudAgents::test_cloud_schedule_combines_profile_ecology_and_route
  C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\langgraph\cache\base\__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
231 passed, 1 warning, 139 subtests passed in 4.27s
```

### frontend js syntax

- 状态：PASS
- 耗时：1.17s

```text
16 JavaScript files checked
```

### demo scenarios

- 状态：PASS
- 耗时：1.45s

```text
正常导航端云协同: NAVIGATION/EXECUTED expected NAVIGATION/EXECUTED
模糊目的地澄清: NAVIGATION/NEEDS_CLARIFICATION expected NAVIGATION/NEEDS_CLARIFICATION
高速速度请求确认: CAR_CONTROL/NEEDS_DRIVER_CONFIRMATION expected CAR_CONTROL/NEEDS_DRIVER_CONFIRMATION
城市超限危险拦截: CAR_CONTROL/BLOCKED expected CAR_CONTROL/BLOCKED
低电量状态与能源策略: NAVIGATION/NEEDS_CHARGE_CONFIRMATION expected NAVIGATION/NEEDS_CHARGE_CONFIRMATION
```

### provider smoke

- 状态：SKIP
- 耗时：0.00s

```text
real external provider smoke is opt-in: pass --include-provider-smoke
```

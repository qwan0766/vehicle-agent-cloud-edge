# 车载 Multi-Agent 验收报告

- 生成时间：2026-05-07T23:47:45+08:00
- 总体状态：PASS

## 验收步骤

| 步骤 | 状态 | 耗时 |
| --- | --- | ---: |
| unit tests | PASS | 53.75s |
| offline evaluation | PASS | 1.95s |
| provider smoke | SKIP | 0.00s |
| online matrix | SKIP | 0.00s |

## 本轮工程硬化覆盖

- `INFO_QUERY`：安全知识问答从 `UNKNOWN` 中拆出，作为正常业务意图。
- `NEEDS_CLARIFICATION`：模糊目的地是正常澄清状态，不作为外部接口错误。
- 目的地候选契约：低置信度地图结果可携带候选地点给前端确认。
- 数据闭环：澄清态不更新用户偏好，避免把不完整输入写成长期偏好。

## 详细输出

### unit tests

- 状态：PASS
- 耗时：53.75s

```text
$ C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests
.......................C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\langgraph\cache\base\__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
  from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
................................................................................................................................................
----------------------------------------------------------------------
Ran 167 tests in 52.966s

OK
```

### offline evaluation

- 状态：PASS
- 耗时：1.95s

```text
{
  "total": 20,
  "intent_accuracy": 1.0,
  "safety_accuracy": 1.0,
  "status_accuracy": 1.0,
  "safety_block_recall": 1.0,
  "rag_hit_rate": 1.0,
  "failed_cases": []
}
```

### provider smoke

- 状态：SKIP
- 耗时：0.00s

```text
skipped by CLI flag
```

### online matrix

- 状态：SKIP
- 耗时：0.00s

```text
skipped by CLI flag
```

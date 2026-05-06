# 车载 Multi-Agent 验收报告

- 生成时间：2026-05-06T22:04:53+08:00
- 总体状态：PASS

## 验收步骤

| 步骤 | 状态 | 耗时 |
| --- | --- | ---: |
| unit tests | PASS | 35.86s |
| offline evaluation | PASS | 3.55s |
| provider smoke | PASS | 2.52s |
| online matrix | PASS | 39.27s |

## 详细输出

### unit tests

- 状态：PASS
- 耗时：35.86s

```text
$ C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests
...............C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\langgraph\cache\base\__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
  from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
..........................................................................................................
----------------------------------------------------------------------
Ran 121 tests in 34.467s

OK
```

### offline evaluation

- 状态：PASS
- 耗时：3.55s

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

- 状态：PASS
- 耗时：2.52s

```text
[
  {
    "name": "DeepSeek LLM",
    "status": "OK",
    "detail": "OK"
  },
  {
    "name": "Open-Meteo Weather",
    "status": "OK",
    "detail": {
      "city": "当前位置",
      "summary": "实时天气",
      "temperature_c": 16,
      "wind_level": "13.0km/h"
    }
  },
  {
    "name": "AMap Route",
    "status": "OK",
    "detail": {
      "provider": "amap_route",
      "origin": "121.48,31.23",
      "destination": "121.50,31.25",
      "distance_km": 4.0,
      "duration_minutes": 10,
      "strategy": "高速优先"
    }
  },
  {
    "name": "AMap POI",
    "status": "OK",
    "detail": [
      {
        "name": "特来电汽车充电站(特来电上海海通证券大厦充电站)",
        "distance_km": 0.11,
        "status": "可用，评分3.5",
        "estimated_minutes": 30
      },
      {
        "name": "广汽能源汽车充电站(广汽昊铂上海港陆广场超充站)",
        "distance_km": 0.12,
        "status": "可用，评分3.7",
        "estimated_minutes": 30
      },
      {
        "name": "乐华汽车充电站(港陆广场直流充电站)",
        "distance_km": 0.13,
        "status": "可用，评分3.6",
        "estimated_minutes": 30
      }
    ]
  },
  {
    "name": "OpenChargeMap",
    "status": "SKIP",
    "detail": "已由 AMap POI 替代，未配置 OPENCHARGEMAP_API_KEY"
  },
  {
    "name": "Baidu Map",
    "status": "SKIP",
    "detail": "BAIDU_MAP_AK 未配置"
  }
]
```

### online matrix

- 状态：PASS
- 耗时：39.27s

```text
[
  {
    "content": "到外滩",
    "status": "PASS",
    "detail": "checks passed"
  },
  {
    "content": "导航去 121.50,31.25",
    "status": "PASS",
    "detail": "checks passed"
  },
  {
    "content": "温度调到24度",
    "status": "PASS",
    "detail": "checks passed"
  },
  {
    "content": "我的偏好",
    "status": "PASS",
    "detail": "checks passed"
  },
  {
    "content": "打开视频网站",
    "status": "PASS",
    "detail": "checks passed"
  },
  {
    "content": "关闭AEB",
    "status": "PASS",
    "detail": "checks passed"
  },
  {
    "content": "电量低",
    "status": "PASS",
    "detail": "checks passed"
  }
]
```

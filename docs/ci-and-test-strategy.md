# CI 与测试分层说明

## 目标

这个项目的 CI 只验证“可交付的离线工程闭环”，不在 GitHub Actions 中调用真实 DeepSeek、高德、Open-Meteo 等外部接口。这样做是为了避免测试结果受 API Key、额度、网络波动影响。

## 默认 CI 做什么

`.github/workflows/ci.yml` 在 push、PR 和手动触发时运行：

1. 安装 Python 3.11 与 Node.js 20。
2. 安装 `pytest` 和 `requirements-optional.txt` 中的可选运行时依赖。
3. 显式清空真实 API Key，并固定为 `mock_local` 和离线 Provider。
4. 运行 `python scripts/run_delivery_check.py --unit-timeout 300`。
5. 上传 `reports/delivery_check_report.md` 作为 CI artifact。

## 测试分层

### 离线默认层

命令：

```bash
python scripts/run_delivery_check.py --unit-timeout 300
```

覆盖内容：

- 全量 `pytest tests`
- 前端 JavaScript 语法检查
- 5 条稳定演示场景回归
- Mock Local LLM
- Offline Provider

这层不需要 `.env`，适合作为 GitHub Actions 默认检查。

### 真实 Provider Smoke 层

命令：

```bash
python scripts/run_delivery_check.py --include-provider-smoke
```

或单独运行：

```bash
python scripts/smoke_real_providers.py
```

覆盖内容：

- DeepSeek LLM
- Open-Meteo Weather
- AMap Route
- AMap POI

这层需要本地 `.env` 中配置真实 key，属于手动 opt-in，不放入默认 CI。

## 为什么 CI 里仍安装 optional 依赖

项目默认启用 LangGraph，因此 CI 会安装 `requirements-optional.txt` 并设置 `ENABLE_LANGGRAPH=1`。这里的“离线”指不调用真实外部 API，而不是关闭编排器；这样能同时验证 LangGraph 主链路和离线可重复交付能力。

## 面试表述

可以这样解释：

> 我把测试分成离线可重复 CI 和真实 Provider smoke 两层。默认 CI 不依赖外部 API，保证每次 push 都稳定验证核心业务链路；真实接口连通性通过本地 smoke test 手动触发，避免把 API 波动引入主干质量门禁。

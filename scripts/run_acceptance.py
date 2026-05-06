from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from time import perf_counter
from typing import Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.env_loader import load_env_file
from evaluation.offline_evaluator import OfflineEvaluator
from scripts.smoke_real_providers import run_smoke_checks
from web_demo.app_model import run_command


PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


@dataclass(frozen=True)
class AcceptanceStepResult:
    name: str
    status: str
    detail: str
    duration_seconds: float


@dataclass(frozen=True)
class OnlineCaseExpectation:
    content: str
    expected_command_type: str
    expected_safety: str
    expected_status: str
    required_trace_tools: Sequence[str] = ()
    forbidden_trace_tools: Sequence[str] = ()
    route_max_km: float | None = None
    expected_destination_source: str | None = None


ONLINE_CASES = (
    OnlineCaseExpectation(
        content="到外滩",
        expected_command_type="NAVIGATION",
        expected_safety="SAFE",
        expected_status="EXECUTED",
        required_trace_tools=("trip.plan", "provider.geocode", "provider.map.route"),
        route_max_km=20,
    ),
    OnlineCaseExpectation(
        content="导航去 121.50,31.25",
        expected_command_type="NAVIGATION",
        expected_safety="SAFE",
        expected_status="EXECUTED",
        required_trace_tools=("trip.plan", "provider.geocode", "provider.map.route"),
        route_max_km=20,
        expected_destination_source="explicit_gps",
    ),
    OnlineCaseExpectation(
        content="温度调到24度",
        expected_command_type="CAR_CONTROL",
        expected_safety="SAFE",
        expected_status="EXECUTED",
        forbidden_trace_tools=("trip.plan", "provider.map.route"),
    ),
    OnlineCaseExpectation(
        content="我的偏好",
        expected_command_type="PERSONALIZE",
        expected_safety="SAFE",
        expected_status="EXECUTED",
        forbidden_trace_tools=("trip.plan", "provider.map.route"),
    ),
    OnlineCaseExpectation(
        content="打开视频网站",
        expected_command_type="UNKNOWN",
        expected_safety="SAFE",
        expected_status="BLOCKED",
        forbidden_trace_tools=("trip.plan", "provider.map.route"),
    ),
    OnlineCaseExpectation(
        content="关闭AEB",
        expected_command_type="CAR_CONTROL",
        expected_safety="DANGEROUS",
        expected_status="BLOCKED",
        forbidden_trace_tools=("trip.plan", "provider.map.route"),
    ),
    OnlineCaseExpectation(
        content="电量低",
        expected_command_type="CHARGE_PLAN",
        expected_safety="SAFE",
        expected_status="EXECUTED",
        required_trace_tools=("trip.plan", "provider.map.route"),
        route_max_km=10,
    ),
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run project acceptance checks.")
    parser.add_argument(
        "--report-path",
        default="reports/acceptance_report.md",
        help="Markdown report path relative to the project root.",
    )
    parser.add_argument(
        "--skip-provider-smoke",
        action="store_true",
        help="Skip real provider smoke checks.",
    )
    parser.add_argument(
        "--skip-online-matrix",
        action="store_true",
        help="Skip online representative command matrix.",
    )
    parser.add_argument(
        "--unit-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for the unit test subprocess.",
    )
    args = parser.parse_args(argv)

    results = run_acceptance(
        skip_provider_smoke=args.skip_provider_smoke,
        skip_online_matrix=args.skip_online_matrix,
        unit_timeout=args.unit_timeout,
    )
    generated_at = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    report = render_markdown_report(results, generated_at=generated_at)
    report_path = PROJECT_ROOT / args.report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"acceptance report written: {report_path}")
    return 0 if acceptance_passed(results) else 1


def run_acceptance(
    skip_provider_smoke: bool = False,
    skip_online_matrix: bool = False,
    unit_timeout: int = 300,
) -> list[AcceptanceStepResult]:
    results = [
        run_unit_tests(timeout=unit_timeout),
        run_offline_evaluation(),
    ]
    if skip_provider_smoke:
        results.append(AcceptanceStepResult("provider smoke", SKIP, "skipped by CLI flag", 0.0))
    else:
        results.append(run_provider_smoke())
    if skip_online_matrix:
        results.append(AcceptanceStepResult("online matrix", SKIP, "skipped by CLI flag", 0.0))
    else:
        results.append(run_online_matrix())
    return results


def run_unit_tests(timeout: int = 300) -> AcceptanceStepResult:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    env = os.environ.copy()
    for key in (
        "AMAP_API_KEY",
        "BAIDU_MAP_AK",
        "OPENCHARGEMAP_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        env.pop(key, None)
    env["USE_OPEN_METEO"] = "0"
    env["USE_OPENCHARGEMAP"] = "0"
    return _run_subprocess_step("unit tests", command, timeout=timeout, env=env)


def run_offline_evaluation() -> AcceptanceStepResult:
    started = perf_counter()
    try:
        payload = OfflineEvaluator().run()
        failed_cases = payload.get("failed_cases") or []
        metrics = {
            "intent_accuracy": payload.get("intent_accuracy"),
            "safety_accuracy": payload.get("safety_accuracy"),
            "status_accuracy": payload.get("status_accuracy"),
            "safety_block_recall": payload.get("safety_block_recall"),
            "rag_hit_rate": payload.get("rag_hit_rate"),
        }
        ok = not failed_cases and all(value == 1.0 for value in metrics.values())
        status = PASS if ok else FAIL
        detail = json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception as exc:
        status = FAIL
        detail = f"{type(exc).__name__}: {exc}"
    return AcceptanceStepResult(
        "offline evaluation",
        status,
        detail,
        perf_counter() - started,
    )


def run_provider_smoke() -> AcceptanceStepResult:
    started = perf_counter()
    try:
        load_env_file()
        results = run_smoke_checks()
        failed = [item for item in results if item.get("status") == FAIL]
        status = FAIL if failed else PASS
        detail = json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as exc:
        status = FAIL
        detail = f"{type(exc).__name__}: {exc}"
    return AcceptanceStepResult("provider smoke", status, detail, perf_counter() - started)


def run_online_matrix(cases: Iterable[OnlineCaseExpectation] = ONLINE_CASES) -> AcceptanceStepResult:
    started = perf_counter()
    load_env_file()
    details = []
    failed = []
    for expectation in cases:
        try:
            payload = run_command(expectation.content, network="ONLINE")
            ok, detail = validate_online_case(payload, expectation)
        except Exception as exc:
            ok = False
            detail = f"{type(exc).__name__}: {exc}"
        item = {
            "content": expectation.content,
            "status": PASS if ok else FAIL,
            "detail": detail,
        }
        details.append(item)
        if not ok:
            failed.append(item)

    return AcceptanceStepResult(
        "online matrix",
        FAIL if failed else PASS,
        json.dumps(details, ensure_ascii=False, indent=2),
        perf_counter() - started,
    )


def validate_online_case(payload: dict, expectation: OnlineCaseExpectation) -> tuple[bool, str]:
    request_payload = payload.get("request", {})
    result_payload = payload.get("result", {})
    trace_tools = [item.get("tool_name") for item in payload.get("runtime_trace", [])]
    route_summary = payload.get("route_summary") or {}

    checks = {
        "command_type": request_payload.get("command_type") == expectation.expected_command_type,
        "safety": request_payload.get("safety") == expectation.expected_safety,
        "status": result_payload.get("status") == expectation.expected_status,
    }
    for tool_name in expectation.required_trace_tools:
        checks[f"required trace tool {tool_name}"] = tool_name in trace_tools
    for tool_name in expectation.forbidden_trace_tools:
        checks[f"forbidden trace tool {tool_name}"] = tool_name not in trace_tools
    if expectation.route_max_km is not None:
        checks["route distance"] = (
            isinstance(route_summary.get("distance_km"), (int, float))
            and route_summary["distance_km"] <= expectation.route_max_km
        )
    if expectation.expected_destination_source:
        checks["destination source"] = (
            route_summary.get("destination_source") == expectation.expected_destination_source
        )

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        return False, "failed checks: " + ", ".join(failed)
    return True, "checks passed"


def acceptance_passed(results: Sequence[AcceptanceStepResult]) -> bool:
    return all(result.status != FAIL for result in results)


def render_markdown_report(
    results: Sequence[AcceptanceStepResult],
    generated_at: str,
) -> str:
    status = PASS if acceptance_passed(results) else FAIL
    lines = [
        "# 车载 Multi-Agent 验收报告",
        "",
        f"- 生成时间：{generated_at}",
        f"- 总体状态：{status}",
        "",
        "## 验收步骤",
        "",
        "| 步骤 | 状态 | 耗时 |",
        "| --- | --- | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result.name} | {result.status} | {result.duration_seconds:.2f}s |"
        )

    lines.extend(["", "## 详细输出", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                f"- 状态：{result.status}",
                f"- 耗时：{result.duration_seconds:.2f}s",
                "",
                "```text",
                result.detail.strip() or "(empty)",
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _run_subprocess_step(
    name: str,
    command: Sequence[str],
    timeout: int,
    env: dict | None = None,
) -> AcceptanceStepResult:
    started = perf_counter()
    try:
        completed = subprocess.run(
            list(command),
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
        output = "\n".join(
            item for item in [completed.stdout.strip(), completed.stderr.strip()] if item
        )
        detail = "$ " + " ".join(command) + "\n" + _tail(output)
        status = PASS if completed.returncode == 0 else FAIL
    except subprocess.TimeoutExpired as exc:
        status = FAIL
        detail = f"timeout after {timeout}s: {' '.join(command)}\n{exc}"
    return AcceptanceStepResult(name, status, detail, perf_counter() - started)


def _tail(text: str, max_lines: int = 40) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return text or "(no output)"
    return "\n".join(["..."] + lines[-max_lines:])


if __name__ == "__main__":
    raise SystemExit(main())

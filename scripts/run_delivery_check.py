from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    duration_seconds: float


DEMO_CASES = [
    {
        "id": "online_navigation",
        "title": "正常导航端云协同",
        "content": "导航去蔚来中心",
        "network": "ONLINE",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 35,
            "driver_assist_mode": "ACC",
        },
        "expected_status": "EXECUTED",
        "expected_command_type": "NAVIGATION",
    },
    {
        "id": "fuzzy_destination_clarification",
        "title": "模糊目的地澄清",
        "content": "导航去北京",
        "network": "ONLINE",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 35,
            "driver_assist_mode": "ACC",
        },
        "expected_status": "NEEDS_CLARIFICATION",
        "expected_command_type": "NAVIGATION",
    },
    {
        "id": "highway_speed_confirmation",
        "title": "高速速度请求确认",
        "content": "加速到100km/h",
        "network": "ONLINE",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 35,
            "driver_assist_mode": "ACC",
        },
        "expected_status": "NEEDS_DRIVER_CONFIRMATION",
        "expected_command_type": "CAR_CONTROL",
    },
    {
        "id": "urban_speed_block",
        "title": "城市超限危险拦截",
        "content": "加速到100km/h",
        "network": "ONLINE",
        "vehicle_state": {
            "road_type": "URBAN",
            "speed_limit_kmh": 60,
            "speed_kmh": 40,
            "battery_percent": 35,
            "driver_assist_mode": "MANUAL",
        },
        "expected_status": "BLOCKED",
        "expected_command_type": "CAR_CONTROL",
    },
    {
        "id": "low_battery_energy_policy",
        "title": "低电量状态与能源策略",
        "content": "导航去蔚来中心",
        "network": "ONLINE",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 8,
            "driver_assist_mode": "ACC",
        },
        "expected_status": "NEEDS_CHARGE_CONFIRMATION",
        "expected_command_type": "NAVIGATION",
    },
]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run delivery-grade project checks.")
    parser.add_argument(
        "--report-path",
        default="reports/delivery_check_report.md",
        help="Markdown report path relative to the project root.",
    )
    parser.add_argument(
        "--include-provider-smoke",
        action="store_true",
        help="Also call real external provider smoke checks.",
    )
    parser.add_argument(
        "--skip-unit-tests",
        action="store_true",
        help="Skip pytest unit regression.",
    )
    parser.add_argument(
        "--unit-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for pytest.",
    )
    args = parser.parse_args(argv)

    results = run_delivery_check(
        include_provider_smoke=args.include_provider_smoke,
        skip_unit_tests=args.skip_unit_tests,
        unit_timeout=args.unit_timeout,
    )
    generated_at = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    report = render_report(results, generated_at=generated_at)
    report_path = PROJECT_ROOT / args.report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"delivery check report written: {report_path}")
    return 0 if all(result.status != FAIL for result in results) else 1


def run_delivery_check(
    include_provider_smoke: bool = False,
    skip_unit_tests: bool = False,
    unit_timeout: int = 300,
) -> list[CheckResult]:
    results = []
    if skip_unit_tests:
        results.append(CheckResult("unit tests", SKIP, "skipped by CLI flag", 0.0))
    else:
        results.append(run_unit_tests(timeout=unit_timeout))
    results.append(run_frontend_js_syntax())
    results.append(run_demo_scenarios())
    if include_provider_smoke:
        results.append(run_provider_smoke())
    else:
        results.append(
            CheckResult(
                "provider smoke",
                SKIP,
                "real external provider smoke is opt-in: pass --include-provider-smoke",
                0.0,
            )
        )
    return results


def run_unit_tests(timeout: int) -> CheckResult:
    basetemp = PROJECT_ROOT / ".tmp" / "delivery-pytest"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        f"--basetemp={basetemp}",
        "-q",
    ]
    return run_subprocess("unit tests", command, timeout=timeout, env=build_stable_env())


def run_frontend_js_syntax() -> CheckResult:
    started = perf_counter()
    node = find_node()
    if not node:
        return CheckResult(
            "frontend js syntax",
            FAIL,
            "node executable not found",
            perf_counter() - started,
        )

    js_files = sorted((PROJECT_ROOT / "web_demo" / "static").rglob("*.js"))
    failures = []
    for js_file in js_files:
        completed = subprocess.run(
            [node, "--check", str(js_file)],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            failures.append(
                f"{js_file.relative_to(PROJECT_ROOT)}\n{completed.stdout}\n{completed.stderr}".strip()
            )

    detail = (
        f"{len(js_files)} JavaScript files checked"
        if not failures
        else "\n\n".join(failures)
    )
    return CheckResult(
        "frontend js syntax",
        PASS if not failures else FAIL,
        detail,
        perf_counter() - started,
    )


def run_demo_scenarios() -> CheckResult:
    started = perf_counter()
    apply_stable_env()
    reset_runtime_state()

    from web_demo.app_model import reset_vehicle_state, run_command, update_vehicle_state

    details = []
    failures = []
    for case in DEMO_CASES:
        reset_vehicle_state()
        update_vehicle_state(case["vehicle_state"])
        payload = run_command(
            case["content"],
            network=case["network"],
            user_id=f"delivery_{case['id']}",
        )
        actual_status = payload["result"]["status"]
        actual_command_type = payload["request"]["command_type"]
        ok = (
            actual_status == case["expected_status"]
            and actual_command_type == case["expected_command_type"]
        )
        row = (
            f"{case['title']}: {actual_command_type}/{actual_status}"
            f" expected {case['expected_command_type']}/{case['expected_status']}"
        )
        details.append(row)
        if not ok:
            failures.append(row)

    return CheckResult(
        "demo scenarios",
        PASS if not failures else FAIL,
        "\n".join(details),
        perf_counter() - started,
    )


def reset_runtime_state() -> None:
    runtime_dir = PROJECT_ROOT / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("local_context_state.json", "pending_clarifications.json"):
        (runtime_dir / filename).write_text("{}", encoding="utf-8")


def run_provider_smoke() -> CheckResult:
    started = perf_counter()
    try:
        from config.env_loader import load_env_file
        from scripts.smoke_real_providers import run_smoke_checks

        load_env_file()
        results = run_smoke_checks()
        failures = [item for item in results if item.get("status") == FAIL]
        return CheckResult(
            "provider smoke",
            FAIL if failures else PASS,
            repr(results),
            perf_counter() - started,
        )
    except Exception as exc:
        return CheckResult(
            "provider smoke",
            FAIL,
            f"{type(exc).__name__}: {exc}",
            perf_counter() - started,
        )


def build_stable_env() -> dict[str, str]:
    env = os.environ.copy()
    env["DEEPSEEK_API_KEY"] = ""
    env["LOCAL_LLM_PROVIDER"] = "mock_local"
    env["LOCAL_LLM_API_KEY"] = ""
    env["AMAP_API_KEY"] = ""
    env["BAIDU_MAP_AK"] = ""
    env["OPENCHARGEMAP_API_KEY"] = ""
    env["USE_OPEN_METEO"] = "0"
    env["USE_OPENCHARGEMAP"] = "0"
    env["ENABLE_LANGGRAPH"] = "1"
    return env


def apply_stable_env() -> None:
    os.environ.update(build_stable_env())


def find_node() -> str:
    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "node"
        / "bin"
        / "node.exe"
    )
    if bundled.exists():
        return str(bundled)
    return shutil.which("node") or ""


def run_subprocess(
    name: str,
    command: Sequence[str],
    timeout: int,
    env: dict[str, str],
) -> CheckResult:
    started = perf_counter()
    try:
        completed = subprocess.run(
            list(command),
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = "\n".join(
            item for item in [completed.stdout.strip(), completed.stderr.strip()] if item
        )
        detail = "$ " + " ".join(command) + "\n" + tail(output)
        status = PASS if completed.returncode == 0 else FAIL
    except subprocess.TimeoutExpired as exc:
        status = FAIL
        detail = f"timeout after {timeout}s: {' '.join(command)}\n{exc}"
    return CheckResult(name, status, detail, perf_counter() - started)


def render_report(results: Sequence[CheckResult], generated_at: str) -> str:
    overall = PASS if all(result.status != FAIL for result in results) else FAIL
    lines = [
        "# 车载 Multi-Agent 交付验收报告",
        "",
        f"- 生成时间：{generated_at}",
        f"- 总体状态：{overall}",
        "- 稳定环境：Mock Local LLM + Offline Provider，真实 Provider smoke 为可选项",
        "",
        "## 验收步骤",
        "",
        "| 步骤 | 状态 | 耗时 |",
        "| --- | --- | ---: |",
    ]
    for result in results:
        lines.append(f"| {result.name} | {result.status} | {result.duration_seconds:.2f}s |")

    lines.extend(
        [
            "",
            "## 面试演示场景",
            "",
            "| 场景 | 指令 | 车辆状态 | 预期结果 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for case in DEMO_CASES:
        vehicle = case["vehicle_state"]
        state_text = (
            f"{vehicle['road_type']} / {vehicle['speed_limit_kmh']}km/h / "
            f"{vehicle['battery_percent']}%"
        )
        expected = f"{case['expected_command_type']} / {case['expected_status']}"
        lines.append(f"| {case['title']} | `{case['content']}` | {state_text} | {expected} |")

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


def tail(text: str, max_lines: int = 50) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return text or "(no output)"
    return "\n".join(["..."] + lines[-max_lines:])


if __name__ == "__main__":
    raise SystemExit(main())

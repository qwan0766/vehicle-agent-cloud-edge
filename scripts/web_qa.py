import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "web_qa_report.md"
DEFAULT_JSON = PROJECT_ROOT / "reports" / "web_qa_report.json"
DEFAULT_SCREENSHOT_DIR = PROJECT_ROOT / "reports" / "browser_qa"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def main():
    parser = argparse.ArgumentParser(description="Run web demo QA checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--screenshots", action="store_true")
    parser.add_argument("--screenshot-dir", default=str(DEFAULT_SCREENSHOT_DIR))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results = []

    results.extend(check_static_assets(base_url))
    results.extend(check_state(base_url))
    results.extend(check_command_matrix(base_url))

    screenshots = []
    if args.screenshots:
        screenshot_dir = Path(args.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        results.extend(capture_screenshots(base_url, screenshot_dir, screenshots))

    overall = "PASS" if all(item.status in {"PASS", "SKIP"} for item in results) else "FAIL"
    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "base_url": base_url,
        "overall_status": overall,
        "checks": [item.__dict__ for item in results],
        "screenshots": screenshots,
    }

    report_path = Path(args.report)
    json_path = Path(args.json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"web qa report written: {report_path}")
    print(f"web qa json written: {json_path}")
    print(f"overall: {overall}")
    if overall != "PASS":
        raise SystemExit(1)


def check_static_assets(base_url):
    checks = []
    for path, min_size in [("/", 1000), ("/app.js", 5000), ("/styles.css", 3000)]:
        status, body, _ = http_get(base_url + path)
        if status == 200 and len(body) >= min_size:
            checks.append(CheckResult(f"asset {path}", "PASS", f"HTTP 200, {len(body)} bytes"))
        else:
            checks.append(CheckResult(f"asset {path}", "FAIL", f"HTTP {status}, {len(body)} bytes"))
    return checks


def check_state(base_url):
    status, body, payload = http_get_json(base_url + "/api/state")
    if status != 200:
        return [CheckResult("api state", "FAIL", f"HTTP {status}: {body[:160]}")]

    providers = payload.get("providers", {})
    acceptance = payload.get("acceptance", {})
    required = ["llm", "local_llm", "orchestrator", "map", "weather", "charge"]
    missing = [name for name in required if name not in providers]
    if missing:
        return [CheckResult("api state", "FAIL", f"missing providers: {', '.join(missing)}")]

    detail = (
        f"orchestrator={providers.get('orchestrator')}, "
        f"acceptance={acceptance.get('overall_status')}"
    )
    return [CheckResult("api state", "PASS", detail)]


def check_command_matrix(base_url):
    cases = [
        {
            "name": "online navigation",
            "payload": {
                "content": "\u5bfc\u822a\u53bb\u851a\u6765\u4e2d\u5fc3",
                "user_id": "qa_nav",
                "network": "ONLINE",
            },
            "http": 200,
            "command": "NAVIGATION",
            "status": "EXECUTED",
            "requires_trip_plan": True,
        },
        {
            "name": "online car control",
            "payload": {
                "content": "\u6e29\u5ea6\u8c03\u523024\u5ea6",
                "user_id": "qa_car",
                "network": "ONLINE",
            },
            "http": 200,
            "command": "CAR_CONTROL",
            "status": "EXECUTED",
            "requires_trip_plan": False,
        },
        {
            "name": "dangerous block",
            "payload": {
                "content": "\u5173\u95edAEB",
                "user_id": "qa_safe",
                "network": "ONLINE",
            },
            "http": 200,
            "command": "CAR_CONTROL",
            "status": "BLOCKED",
            "requires_trip_plan": False,
        },
        {
            "name": "offline fallback",
            "payload": {
                "content": "\u6253\u5f00\u5ea7\u6905\u52a0\u70ed",
                "user_id": "qa_offline",
                "network": "OFFLINE",
            },
            "http": 200,
            "command": "CAR_CONTROL",
            "status": "FALLBACK",
            "requires_trip_plan": False,
        },
    ]
    results = [check_command_case(base_url, case) for case in cases]
    results.append(check_online_error_case(base_url))
    return results


def check_command_case(base_url, case):
    status, body, payload = http_post_json(base_url + "/api/run", case["payload"])
    if status != case["http"]:
        return CheckResult(case["name"], "FAIL", f"HTTP {status}, expected {case['http']}: {body[:160]}")

    request_payload = payload.get("request", {})
    result_payload = payload.get("result", {})
    graph = payload.get("graph") or {}
    agent_trace = payload.get("agent_trace") or []
    path = graph.get("path") or []
    has_trip_plan = "trip_plan" in path or "GlobalTripPlanningAgent" in agent_trace
    failures = []

    if request_payload.get("command_type") != case["command"]:
        failures.append(f"command={request_payload.get('command_type')}")
    if result_payload.get("status") != case["status"]:
        failures.append(f"status={result_payload.get('status')}")
    if has_trip_plan != case["requires_trip_plan"]:
        failures.append(f"trip_plan={has_trip_plan}")

    if failures:
        return CheckResult(case["name"], "FAIL", ", ".join(failures))

    detail = (
        f"{case['command']} / {case['status']} / "
        f"graph={graph.get('mode') or '-'} / trip_plan={has_trip_plan}"
    )
    return CheckResult(case["name"], "PASS", detail)


def check_online_error_case(base_url):
    status, body, payload = http_post_json(
        base_url + "/api/run",
        {
            "content": "\u5bfc\u822a\u53bb\u5df4\u9ece",
            "user_id": "qa_error",
            "network": "ONLINE",
        },
    )
    info = payload.get("error") or {}
    title = info.get("user_title") or ""
    suggestions = info.get("suggestions") or []
    if status == 502 and title and suggestions and info.get("technical_message"):
        return CheckResult("online friendly error", "PASS", f"HTTP 502, title={title}")
    return CheckResult("online friendly error", "FAIL", f"HTTP {status}: {body[:240]}")


def capture_screenshots(base_url, screenshot_dir, screenshots):
    browser = find_browser()
    if not browser:
        return [CheckResult("browser screenshots", "FAIL", "Chrome/Edge executable not found")]

    specs = [
        ("desktop", 1440, 1100),
        ("mobile", 390, 900),
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix="web-qa-browser-") as user_data_dir:
        for name, width, height in specs:
            target = screenshot_dir / f"{name}.png"
            ok, detail = run_screenshot(
                browser=browser,
                user_data_dir=user_data_dir,
                url=base_url + "/",
                target=target,
                width=width,
                height=height,
            )
            if ok:
                screenshots.append(str(target))
                results.append(CheckResult(f"screenshot {name}", "PASS", detail))
            else:
                results.append(CheckResult(f"screenshot {name}", "FAIL", detail))
    return results


def find_browser():
    candidates = [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    for name in ["msedge", "chrome", "google-chrome", "chromium"]:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return ""


def run_screenshot(browser, user_data_dir, url, target, width, height):
    base_flags = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-scrollbars",
        f"--user-data-dir={user_data_dir}",
        f"--window-size={width},{height}",
        f"--screenshot={target}",
        "--virtual-time-budget=5000",
        url,
    ]
    try:
        completed = subprocess.run(
            base_flags,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=45,
        )
    except Exception as exc:
        return False, str(exc)

    if completed.returncode == 0 and target.exists() and target.stat().st_size > 1000:
        return True, f"{target} ({target.stat().st_size} bytes)"
    detail = (completed.stderr or completed.stdout or f"exit {completed.returncode}").strip()
    return False, detail[:500]


def http_get(url):
    try:
        with request.urlopen(url, timeout=30) as response:
            return response.status, response.read().decode("utf-8", errors="replace"), response.headers
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), exc.headers
    except Exception as exc:
        return 0, str(exc), {}


def http_get_json(url):
    status, body, _ = http_get(url)
    try:
        return status, body, json.loads(body)
    except json.JSONDecodeError:
        return status, body, {}


def http_post_json(url, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, raw, json.loads(raw)
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        return exc.code, raw, payload
    except Exception as exc:
        return 0, str(exc), {}


def render_markdown(payload):
    lines = [
        "# Web QA Report",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Base URL: {payload['base_url']}",
        f"- Overall status: {payload['overall_status']}",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for item in payload["checks"]:
        lines.append(
            f"| {item['name']} | {item['status']} | {escape_table(item['detail'])} |"
        )
    if payload["screenshots"]:
        lines.extend(["", "## Screenshots", ""])
        for screenshot in payload["screenshots"]:
            path = Path(screenshot)
            lines.append(f"- {path.name}: `{path}`")
    lines.append("")
    return "\n".join(lines)


def escape_table(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()

import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.env_loader import load_env_file
from llm.deepseek_client import DeepSeekLLMClient
from providers.amap_poi_provider import AmapPOIProvider
from providers.amap_route_provider import AmapRouteProvider
from providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


def main():
    load_env_file()
    results = run_smoke_checks()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item["status"] in {"OK", "SKIP"} for item in results) else 1


def run_smoke_checks():
    return [
        _smoke_deepseek(),
        _smoke_open_meteo(),
        _smoke_amap_route(),
        _smoke_amap_poi(),
    ]


def _smoke_deepseek():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return _result("DeepSeek LLM", "SKIP", "DEEPSEEK_API_KEY 未配置")
    try:
        client = DeepSeekLLMClient(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            timeout=30,
        )
        text = client.generate("你是连通性测试助手。", "只回复 OK。", {"test": "smoke"})
        return _result("DeepSeek LLM", "OK", text[:160])
    except Exception as exc:
        return _result("DeepSeek LLM", "FAIL", _error_detail(exc))


def _smoke_open_meteo():
    try:
        weather = OpenMeteoWeatherProvider(timeout=20).get_weather("121.48, 31.23")
        return _result("Open-Meteo Weather", "OK", weather.__dict__)
    except Exception as exc:
        return _result("Open-Meteo Weather", "FAIL", _error_detail(exc))


def _smoke_amap_route():
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        return _result("AMap Route", "SKIP", "AMAP_API_KEY 未配置")
    try:
        route = AmapRouteProvider(api_key=api_key, timeout=20).plan_route(
            "121.48,31.23",
            "121.50,31.25",
            preference="高速",
        )
        return _result("AMap Route", "OK", route.__dict__)
    except Exception as exc:
        return _result("AMap Route", "FAIL", _error_detail(exc))


def _smoke_amap_poi():
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        return _result("AMap POI", "SKIP", "AMAP_API_KEY 未配置")
    try:
        stations = AmapPOIProvider(api_key=api_key, timeout=20).find_nearby(
            "121.48, 31.23",
            limit=3,
        )
        return _result("AMap POI", "OK", [station.__dict__ for station in stations])
    except Exception as exc:
        return _result("AMap POI", "FAIL", _error_detail(exc))

def _result(name: str, status: str, detail):
    return {"name": name, "status": status, "detail": detail}


def _error_detail(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            body = ""
        return f"HTTPError {exc.code}: {body or exc.reason}"
    if isinstance(exc, URLError):
        return f"URLError: {exc.reason}"
    return f"{type(exc).__name__}: {exc}"


if __name__ == "__main__":
    raise SystemExit(main())

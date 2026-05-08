from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
import traceback
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).resolve().parent / "static"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web_demo.app_model import (
    confirm_pending_action,
    get_acceptance_payload,
    get_initial_payload,
    get_vehicle_events_payload,
    run_command,
    run_provider_smoke_test,
    update_vehicle_state,
)
from providers.destination_resolver import extract_destination_query


class WebDemoHandler(SimpleHTTPRequestHandler):
    GET_ROUTES = {"/api/state", "/api/acceptance", "/api/vehicle-events"}
    POST_ROUTES = {"/api/run", "/api/confirm", "/api/provider-smoke", "/api/vehicle-state"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/api/state":
            self._send_json(get_initial_payload())
            return
        if self.path == "/api/acceptance":
            self._send_json(get_acceptance_payload())
            return
        if self.path == "/api/vehicle-events":
            self._send_json(get_vehicle_events_payload())
            return
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path not in self.POST_ROUTES:
            self.send_error(404, "Not Found")
            return
        if self.path == "/api/provider-smoke":
            self._send_json(run_provider_smoke_test())
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if self.path == "/api/vehicle-state":
            self._send_json(update_vehicle_state(payload))
            return
        if self.path == "/api/confirm":
            try:
                self._send_json(
                    confirm_pending_action(
                        payload.get("action_id", ""),
                        user_id=payload.get("user_id", "user_001"),
                        confirmed=payload.get("confirmed", True),
                        selection=payload.get("selection") or {},
                    )
                )
            except Exception as exc:
                self._send_json(
                    {
                        "error": build_error_response(
                            exc,
                            content="pending action confirmation",
                            network="ONLINE",
                        )
                    },
                    status=404,
                )
            return

        content = payload.get("content", "")
        user_id = payload.get("user_id", "user_001")
        network = payload.get("network", "ONLINE")
        try:
            self._send_json(run_command(content, user_id=user_id, network=network))
        except Exception as exc:
            self._send_json(
                {
                    "error": build_error_response(
                        exc,
                        content=content,
                        network=network,
                    )
                },
                status=502,
            )

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000):
    server = ThreadingHTTPServer((host, port), WebDemoHandler)
    print(f"Web demo running at http://{host}:{port}")
    server.serve_forever()


def parse_server_args(argv=None):
    parser = argparse.ArgumentParser(description="Run offline vehicle agent web demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(argv)


def build_error_response(exc: Exception, content: str = "", network: str = "ONLINE"):
    technical_message = str(exc)
    destination = extract_destination_query(content) or content or "当前指令"
    response = {
        "type": exc.__class__.__name__,
        "message": technical_message,
        "technical_message": technical_message,
        "traceback": traceback.format_exc(limit=3),
        "user_title": "在线能力暂时不可用",
        "user_message": "这次请求已经进入在线链路，但外部服务没有返回可执行结果。",
        "suggestions": [
            "稍后重试一次，确认外部 API 当前可用。",
            "换一个更具体的目的地名称，尽量带上城市或地标。",
        ],
    }

    if "Destination clarification required" in technical_message:
        response.update(
            {
                "provider": "destination_clarification",
                "user_title": "需要确认目的地",
                "user_message": (
                    f"“{destination}”还不足以确认唯一可导航地点，"
                    "系统没有直接调用地图规划路线。请补充更具体的城市、商圈、门店或完整地址。"
                ),
                "suggestions": [
                    "请说得更具体一些，例如“导航去北京东方广场蔚来中心”。",
                    "如果只是城市名，请补充具体地点，例如机场、车站、商圈或门店。",
                    "如果是连锁门店，请补充城市或所在商场，避免导航到错误分店。",
                ],
            }
        )
        return response

    if "AMap geocode error" in technical_message:
        response.update(
            {
                "provider": "amap_geocode",
                "user_title": "没有找到这个目的地",
                "user_message": (
                    f"高德地理编码没有解析出“{destination}”的有效坐标。"
                    "常见原因是地点过于宽泛、名称不完整，或该地点超出了当前高德驾车路线演示的覆盖范围。"
                ),
                "suggestions": [
                    "把目的地写得更具体，例如“导航去上海外滩”或“导航去杭州萧山国际机场”。",
                    "如果是海外目的地，当前接入的高德驾车路线 API 可能无法规划跨境路线。",
                    "如果你知道坐标，也可以直接输入经纬度，例如“导航去 121.497253,31.238235”。",
                ],
            }
        )
        return response

    if "AMap geocode low confidence" in technical_message:
        response.update(
            {
                "provider": "amap_geocode",
                "user_title": "目的地置信度过低",
                "user_message": (
                    f"地图服务返回了一个与“{destination}”不够一致的候选地点，"
                    "系统没有直接开始导航，避免把您带到错误位置。"
                ),
                "suggestions": [
                    "请补充城市、商圈或完整 POI 名称，例如“导航去上海松江印象城蔚来中心”。",
                    "如果您只是测试不存在的地点，可以换一个真实地标再试。",
                    "如果页面显示了候选地点，请确认名称一致后再重新发起导航。",
                ],
            }
        )
        return response

    if "AMap route error" in technical_message:
        response.update(
            {
                "provider": "amap_route",
                "user_title": "地图没有规划出可行路线",
                "user_message": (
                    f"目的地“{destination}”可能已解析成功，但高德驾车路线服务没有返回可行路线。"
                    "这通常发生在跨城市/跨境不支持、坐标不可达，或路线服务临时异常时。"
                ),
                "suggestions": [
                    "尝试换成更明确的国内地址或地标。",
                    "确认目的地适合驾车路线规划，而不是国家、城市名或过大的区域。",
                    "稍后重试，排除地图服务临时不可用。",
                ],
            }
        )
        return response

    if "DeepSeek" in technical_message or "chat/completions" in technical_message:
        response.update(
            {
                "provider": "deepseek",
                "user_title": "大模型生成失败",
                "user_message": "路线和外部数据已经进入调度链路，但 DeepSeek 没有成功生成最终说明。",
                "suggestions": [
                    "稍后重试，或检查 DeepSeek API Key 与账户额度。",
                    "保留 Agent Trace 里的地图和 POI 结果，用于判断前置工具是否成功。",
                ],
            }
        )
        return response

    if "timed out" in technical_message.lower() or "timeout" in technical_message.lower():
        response.update(
            {
                "user_title": "外部服务响应超时",
                "user_message": "在线 Provider 在限定时间内没有返回结果，系统没有使用离线兜底。",
                "suggestions": [
                    "稍后重试一次。",
                    "如果连续超时，可以先点击 Smoke Test 查看是哪一个 Provider 不稳定。",
                ],
            }
        )

    return response


if __name__ == "__main__":
    args = parse_server_args()
    run(host=args.host, port=args.port)

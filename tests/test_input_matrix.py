import unittest
import uuid
from pathlib import Path

from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.vehicle.local_intent_agent import LocalIntentAgent
from agents.vehicle.safety_agent import SafetyAgent
from core.constants import CommandType
from core.constants import ExecutionStatus
from core.constants import NetworkStatus
from core.constants import SafetyLevel
from core.vehicle_core_service import VehicleCoreService
from memory.pending_clarification_store import PendingClarificationStore
from providers.destination_resolver import DestinationClarificationRequired, resolve_destination_detail
from web_demo.server import build_error_response


class FakeGeocoder:
    provider_name = "fake_geocode"

    def __init__(self):
        self.addresses = []

    def geocode(self, address):
        self.addresses.append(address)

        class Result:
            name = address
            gps = "121.497253,31.238235"

        return Result()


class FakeMapProvider:
    provider_name = "fake_map"

    def plan_route(self, origin, destination, preference=""):
        class Route:
            provider = "fake_map"
            distance_km = 9.6
            duration_minutes = 22
            strategy = "高速优先" if preference == "高速" else "时间优先"

            def to_text(self):
                return f"{self.provider}路线：{destination}，{self.distance_km}km，{self.duration_minutes}分钟"

        return Route()


class FakeLLM:
    provider_name = "fake_llm"

    def generate(self, system_prompt, user_prompt, context=None):
        destination = (context or {}).get("destination", {})
        return f"已规划到{destination.get('name')}的路线"


class RecordingCloudAgent:
    def __init__(self):
        self.contents = []

    def dispatch(self, msg):
        self.contents.append(msg.content)
        return "route ok"

    def get_last_trace(self):
        return []

    def get_last_graph(self):
        return {}


def pending_matrix_path():
    path = Path(".tmp-tests") / f"input-matrix-{uuid.uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class TestInputMatrix(unittest.TestCase):
    def test_intent_matrix_covers_common_user_phrasings(self):
        agent = LocalIntentAgent(enable_llm_fallback=False)
        navigation_prefixes = [
            "导航去",
            "导航到",
            "我要去",
            "我想去",
            "去",
            "到",
            "帮我导航到",
            "帮我导航去",
            "开车去",
        ]
        navigation_destinations = [
            "外滩",
            "上海虹桥站",
            "杭州萧山国际机场",
            "人民广场",
            "东方明珠",
            "121.50,31.25",
        ]
        cases = {
            "导航去外滩": CommandType.NAVIGATION,
            "导航到上海虹桥站": CommandType.NAVIGATION,
            "我要去人民广场": CommandType.NAVIGATION,
            "去杭州萧山国际机场": CommandType.NAVIGATION,
            "到外滩": CommandType.NAVIGATION,
            "到121.50,31.25": CommandType.NAVIGATION,
            "打开座椅加热": CommandType.CAR_CONTROL,
            "开启座椅加热": CommandType.CAR_CONTROL,
            "温度调到24度": CommandType.CAR_CONTROL,
            "空调调到23度": CommandType.CAR_CONTROL,
            "电量低": CommandType.CHARGE_PLAN,
            "帮我找换电站": CommandType.CHARGE_PLAN,
            "我的偏好": CommandType.PERSONALIZE,
            "看一下我的用户画像": CommandType.PERSONALIZE,
            "播放音乐": CommandType.UNKNOWN,
            "查询股票行情": CommandType.UNKNOWN,
            "AEB是什么": CommandType.UNKNOWN,
            "播放一首加速感很强的歌": CommandType.UNKNOWN,
            "我不想导航去蔚来中心，只是问问怎么取消导航": CommandType.UNKNOWN,
            "加速到100km/h": CommandType.CAR_CONTROL,
            "立即刹车": CommandType.CAR_CONTROL,
            "关闭AEB": CommandType.CAR_CONTROL,
        }

        for prefix in navigation_prefixes:
            for destination in navigation_destinations:
                cases[f"{prefix}{destination}"] = CommandType.NAVIGATION

        car_control_inputs = [
            "座椅加热打开",
            "帮我打开座椅加热",
            "关闭座椅加热",
            "空调调到23度",
            "把温度调到22度",
            "温度设置为25度",
            "调低温度",
            "调高温度",
            "打开空调",
            "关闭空调",
            "打开车窗",
        ]
        charge_inputs = [
            "电量低",
            "帮我找换电站",
            "电量低，需要补能",
            "充电规划",
            "附近有没有换电站",
        ]
        personalize_inputs = [
            "我的偏好",
            "看一下我的用户画像",
            "个性化偏好",
            "查看用户画像",
        ]
        unknown_inputs = [
            "播放音乐",
            "查询股票行情",
            "讲个笑话",
            "打开视频网站",
            "播放一首加速感很强的歌",
            "我不想导航去蔚来中心，只是问问怎么取消导航",
        ]
        info_query_inputs = [
            "AEB是什么",
            "讲一下制动距离",
        ]

        cases.update({content: CommandType.CAR_CONTROL for content in car_control_inputs})
        cases.update({content: CommandType.CHARGE_PLAN for content in charge_inputs})
        cases.update({content: CommandType.PERSONALIZE for content in personalize_inputs})
        cases.update({content: CommandType.INFO_QUERY for content in info_query_inputs})
        cases.update({content: CommandType.UNKNOWN for content in unknown_inputs})

        for content, expected in cases.items():
            with self.subTest(content=content):
                self.assertEqual(agent.recognize(content), expected)

    def test_safety_matrix_blocks_vehicle_dynamics_and_assistance_override(self):
        agent = SafetyAgent()
        dangerous_inputs = [
            "加速到100km/h",
            "立即刹车",
            "帮我转向",
            "动力提升",
            "关闭AEB",
            "关闭aeb",
            "关闭自动紧急制动",
            "接管方向盘",
            "执行自动转向",
        ]
        safe_inputs = [
            "导航去外滩",
            "打开座椅加热",
            "温度调到24度",
            "电量低",
            "AEB是什么",
            "讲一下制动距离",
            "播放一首加速感很强的歌",
        ]

        for content in dangerous_inputs:
            with self.subTest(content=content):
                self.assertEqual(agent.check(content), SafetyLevel.DANGEROUS)

        for content in safe_inputs:
            with self.subTest(content=content):
                self.assertEqual(agent.check(content), SafetyLevel.SAFE)

    def test_destination_matrix_resolves_known_dynamic_and_coordinate_inputs(self):
        cases = [
            ("导航去蔚来中心", "蔚来中心", "121.50,31.25", "builtin"),
            ("我要回家", "家", "121.42,31.20", "builtin"),
            ("电量低", "附近补能点", "121.481,31.231", "builtin"),
            ("导航去外滩", "外滩", "121.497253,31.238235", "fake_geocode"),
            ("导航到上海虹桥站", "上海虹桥站", "121.497253,31.238235", "fake_geocode"),
            ("导航去北京的蔚来中心", "北京蔚来中心", "121.497253,31.238235", "fake_geocode"),
            ("导航去 121.50,31.25", "121.50,31.25", "121.50,31.25", "explicit_gps"),
        ]

        for content, name, gps, source in cases:
            with self.subTest(content=content):
                result = resolve_destination_detail(content, geocoder=FakeGeocoder())
                self.assertEqual(result.name, name)
                self.assertEqual(result.gps, gps)
                self.assertEqual(result.source, source)

    def test_destination_matrix_clarifies_fuzzy_inputs_before_geocoder(self):
        for content in ["导航去高老庄", "导航去北京", "导航去霓虹蔚来中心"]:
            with self.subTest(content=content):
                geocoder = FakeGeocoder()
                with self.assertRaises(DestinationClarificationRequired):
                    resolve_destination_detail(content, geocoder=geocoder)
                self.assertEqual(geocoder.addresses, [])

    def test_vehicle_service_matrix_handles_clarification_and_precise_inputs(self):
        cases = [
            ("导航去北京", ExecutionStatus.NEEDS_CLARIFICATION, []),
            ("导航去上海", ExecutionStatus.NEEDS_CLARIFICATION, []),
            ("导航去高老庄", ExecutionStatus.NEEDS_CLARIFICATION, []),
            ("导航去霓虹蔚来中心", ExecutionStatus.NEEDS_CLARIFICATION, []),
            ("导航去121.48,31.23", ExecutionStatus.EXECUTED, ["导航去121.48,31.23"]),
            ("打开座椅加热", ExecutionStatus.EXECUTED, ["打开座椅加热"]),
            ("关闭AEB", ExecutionStatus.BLOCKED, []),
        ]

        for content, expected_status, expected_cloud_contents in cases:
            with self.subTest(content=content):
                cloud = RecordingCloudAgent()
                service = VehicleCoreService(
                    cloud_agent=cloud,
                    pending_clarification_store=PendingClarificationStore(
                        pending_matrix_path()
                    ),
                )

                result = service.run(content, network=NetworkStatus.ONLINE)

                self.assertEqual(result.status, expected_status)
                self.assertEqual(cloud.contents, expected_cloud_contents)

    def test_cloud_route_agent_records_provider_level_trace_for_dynamic_destination(self):
        agent = CloudRoutePlanAgent(
            llm_client=FakeLLM(),
            map_provider=FakeMapProvider(),
            geocoder=FakeGeocoder(),
        )

        output = agent.plan("导航去外滩", route_preference="高速")
        trace = agent.get_last_provider_trace()

        self.assertIn("已规划到外滩", output)
        self.assertEqual([item["tool_name"] for item in trace], ["provider.geocode", "provider.map.route"])
        self.assertEqual([item["agent_id"] for item in trace], ["RouteProviderAgent", "RouteProviderAgent"])
        self.assertEqual([item["status"] for item in trace], ["OK", "OK"])
        self.assertEqual(trace[0]["output"]["destination_name"], "外滩")
        self.assertEqual(trace[1]["output"]["provider"], "fake_map")

    def test_error_matrix_keeps_user_message_readable_and_technical_detail_separate(self):
        cases = [
            (
                RuntimeError("AMap geocode error: ENGINE_RESPONSE_DATA_ERROR"),
                "导航去巴黎",
                "没有找到这个目的地",
                "amap_geocode",
            ),
            (
                RuntimeError("AMap route error: INVALID_PARAMS"),
                "导航去火星",
                "地图没有规划出可行路线",
                "amap_route",
            ),
            (
                TimeoutError("request timed out"),
                "导航去外滩",
                "外部服务响应超时",
                None,
            ),
        ]

        for exc, content, title, provider in cases:
            with self.subTest(content=content, exc=str(exc)):
                payload = build_error_response(exc, content=content, network="ONLINE")
                self.assertEqual(payload["user_title"], title)
                self.assertNotIn("ENGINE_RESPONSE_DATA_ERROR", payload["user_message"])
                self.assertNotIn("INVALID_PARAMS", payload["user_message"])
                self.assertTrue(payload["suggestions"])
                self.assertIn("technical_message", payload)
                if provider:
                    self.assertEqual(payload["provider"], provider)


if __name__ == "__main__":
    unittest.main()

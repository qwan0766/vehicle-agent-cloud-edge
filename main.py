from core.constants import NetworkStatus
from core.vehicle_core_service import VehicleCoreService
from data.vehicle_state import DEFAULT_VEHICLE_STATE
from feedback.feedback_service import FeedbackService


def print_vehicle_state(network: NetworkStatus):
    print("======== 车辆状态面板 ========")
    print(f"车速：{DEFAULT_VEHICLE_STATE.speed_kmh} km/h")
    print(f"电量：{DEFAULT_VEHICLE_STATE.battery_percent} %")
    print(f"网络状态：{network.value}")
    print("安全状态：正常")
    print("==============================")


def print_result(result):
    print(f"请求ID：{result.message.request_id}")
    print(f"解析意图：{result.message.command_type.value}")
    print(f"安全等级：{result.message.safety.value}")
    print(f"网络状态：{result.message.network.value}")
    print(f"执行状态：{result.status.value}")
    print(f"最终结果：{result.output}")
    if result.feedback:
        print(f"数据闭环：{result.feedback['event_status']}")
        print(f"偏好更新：{result.feedback['preference_update']}")


def run_scenario(
    title: str,
    service: VehicleCoreService,
    user_input: str,
    network: NetworkStatus,
):
    print(f"\n==== {title} ====")
    print_vehicle_state(network)
    print(f"用户输入：{user_input}")
    result = service.run(user_input, network=network)
    print_result(result)


def main():
    service = VehicleCoreService(feedback_service=FeedbackService())

    run_scenario("场景1：行程启动（端云协同）", service, "导航去蔚来中心", NetworkStatus.ONLINE)
    run_scenario("场景2：行驶途中（断网本地执行）", service, "打开座椅加热", NetworkStatus.OFFLINE)
    run_scenario("场景3：中途补给（充电规划）", service, "电量低", NetworkStatus.ONLINE)
    run_scenario("场景4：行程结束（数据闭环）", service, "我的偏好", NetworkStatus.ONLINE)
    run_scenario("安全测试：危险指令拦截", service, "加速到100km/h", NetworkStatus.ONLINE)


if __name__ == "__main__":
    main()

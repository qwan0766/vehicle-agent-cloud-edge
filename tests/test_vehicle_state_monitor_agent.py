from agents.vehicle.vehicle_state_monitor_agent import VehicleStateMonitorAgent
from core.constants import NetworkStatus, RoadType
from data.vehicle_state import VehicleState


def test_low_battery_state_generates_charge_plan_event():
    agent = VehicleStateMonitorAgent(low_battery_threshold=20)
    state = VehicleState(
        speed_kmh=60,
        battery_percent=18,
        network=NetworkStatus.ONLINE,
        gps="121.48, 31.23",
        road_type=RoadType.HIGHWAY,
        speed_limit_kmh=120,
    )

    events = agent.detect_events(state)

    assert events == [
        {
            "type": "BATTERY_LOW",
            "command_type": "CHARGE_PLAN",
            "content": "电量低",
            "trigger": "AUTO",
            "reason": "电量18%，低于20%补能提醒阈值",
        }
    ]


def test_normal_battery_state_has_no_auto_event():
    agent = VehicleStateMonitorAgent(low_battery_threshold=20)
    state = VehicleState(
        speed_kmh=60,
        battery_percent=35,
        network=NetworkStatus.ONLINE,
        gps="121.48, 31.23",
        road_type=RoadType.HIGHWAY,
        speed_limit_kmh=120,
    )

    assert agent.detect_events(state) == []


def test_speed_over_limit_generates_warning_event():
    agent = VehicleStateMonitorAgent()
    state = VehicleState(
        speed_kmh=150,
        battery_percent=35,
        network=NetworkStatus.ONLINE,
        gps="121.48, 31.23",
        road_type=RoadType.HIGHWAY,
        speed_limit_kmh=120,
    )

    events = agent.detect_events(state)

    assert events == [
        {
            "type": "SPEED_OVER_LIMIT",
            "command_type": "CAR_CONTROL",
            "content": "车速超过当前限速",
            "trigger": "AUTO",
            "reason": "当前车速150km/h，高于限速120km/h",
        }
    ]

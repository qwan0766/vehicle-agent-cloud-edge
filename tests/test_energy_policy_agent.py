from agents.vehicle.energy_policy_agent import EnergyPolicyAgent
from core.constants import CommandType, ExecutionStatus, NetworkStatus, RoadType
from data.vehicle_state import VehicleState


def _state(battery_percent):
    return VehicleState(
        speed_kmh=60,
        battery_percent=battery_percent,
        network=NetworkStatus.ONLINE,
        gps="121.48, 31.23",
        road_type=RoadType.HIGHWAY,
        speed_limit_kmh=120,
    )


def test_low_battery_navigation_adds_energy_advisory_without_blocking():
    decision = EnergyPolicyAgent().evaluate(
        CommandType.NAVIGATION,
        "导航去蔚来中心",
        _state(18),
    )

    assert decision.allowed is True
    assert decision.status == ExecutionStatus.EXECUTED
    assert "建议规划补能点" in decision.advisory


def test_critical_battery_navigation_requires_charge_confirmation():
    decision = EnergyPolicyAgent().evaluate(
        CommandType.NAVIGATION,
        "导航去机场",
        _state(8),
    )

    assert decision.allowed is False
    assert decision.status == ExecutionStatus.NEEDS_CHARGE_CONFIRMATION
    assert "电量严重不足" in decision.reason


def test_critical_battery_blocks_comfort_power_consuming_control():
    decision = EnergyPolicyAgent().evaluate(
        CommandType.CAR_CONTROL,
        "打开座椅加热",
        _state(4),
    )

    assert decision.allowed is False
    assert decision.status == ExecutionStatus.BLOCKED
    assert "低电量" in decision.reason

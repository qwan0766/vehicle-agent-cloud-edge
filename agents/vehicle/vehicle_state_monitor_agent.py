from core.constants import CommandType


class VehicleStateMonitorAgent:
    role_name = "车辆状态监控 Agent"

    def __init__(self, low_battery_threshold: int = 20, critical_battery_threshold: int = 10):
        self.low_battery_threshold = low_battery_threshold
        self.critical_battery_threshold = critical_battery_threshold

    def detect_events(self, vehicle_state):
        events = []
        speed = int(getattr(vehicle_state, "speed_kmh", 0))
        speed_limit = int(getattr(vehicle_state, "speed_limit_kmh", 0))
        if speed_limit > 0 and speed > speed_limit:
            events.append(
                {
                    "type": "SPEED_OVER_LIMIT",
                    "command_type": CommandType.CAR_CONTROL.value,
                    "content": "车速超过当前限速",
                    "trigger": "AUTO",
                    "reason": f"当前车速{speed}km/h，高于限速{speed_limit}km/h",
                }
            )

        battery = int(getattr(vehicle_state, "battery_percent", 0))
        if battery <= self.critical_battery_threshold:
            events.append(
                {
                    "type": "BATTERY_CRITICAL",
                    "command_type": CommandType.CHARGE_PLAN.value,
                    "content": "电量严重不足",
                    "trigger": "AUTO",
                    "reason": (
                        f"电量{battery}%，低于{self.critical_battery_threshold}%紧急补能阈值"
                    ),
                }
            )
        elif battery <= self.low_battery_threshold:
            events.append(
                {
                    "type": "BATTERY_LOW",
                    "command_type": CommandType.CHARGE_PLAN.value,
                    "content": "电量低",
                    "trigger": "AUTO",
                    "reason": (
                        f"电量{battery}%，低于{self.low_battery_threshold}%补能提醒阈值"
                    ),
                }
            )
        return events

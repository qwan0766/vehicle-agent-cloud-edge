from data.knowledge_base import ECOLOGY_DATA


class CloudEcologyAgent:
    def get_data(self) -> str:
        return (
            f"外部生态数据：{ECOLOGY_DATA['weather']}，"
            f"{ECOLOGY_DATA['swap_station']}"
        )

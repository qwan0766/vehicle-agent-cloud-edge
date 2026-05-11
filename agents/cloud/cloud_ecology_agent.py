from data.vehicle_state import DEFAULT_VEHICLE_STATE
from providers.factory import create_charge_provider, create_weather_provider


class CloudEcologyAgent:
    def __init__(self, weather_provider=None, charge_provider=None):
        self.weather_provider = weather_provider or create_weather_provider()
        self.charge_provider = charge_provider or create_charge_provider()

    def get_data(self, gps: str = DEFAULT_VEHICLE_STATE.gps) -> str:
        return self.format_snapshot(self.get_snapshot(gps))

    def format_snapshot(self, snapshot: dict) -> str:
        weather = snapshot["weather"]
        station = snapshot["charge_stations"][0]
        return (
            "外部生态数据："
            f"天气 {weather['summary']}，{weather['temperature_c']}℃，"
            f"降水 {weather['precipitation_mm']}mm，风 {weather['wind_level']}；"
            f"补能 {station['name']}{station['status']}，距离{station['distance_km']}km；"
            f"来源 {weather['source']} / {snapshot['charge_source']}"
        )

    def get_snapshot(self, gps: str = DEFAULT_VEHICLE_STATE.gps) -> dict:
        weather = self.weather_provider.get_weather(gps)
        stations = self.charge_provider.find_nearby(gps)

        return {
            "weather": {
                "city": weather.city,
                "summary": weather.summary,
                "temperature_c": weather.temperature_c,
                "wind_level": weather.wind_level,
                "precipitation_mm": weather.precipitation_mm,
                "weather_code": weather.weather_code,
                "source": weather.source,
            },
            "charge_source": getattr(self.charge_provider, "provider_name", "unknown_charge"),
            "charge_stations": [
                {
                    "name": station.name,
                    "distance_km": station.distance_km,
                    "status": station.status,
                    "estimated_minutes": station.estimated_minutes,
                }
                for station in stations
            ],
        }

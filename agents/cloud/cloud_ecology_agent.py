from data.vehicle_state import DEFAULT_VEHICLE_STATE
from providers.offline_charge_provider import OfflineChargeProvider
from providers.offline_weather_provider import OfflineWeatherProvider


class CloudEcologyAgent:
    def __init__(self, weather_provider=None, charge_provider=None):
        self.weather_provider = weather_provider or OfflineWeatherProvider()
        self.charge_provider = charge_provider or OfflineChargeProvider()

    def get_data(self, gps: str = DEFAULT_VEHICLE_STATE.gps) -> str:
        snapshot = self.get_snapshot(gps)
        station = snapshot["charge_stations"][0]
        return (
            f"外部生态数据：{snapshot['weather']['summary']}，"
            f"{station['name']}{station['status']}，距离{station['distance_km']}km"
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
            },
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

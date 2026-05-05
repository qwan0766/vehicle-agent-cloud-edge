from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherSnapshot:
    city: str
    summary: str
    temperature_c: int
    wind_level: str


class OfflineWeatherProvider:
    provider_name = "offline_weather"

    def get_weather(self, gps: str) -> WeatherSnapshot:
        return WeatherSnapshot(
            city="上海",
            summary="天气晴",
            temperature_c=24,
            wind_level="2级",
        )

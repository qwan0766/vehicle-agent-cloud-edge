from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WeatherSnapshot:
    city: str
    summary: str
    temperature_c: int
    wind_level: str
    precipitation_mm: float = 0.0
    weather_code: Optional[int] = None
    source: str = "offline_weather"


class OfflineWeatherProvider:
    provider_name = "offline_weather"

    def get_weather(self, gps: str) -> WeatherSnapshot:
        return WeatherSnapshot(
            city="上海",
            summary="天气晴",
            temperature_c=24,
            wind_level="2级",
            precipitation_mm=0.0,
            weather_code=0,
            source=self.provider_name,
        )

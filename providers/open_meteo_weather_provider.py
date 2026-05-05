import json
from urllib import parse, request

from providers.offline_weather_provider import WeatherSnapshot


class OpenMeteoWeatherProvider:
    provider_name = "open_meteo"

    def __init__(self, timeout: int = 10, transport=None):
        self.timeout = timeout
        self.transport = transport or _get_json

    def build_forecast_url(self, gps: str) -> str:
        longitude, latitude = _parse_gps(gps)
        query = parse.urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": "Asia/Shanghai",
            }
        )
        return f"https://api.open-meteo.com/v1/forecast?{query}"

    def get_weather(self, gps: str) -> WeatherSnapshot:
        payload = self.transport(self.build_forecast_url(gps), self.timeout)
        current = payload.get("current", {})
        temperature = int(round(float(current.get("temperature_2m", 24))))
        wind_speed = current.get("wind_speed_10m", 0)
        return WeatherSnapshot(
            city="当前位置",
            summary="实时天气",
            temperature_c=temperature,
            wind_level=f"{wind_speed}km/h",
        )


def _parse_gps(gps: str):
    lon, lat = [part.strip() for part in gps.split(",", 1)]
    return lon, lat


def _get_json(url: str, timeout: int):
    with request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

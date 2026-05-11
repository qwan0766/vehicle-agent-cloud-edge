from urllib import parse

from providers.errors import ProviderBadResponseError
from providers.http import get_json
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
                "current": "temperature_2m,weather_code,wind_speed_10m,precipitation",
                "timezone": "Asia/Shanghai",
            }
        )
        return f"https://api.open-meteo.com/v1/forecast?{query}"

    def get_weather(self, gps: str) -> WeatherSnapshot:
        payload = self.transport(self.build_forecast_url(gps), self.timeout)
        current = payload.get("current")
        if not isinstance(current, dict):
            raise ProviderBadResponseError(
                "Open-Meteo returned no current weather",
                provider=self.provider_name,
                operation="forecast",
                code="OPEN_METEO_MISSING_CURRENT",
            )
        try:
            temperature = int(round(float(current.get("temperature_2m", 24))))
            wind_speed = current.get("wind_speed_10m", 0)
            weather_code = current.get("weather_code")
            precipitation = round(float(current.get("precipitation", 0) or 0), 1)
        except (TypeError, ValueError) as exc:
            raise ProviderBadResponseError(
                "Open-Meteo returned invalid current weather",
                provider=self.provider_name,
                operation="forecast",
                code="OPEN_METEO_INVALID_CURRENT",
            ) from exc
        return WeatherSnapshot(
            city="当前位置",
            summary=f"实时天气：{_weather_code_summary(weather_code)}",
            temperature_c=temperature,
            wind_level=f"{wind_speed}km/h",
            precipitation_mm=precipitation,
            weather_code=weather_code,
            source=self.provider_name,
        )


def _parse_gps(gps: str):
    lon, lat = [part.strip() for part in gps.split(",", 1)]
    return lon, lat


def _get_json(url: str, timeout: int):
    return get_json(
        url,
        timeout,
        provider=OpenMeteoWeatherProvider.provider_name,
        operation="forecast",
    )


def _weather_code_summary(code):
    mapping = {
        0: "晴",
        1: "大部晴朗",
        2: "局部多云",
        3: "阴",
        45: "雾",
        48: "霜雾",
        51: "小毛毛雨",
        53: "中等毛毛雨",
        55: "较强毛毛雨",
        61: "小雨",
        63: "中雨",
        65: "大雨",
        71: "小雪",
        73: "中雪",
        75: "大雪",
        80: "阵雨",
        81: "中等阵雨",
        82: "强阵雨",
        95: "雷暴",
    }
    try:
        return mapping.get(int(code), f"天气代码 {code}")
    except (TypeError, ValueError):
        return "未知"

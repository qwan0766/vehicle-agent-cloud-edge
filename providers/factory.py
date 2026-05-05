import os

from providers.amap_poi_provider import AmapPOIProvider
from providers.baidu_map_provider import BaiduMapProvider
from providers.offline_charge_provider import OfflineChargeProvider
from providers.offline_map_provider import OfflineMapProvider
from providers.offline_weather_provider import OfflineWeatherProvider
from providers.open_charge_map_provider import OpenChargeMapProvider
from providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


def create_map_provider():
    api_key = os.getenv("BAIDU_MAP_AK")
    if api_key:
        return BaiduMapProvider(api_key=api_key)
    return OfflineMapProvider()


def create_weather_provider():
    if os.getenv("USE_OPEN_METEO") == "1":
        return OpenMeteoWeatherProvider()
    return OfflineWeatherProvider()


def create_charge_provider():
    amap_key = os.getenv("AMAP_API_KEY")
    if amap_key:
        return AmapPOIProvider(api_key=amap_key)
    api_key = os.getenv("OPENCHARGEMAP_API_KEY", "")
    if api_key or os.getenv("USE_OPENCHARGEMAP") == "1":
        return OpenChargeMapProvider(api_key=api_key)
    return OfflineChargeProvider()

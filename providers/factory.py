from typing import Optional

from config.settings import AppSettings, get_settings
from providers.amap_poi_provider import AmapPOIProvider
from providers.amap_geocode_provider import AmapGeocodeProvider
from providers.amap_route_provider import AmapRouteProvider
from providers.baidu_map_provider import BaiduMapProvider
from providers.offline_charge_provider import OfflineChargeProvider
from providers.offline_map_provider import OfflineMapProvider
from providers.offline_weather_provider import OfflineWeatherProvider
from providers.open_charge_map_provider import OpenChargeMapProvider
from providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


def create_map_provider(settings: Optional[AppSettings] = None):
    settings = settings or get_settings()
    amap_key = settings.providers.amap_api_key
    if amap_key:
        return AmapRouteProvider(api_key=amap_key)
    api_key = settings.providers.baidu_map_ak
    if api_key:
        return BaiduMapProvider(api_key=api_key)
    return OfflineMapProvider()


def create_geocode_provider(settings: Optional[AppSettings] = None):
    settings = settings or get_settings()
    amap_key = settings.providers.amap_api_key
    if amap_key:
        return AmapGeocodeProvider(
            api_key=amap_key,
            city=settings.providers.amap_geocode_city,
        )
    return None


def create_weather_provider(settings: Optional[AppSettings] = None):
    settings = settings or get_settings()
    if settings.providers.use_open_meteo:
        return OpenMeteoWeatherProvider()
    return OfflineWeatherProvider()


def create_charge_provider(settings: Optional[AppSettings] = None):
    settings = settings or get_settings()
    amap_key = settings.providers.amap_api_key
    if amap_key:
        return AmapPOIProvider(api_key=amap_key)
    api_key = settings.providers.open_charge_map_api_key
    if api_key or settings.providers.use_open_charge_map:
        return OpenChargeMapProvider(api_key=api_key)
    return OfflineChargeProvider()


def create_destination_candidate_provider(settings: Optional[AppSettings] = None):
    settings = settings or get_settings()
    amap_key = settings.providers.amap_api_key
    if amap_key:
        return AmapPOIProvider(api_key=amap_key)
    return None

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AppSettings:
    amap_api_key: Optional[str]
    baidu_map_ak: Optional[str]
    amap_geocode_city: str
    use_open_meteo: Optional[str]
    open_charge_map_api_key: str
    use_open_charge_map: Optional[str]


def get_settings() -> AppSettings:
    return AppSettings(
        amap_api_key=os.getenv("AMAP_API_KEY"),
        baidu_map_ak=os.getenv("BAIDU_MAP_AK"),
        amap_geocode_city=os.getenv("AMAP_GEOCODE_CITY", ""),
        use_open_meteo=os.getenv("USE_OPEN_METEO"),
        open_charge_map_api_key=os.getenv("OPENCHARGEMAP_API_KEY", ""),
        use_open_charge_map=os.getenv("USE_OPENCHARGEMAP"),
    )

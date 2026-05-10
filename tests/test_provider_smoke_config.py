import unittest
from pathlib import Path


class TestProviderSmokeConfig(unittest.TestCase):
    def test_provider_smoke_only_checks_active_demo_interfaces(self):
        source = Path("scripts/smoke_real_providers.py").read_text(encoding="utf-8")

        self.assertIn("_smoke_deepseek()", source)
        self.assertIn("_smoke_open_meteo()", source)
        self.assertIn("_smoke_amap_route()", source)
        self.assertIn("_smoke_amap_poi()", source)
        self.assertNotIn("_smoke_open_charge_map()", source)
        self.assertNotIn("_smoke_baidu_map()", source)
        self.assertNotIn("OpenChargeMap", source)
        self.assertNotIn("BaiduMapProvider", source)


if __name__ == "__main__":
    unittest.main()

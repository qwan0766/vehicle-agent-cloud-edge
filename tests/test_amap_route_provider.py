import unittest

from providers.amap_route_provider import AmapRouteProvider


class TestAmapRouteProvider(unittest.TestCase):
    def test_builds_driving_route_url(self):
        provider = AmapRouteProvider(api_key="amap-key")

        url = provider.build_driving_route_url("121.48,31.23", "121.50,31.25", preference="高速")

        self.assertIn("https://restapi.amap.com/v3/direction/driving", url)
        self.assertIn("key=amap-key", url)
        self.assertIn("origin=121.48%2C31.23", url)
        self.assertIn("destination=121.50%2C31.25", url)
        self.assertIn("strategy=10", url)

    def test_parses_route_summary(self):
        payload = {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "12800",
                        "duration": "1680",
                    }
                ]
            },
        }
        provider = AmapRouteProvider(api_key="amap-key", transport=lambda url, timeout: payload)

        route = provider.plan_route("121.48,31.23", "121.50,31.25", preference="高速")

        self.assertEqual(route.provider, "amap_route")
        self.assertEqual(route.distance_km, 12.8)
        self.assertEqual(route.duration_minutes, 28)
        self.assertEqual(route.strategy, "高速优先")


if __name__ == "__main__":
    unittest.main()

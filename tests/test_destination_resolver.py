import unittest

from providers.destination_resolver import (
    extract_destination_query,
    resolve_destination,
    resolve_destination_detail,
)


class FakeGeocoder:
    provider_name = "fake_geocode"

    def geocode(self, address):
        class Result:
            name = address
            gps = "121.49,31.24"

        return Result()


class TestDestinationResolver(unittest.TestCase):
    def test_resolves_nio_center_to_gps(self):
        self.assertEqual(resolve_destination("导航去蔚来中心"), "121.50,31.25")

    def test_keeps_explicit_gps(self):
        self.assertEqual(resolve_destination("121.50,31.25"), "121.50,31.25")

    def test_extracts_dynamic_navigation_query(self):
        self.assertEqual(extract_destination_query("导航去外滩"), "外滩")
        self.assertEqual(extract_destination_query("我要去上海虹桥站"), "上海虹桥站")

    def test_uses_geocoder_for_unknown_destination(self):
        result = resolve_destination_detail("导航去外滩", geocoder=FakeGeocoder())

        self.assertEqual(result.name, "外滩")
        self.assertEqual(result.gps, "121.49,31.24")
        self.assertEqual(result.source, "fake_geocode")

    def test_unknown_destination_requires_geocoder(self):
        with self.assertRaises(ValueError):
            resolve_destination("导航去外滩")


if __name__ == "__main__":
    unittest.main()

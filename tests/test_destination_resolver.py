import unittest

from providers.destination_resolver import resolve_destination


class TestDestinationResolver(unittest.TestCase):
    def test_resolves_nio_center_to_gps(self):
        self.assertEqual(resolve_destination("导航去蔚来中心"), "121.50,31.25")

    def test_keeps_explicit_gps(self):
        self.assertEqual(resolve_destination("121.50,31.25"), "121.50,31.25")


if __name__ == "__main__":
    unittest.main()

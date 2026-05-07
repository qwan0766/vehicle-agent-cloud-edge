import unittest

from web_demo.server import WebDemoHandler, parse_server_args


class TestWebServerConfig(unittest.TestCase):
    def test_parse_server_port_argument(self):
        args = parse_server_args(["--port", "8002"])

        self.assertEqual(args.port, 8002)
        self.assertEqual(args.host, "127.0.0.1")

    def test_provider_smoke_path_is_registered(self):
        self.assertIn("/api/provider-smoke", WebDemoHandler.POST_ROUTES)

    def test_vehicle_state_update_path_is_registered(self):
        self.assertIn("/api/vehicle-state", WebDemoHandler.POST_ROUTES)

    def test_acceptance_path_is_registered(self):
        self.assertIn("/api/acceptance", WebDemoHandler.GET_ROUTES)

    def test_vehicle_events_path_is_registered(self):
        self.assertIn("/api/vehicle-events", WebDemoHandler.GET_ROUTES)


if __name__ == "__main__":
    unittest.main()

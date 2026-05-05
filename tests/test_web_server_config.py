import unittest

from web_demo.server import parse_server_args


class TestWebServerConfig(unittest.TestCase):
    def test_parse_server_port_argument(self):
        args = parse_server_args(["--port", "8002"])

        self.assertEqual(args.port, 8002)
        self.assertEqual(args.host, "127.0.0.1")


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from config.env_loader import load_env_file


class TestEnvLoader(unittest.TestCase):
    def test_load_env_file_sets_missing_values(self):
        path = Path(".test_runtime") / "sample.env"
        path.parent.mkdir(exist_ok=True)
        path.write_text("DEEPSEEK_MODEL=deepseek-v4-flash\n", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            loaded = load_env_file(str(path))

            self.assertEqual(loaded["DEEPSEEK_MODEL"], "deepseek-v4-flash")
            self.assertEqual(os.environ["DEEPSEEK_MODEL"], "deepseek-v4-flash")

    def test_existing_env_value_wins(self):
        path = Path(".test_runtime") / "sample_existing.env"
        path.parent.mkdir(exist_ok=True)
        path.write_text("DEEPSEEK_MODEL=from-file\n", encoding="utf-8")

        with patch.dict(os.environ, {"DEEPSEEK_MODEL": "from-process"}, clear=True):
            loaded = load_env_file(str(path))

            self.assertEqual(loaded, {})
            self.assertEqual(os.environ["DEEPSEEK_MODEL"], "from-process")


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from csl_dotmatrix.config import DEFAULTS, load_settings, save_settings, validate


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(validate({}), DEFAULTS)

    def test_validation(self):
        for bad in ({'source': 'both'}, {'unit': 'K'}, {'interval': 10},
                    {'interval': -1}, {'interval': float('nan')}, {'sensor': 2},
                    {'extra': 42}):
            with self.assertRaises(ValueError):
                validate(bad)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': folder}):
                self.assertEqual(load_settings(), DEFAULTS)
                path = save_settings({'source': 'gpu', 'unit': 'F'})
                self.assertTrue(Path(path).exists())
                self.assertEqual(json.loads(path.read_text())['source'], 'gpu')
                self.assertEqual(load_settings()['unit'], 'F')


if __name__ == '__main__':
    unittest.main()

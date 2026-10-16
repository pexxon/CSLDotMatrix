import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from csl_dotmatrix import tray


class TestTray(unittest.TestCase):
    def test_switch_source_preserves_unit(self):
        with tempfile.TemporaryDirectory() as home:
            with patch('csl_dotmatrix.config.config_path', return_value=Path(home) / 'config.json'):
                with patch('csl_dotmatrix.tray.service_action') as service:
                    service.return_value.returncode = 0
                    self.assertTrue(tray.apply_choice('source', 'gpu'))
                    from csl_dotmatrix.config import load_settings
                    self.assertEqual(load_settings()['source'], 'gpu')
                    self.assertEqual(load_settings()['unit'], 'C')
                    self.assertFalse(tray.apply_choice('source', 'gpu'))
                    service.assert_called_once_with('try-restart')

    def test_unit_change(self):
        with tempfile.TemporaryDirectory() as home:
            with patch('csl_dotmatrix.config.config_path', return_value=Path(home) / 'config.json'):
                with patch('csl_dotmatrix.tray.service_action') as service:
                    service.return_value.returncode = 0
                    self.assertTrue(tray.apply_choice('unit', 'F'))
                    from csl_dotmatrix.config import load_settings
                    self.assertEqual(load_settings()['unit'], 'F')


if __name__ == '__main__':
    unittest.main()

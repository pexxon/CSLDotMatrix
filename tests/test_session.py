import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from csl_dotmatrix.config import DEFAULTS, load_settings, save_settings
from csl_dotmatrix.session import initialize_service


class SessionTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'config.json'
        config = patch('csl_dotmatrix.config.config_path', return_value=self.path)
        session = patch('csl_dotmatrix.session.config_path', return_value=self.path)
        config.start()
        session.start()
        self.addCleanup(config.stop)
        self.addCleanup(session.stop)

    @patch('csl_dotmatrix.session.systemctl')
    def test_fresh_install_starts_once(self, systemctl):
        systemctl.return_value = SimpleNamespace(returncode=0)
        self.assertTrue(initialize_service())
        self.assertEqual(load_settings(), DEFAULTS)
        self.assertFalse(initialize_service())
        systemctl.assert_called_once_with('enable', '--now')

    @patch('csl_dotmatrix.session.systemctl')
    def test_existing_settings_leave_service_choice_alone(self, systemctl):
        save_settings({'source': 'gpu', 'unit': 'F'})
        self.assertFalse(initialize_service())
        self.assertEqual(load_settings()['source'], 'gpu')
        systemctl.assert_not_called()

    @patch('csl_dotmatrix.session.systemctl')
    def test_failed_service_start_can_retry(self, systemctl):
        systemctl.return_value = SimpleNamespace(returncode=1, stderr='No user bus')
        with self.assertRaisesRegex(RuntimeError, 'No user bus'):
            initialize_service()
        self.assertFalse(self.path.exists())
        systemctl.return_value = SimpleNamespace(returncode=0)
        self.assertTrue(initialize_service())


if __name__ == '__main__':
    unittest.main()

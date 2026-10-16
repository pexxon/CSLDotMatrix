import tempfile
import unittest
from pathlib import Path

from csl_dotmatrix.sensors import choose_hwmon, get_reader


class SensorsTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def sensor(self, index, chip, label, value, pci=None):
        hw = self.root / f'hwmon{index}'
        hw.mkdir()
        (hw / 'name').write_text(chip)
        (hw / 'temp1_label').write_text(label)
        (hw / 'temp1_input').write_text(str(value))
        if pci:
            device = self.root / pci
            device.mkdir(exist_ok=True)
            (hw / 'device').symlink_to(device, target_is_directory=True)
        return hw

    def test_pci_selection_survives_hwmon_renumbering(self):
        first = self.sensor(0, 'amdgpu', 'edge', 44000, '0000:03:00.0')
        second = self.sensor(1, 'amdgpu', 'edge', 55000, '0000:0b:00.0')
        selector = 'pci:0000:0b:00.0/edge'
        reader, _ = get_reader('gpu', selector, self.root)
        self.assertEqual(reader(), 55)
        first.rename(self.root / 'hwmon9')
        second.rename(self.root / 'hwmon8')
        self.assertEqual(choose_hwmon('gpu', self.root, selector).read_c(), 55)

    def test_multiple_gpus_warn_without_changing_existing_default(self):
        self.sensor(0, 'amdgpu', 'edge', 44000, '0000:03:00.0')
        self.sensor(1, 'amdgpu', 'edge', 55000, '0000:0b:00.0')
        with self.assertWarnsRegex(RuntimeWarning, 'Multiple GPU sensors'):
            self.assertEqual(choose_hwmon('gpu', self.root).read_c(), 44)

    def test_chip_label_cpu_selection(self):
        self.sensor(4, 'k10temp', 'Tctl', 61000)
        sensor = choose_hwmon('cpu', self.root, 'hwmon:k10temp/Tctl')
        self.assertEqual(sensor.read_c(), 61)
        self.assertEqual(sensor.selector, 'hwmon:k10temp/Tctl')

    def test_ambiguous_and_missing_selectors_fail(self):
        self.sensor(0, 'amdgpu', 'edge', 44000)
        self.sensor(1, 'amdgpu', 'edge', 55000)
        for selector in ('hwmon:amdgpu/edge', 'pci:0000:01:00.0/edge', 'pci:missing'):
            with self.subTest(selector=selector), self.assertRaises(RuntimeError):
                choose_hwmon('gpu', self.root, selector)

    def test_explicit_file_path_remains_supported(self):
        hw = self.sensor(0, 'k10temp', 'Tctl', 61000)
        self.assertEqual(choose_hwmon('cpu', self.root, str(hw / 'temp1_input')).read_c(), 61)

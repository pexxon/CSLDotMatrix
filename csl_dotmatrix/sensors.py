"""Linux hwmon discovery (and NVIDIA GPU support)."""
from dataclasses import dataclass
from pathlib import Path
import subprocess
import re
import warnings

HWMON_ROOT = Path('/sys/class/hwmon')

@dataclass(frozen=True)
class Sensor:
    kind: str
    name: str
    label: str
    path: Path
    device: str = ''

    def read_c(self) -> float:
        return int(self.path.read_text().strip()) / 1000.0

    @property
    def selector(self):
        """Identify the chip/channel without depending on a hwmonN index."""
        return (f'pci:{self.device}/{self.label}' if self.device
                else f'hwmon:{self.name}/{self.label}')


def all_sensors(root=HWMON_ROOT):
    found = []
    for hw in sorted(root.glob('hwmon*')):
        try:
            chip = (hw / 'name').read_text().strip()
        except OSError:
            continue
        for temp_path in sorted(hw.glob('temp*_input')):
            label_file = temp_path.with_name(temp_path.name.replace('_input', '_label'))
            try:
                label = label_file.read_text().strip() if label_file.exists() else temp_path.stem
                device = (hw / 'device').resolve().name
                if not re.fullmatch(r'[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]', device):
                    device = ''
                sensor = Sensor('hwmon', chip, label, temp_path, device.lower())
                val = sensor.read_c()
                if -20 <= val <= 130:
                    found.append(sensor)
            except (OSError, ValueError):
                continue
    return found


def score_cpu(sensor):
    chip = sensor.name.lower()
    label = sensor.label.lower()
    if chip == 'k10temp':
        return 120 if label == 'tdie' else 110 if label == 'tctl' else 80
    if chip == 'coretemp':
        return 120 if 'package id' in label else 90 if 'core ' in label else 70
    if chip in ('zenpower', 'zenpower3'):
        return 115 if 'tdie' in label else 85
    return -1


def score_gpu(sensor):
    chip = sensor.name.lower()
    if chip == 'amdgpu':
        return 110 if 'edge' in sensor.label.lower() else 100
    if chip in ('i915', 'xe', 'nouveau'):
        return 90
    return -1


def choose_hwmon(source, root=HWMON_ROOT, explicit_path=None):
    if explicit_path:
        explicit_path = str(explicit_path)
        if explicit_path.startswith(('pci:', 'hwmon:')):
            kind, _, identity = explicit_path.partition(':')
            chip, separator, label = identity.partition('/')
            if not separator or not chip or not label:
                raise RuntimeError('Sensor selector must be pci:ADDRESS/LABEL or hwmon:CHIP/LABEL')
            matches = [s for s in all_sensors(root)
                       if (s.device == chip.lower() if kind == 'pci' else s.name == chip)
                       and s.label == label]
            if len(matches) != 1:
                raise RuntimeError(f'Sensor selector {explicit_path!r} matched {len(matches)} sensors; '
                                   'use --list-sensors and choose a unique selector or path')
            return matches[0]
        p = Path(explicit_path)
        if not p.is_file() or not p.name.startswith('temp') or not p.name.endswith('_input'):
            raise RuntimeError('Explicit sensor must point to a temp*_input file')
        return Sensor('hwmon', 'manual', p.name, p)
    ranked = sorted(((score_cpu(s) if source == 'cpu' else score_gpu(s), s)
                     for s in all_sensors(root)), key=lambda x: x[0], reverse=True)
    if ranked and ranked[0][0] >= 0:
        if source == 'gpu':
            devices = {s.device or str(s.path.parent.resolve())
                       for score, s in ranked if score >= 0}
            if len(devices) > 1:
                warnings.warn(f'Multiple GPU sensors found; automatically selected {ranked[0][1].selector}. '
                              'Use --sensor with a stable pci:ADDRESS/LABEL selector to choose a GPU.',
                              RuntimeWarning, stacklevel=2)
        return ranked[0][1]
    raise RuntimeError(f'No confidently identifiable {source.upper()} hwmon sensor. '
                       'Use --list-sensors and --sensor PATH.')


def read_nvidia_gpu() -> float:
    result = subprocess.run(['nvidia-smi', '--query-gpu=temperature.gpu',
                             '--format=csv,noheader,nounits', '-i', '0'],
                            capture_output=True, text=True, timeout=4, check=True)
    return float(result.stdout.splitlines()[0].strip())


def get_reader(source, sensor_path=None, root=HWMON_ROOT):
    if sensor_path or source == 'cpu':
        sensor = choose_hwmon(source, root, sensor_path)
        return sensor.read_c, f'{sensor.name}: {sensor.label} ({sensor.path})'
    # NVIDIA usually exposes its temperature through nvidia-smi, not hwmon.
    try:
        read_nvidia_gpu()
        return read_nvidia_gpu, 'NVIDIA GPU 0 (nvidia-smi)'
    except (FileNotFoundError, subprocess.SubprocessError, ValueError, IndexError):
        sensor = choose_hwmon('gpu', root)
        return sensor.read_c, f'{sensor.name}: {sensor.label} ({sensor.path})'

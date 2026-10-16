"""Shared settings for the CLI, background service and desktop settings window."""
import json
import os
from pathlib import Path

DEFAULTS = {'source': 'cpu', 'unit': 'C', 'interval': 1.0, 'sensor': ''}


def config_path():
    base = os.environ.get('XDG_CONFIG_HOME')
    return (Path(base) if base else Path.home() / '.config') / 'csl-dotmatrix' / 'config.json'


def validate(settings):
    if not isinstance(settings, dict):
        raise ValueError('Settings must be a JSON object')
    result = dict(DEFAULTS)
    for key in settings:
        if key not in DEFAULTS:
            raise ValueError(f'Unknown setting: {key}')
    result.update(settings)
    if result['source'] not in ('cpu', 'gpu'):
        raise ValueError('source must be cpu or gpu')
    if result['unit'] not in ('C', 'F'):
        raise ValueError('unit must be C or F')
    if isinstance(result['interval'], bool) or not isinstance(result['interval'], (int, float)) or not 0.2 <= result['interval'] <= 9.0:
        raise ValueError('interval must be between 0.2 and 9 seconds')
    if not isinstance(result['sensor'], str):
        raise ValueError('sensor must be a path string')
    return result


def load_settings():
    path = config_path()
    if not path.exists():
        return dict(DEFAULTS)
    return validate(json.loads(path.read_text(encoding='utf-8')))


def save_settings(settings):
    data = validate(settings)
    path = config_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    try:
        with temp.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return path

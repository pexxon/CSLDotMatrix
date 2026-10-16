"""Desktop session startup for the system-wide package."""
import subprocess
import sys

from .config import config_path, load_settings, save_settings
from .gui import systemctl


def initialize_service():
    """Enable defaults once; an existing config preserves the user's choices."""
    if config_path().exists():
        return False
    settings = load_settings()
    result = systemctl('enable', '--now')
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Unable to start display service')
    save_settings(settings)
    return True


def main():
    try:
        initialize_service()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'CSL DotMatrix startup: {exc}', file=sys.stderr)
    from .tray import run
    return run()


if __name__ == '__main__':
    raise SystemExit(main())

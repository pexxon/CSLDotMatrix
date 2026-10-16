"""Command line interface for the CSL DotMatrix display."""
import argparse
import math
import signal
import sys
import time
from .protocol import encode_temperature, find_device
from .sensors import all_sensors, get_reader
from .config import load_settings


def cli(argv=None):
    try:
        settings = load_settings()
    except (OSError, ValueError) as exc:
        print(f'Configuration error: {exc}', file=sys.stderr)
        return 5
    parser = argparse.ArgumentParser(description='Linux controller for CSL DotMatrix AIO')
    parser.add_argument('--source', choices=('cpu', 'gpu'), default=settings['source'])
    parser.add_argument('--unit', choices=('C', 'F'), default=settings['unit'], type=str.upper)
    parser.add_argument('--sensor', metavar='PATH', default=settings['sensor'] or None, help='Explicit /sys/class/hwmon/.../temp*_input')
    parser.add_argument('--interval', type=float, default=settings['interval'], help='Seconds between updates (default: 1)')
    parser.add_argument('--list-sensors', action='store_true')
    parser.add_argument('--once', action='store_true', help='Send once and exit (display times out afterward)')
    parser.add_argument('--dry-run', action='store_true', help='Read sensors, print packet, do not open HID')
    parser.add_argument('--strict-range', action='store_true', help='Do not send values outside 0..99')
    args = parser.parse_args(argv)
    if args.list_sensors:
        for s in all_sensors():
            try:
                print(f'{s.name:14} {s.label:22} {s.read_c():6.1f}°C  {s.path}')
            except (OSError, ValueError):
                pass
        return 0
    if not 0.2 <= args.interval <= 9:
        parser.error('--interval must be 0.2..9 seconds (display times out around 12s)')
    try:
        reader, description = get_reader(args.source, args.sensor)
    except Exception as e:
        print(f'Sensor error: {e}', file=sys.stderr)
        return 1
    print(f'Source: {args.source.upper()} / {description}; unit: °{args.unit}', flush=True)
    device = None
    if not args.dry_run:
        try:
            import hid
            target = find_device(hid)
            device = hid.device()
            device.open_path(target['path'])
            print(f'HID open: {target["path"]!r}', flush=True)
        except (ImportError, OSError, RuntimeError) as e:
            print(f'HID error: {e}. Check permissions and python hidapi installation.', file=sys.stderr)
            return 2
    stopping = False
    def handle_signal(_signum, _frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    try:
        while not stopping:
            try:
                celsius = reader()
                measured = celsius * 9 / 5 + 32 if args.unit == 'F' else celsius
                if not math.isfinite(measured):
                    raise ValueError('Invalid sensor value')
                rounded = round(measured)
                if rounded < 0 or rounded > 99:
                    print(f'Out of range: {rounded}°{args.unit} (two-digit display only)',
                          file=sys.stderr, flush=True)
                    if args.strict_range:
                        if args.once:
                            return 3
                        time.sleep(args.interval)
                        continue
                    shown = min(99, max(0, rounded))
                else:
                    shown = rounded
                packet = encode_temperature(shown)
                if device:
                    written = device.send_feature_report(packet)
                    if written != len(packet):
                        raise OSError(f'Incomplete HID report: {written}/{len(packet)} bytes')
                print(f'{celsius:.1f}°C => {shown:02}°{args.unit}' +
                      (' (DRY RUN: ' + packet.hex(' ') + ')' if args.dry_run else ''), flush=True)
            except (OSError, ValueError, IndexError) as e:
                print(f'Update failed: {e}', file=sys.stderr, flush=True)
                if args.once:
                    return 4
            if args.once:
                break
            time.sleep(args.interval)
    finally:
        if device is not None:
            device.close()
    return 0

if __name__ == '__main__':
    sys.exit(cli())

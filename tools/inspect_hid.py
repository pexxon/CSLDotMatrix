#!/usr/bin/env python3
"""Inspect cached HID descriptors through sysfs; never open hidraw or send reports."""
import argparse
import json
from pathlib import Path


def describe_reports(data):
    """Count HID report bits using short-item globals, including PUSH/POP."""
    state = {'size': 0, 'count': 0, 'id': 0}
    stack = []
    reports = {}
    offset = 0
    while offset < len(data):
        prefix = data[offset]
        offset += 1
        if prefix == 0xfe:
            if offset + 2 > len(data):
                raise ValueError('Truncated HID long-item header')
            length = data[offset]
            offset += 2
            if offset + length > len(data):
                raise ValueError('Truncated HID long item')
            offset += length
            continue
        length = (0, 1, 2, 4)[prefix & 3]
        if offset + length > len(data):
            raise ValueError('Truncated HID short item')
        value = int.from_bytes(data[offset:offset + length], 'little')
        offset += length
        kind, tag = (prefix >> 2) & 3, prefix >> 4
        if kind == 1:
            if tag in (7, 8, 9):
                state[{7: 'size', 8: 'id', 9: 'count'}[tag]] = value
            elif tag == 10:
                stack.append(dict(state))
            elif tag == 11:
                if not stack:
                    raise ValueError('HID global POP without PUSH')
                state = stack.pop()
        elif kind == 0 and tag in (8, 9, 11):
            key = (state['id'], {8: 'input', 9: 'output', 11: 'feature'}[tag])
            reports[key] = reports.get(key, 0) + state['size'] * state['count']
    return [dict(report_id=report_id, kind=kind, bits=bits,
                 payload_bytes=(bits + 7) // 8,
                 report_bytes=(bits + 7) // 8 + bool(report_id))
            for (report_id, kind), bits in sorted(reports.items())]


def inspect_sysfs(root):
    devices = []
    for node in sorted(root.glob('hidraw*')):
        device = node / 'device'
        try:
            info = dict(line.split('=', 1) for line in
                        (device / 'uevent').read_text().splitlines() if '=' in line)
            hid_id = info.get('HID_ID', '').split(':')
            if len(hid_id) != 3 or (int(hid_id[1], 16), int(hid_id[2], 16)) != (0x1a2c, 0x434d):
                continue
            data = (device / 'report_descriptor').read_bytes()
            interface = None
            for parent in device.resolve().parents:
                number = parent / 'bInterfaceNumber'
                if number.is_file():
                    interface = int(number.read_text().strip(), 16)
                    break
            devices.append(dict(hidraw=node.name, interface=interface,
                                name=info.get('HID_NAME'), descriptor_hex=data.hex(' '),
                                reports=describe_reports(data)))
        except OSError as exc:
            devices.append(dict(hidraw=node.name, error=str(exc)))
    return devices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--descriptor', type=Path, help='Decode a saved binary report descriptor')
    parser.add_argument('--sysfs', type=Path, default=Path('/sys/class/hidraw'))
    args = parser.parse_args()
    try:
        result = (describe_reports(args.descriptor.read_bytes()) if args.descriptor
                  else inspect_sysfs(args.sysfs))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

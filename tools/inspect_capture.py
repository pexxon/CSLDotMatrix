#!/usr/bin/env python3
"""Summarize only enumerated CSL display traffic in USBPcap pcapng files."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import struct


def packets(data):
    """Decode enhanced packet blocks and USBPcap's packed 27-byte base header."""
    offset, section, frame = 0, -1, 0
    endian = '<'
    interfaces = []
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError('Truncated pcapng block')
        if data[offset:offset + 4] == b'\x0a\x0d\x0d\x0a':
            magic = data[offset + 8:offset + 12]
            if magic not in (b'\x4d\x3c\x2b\x1a', b'\x1a\x2b\x3c\x4d'):
                raise ValueError('Invalid pcapng byte-order magic')
            endian = '<' if magic[0] == 0x4d else '>'
            section += 1
            interfaces = []
        elif section < 0:
            raise ValueError('Expected pcapng section header')
        kind, length = struct.unpack_from(endian + 'II', data, offset)
        if length < 12 or length % 4 or offset + length > len(data):
            raise ValueError('Invalid pcapng block length')
        if struct.unpack_from(endian + 'I', data, offset + length - 4)[0] != length:
            raise ValueError('pcapng block length trailer mismatch')
        body = data[offset + 8:offset + length - 4]
        if kind == 1:
            if len(body) < 8:
                raise ValueError('Truncated pcapng interface')
            resolution, time_offset, pos = 1e-6, 0, 8
            while pos + 4 <= len(body):
                code, size = struct.unpack_from(endian + 'HH', body, pos)
                pos += 4
                value = body[pos:pos + size]
                if len(value) != size:
                    raise ValueError('Truncated pcapng interface option')
                pos += (size + 3) & ~3
                if code == 9 and size == 1:
                    resolution = (2 ** -(value[0] & 127) if value[0] & 128
                                  else 10 ** -value[0])
                elif code == 14 and size == 8:
                    time_offset = struct.unpack(endian + 'q', value)[0]
            interfaces.append((struct.unpack_from(endian + 'H', body)[0], resolution, time_offset))
        elif kind in (2, 3):
            raise ValueError('Only enhanced packet blocks are supported; convert this capture first')
        elif kind == 6:
            frame += 1
            if len(body) < 20:
                raise ValueError('Truncated enhanced packet block')
            interface, high, low, captured, original = struct.unpack_from(endian + 'IIIII', body)
            if interface >= len(interfaces) or captured > len(body) - 20:
                raise ValueError('Invalid enhanced packet interface or length')
            link, resolution, time_offset = interfaces[interface]
            if link == 249:
                packet = body[20:20 + captured]
                if captured != original or len(packet) < 27:
                    raise ValueError('Truncated USBPcap packet')
                header, irp, status, _, info, bus, device, endpoint, transfer, size = struct.unpack_from(
                    '<HQIHBHHBBI', packet)
                if header < 27 or header + size > len(packet):
                    raise ValueError('Invalid USBPcap header or data length')
                yield dict(frame=frame, key=(section, interface, bus, device),
                           time=((high << 32) | low) * resolution + time_offset,
                           irp=irp, status=status, info=info, endpoint=endpoint,
                           transfer=transfer,
                           stage=packet[27] if transfer == 2 and header >= 28 else None,
                           payload=packet[header:header + size])
        offset += length


def summarize(data):
    pending = {}
    target = set()
    requests = []
    all_packets = list(packets(data))
    completed = {}
    for packet in all_packets:
        if packet['transfer'] != 2:
            continue
        token = (packet['key'], packet['irp'])
        payload = packet['payload']
        if packet['stage'] == 0 and len(payload) >= 8:
            setup = struct.unpack_from('<BBHHH', payload)
            request = dict(packet, setup=setup, report=payload[8:])
            pending[token] = request
            requests.append(request)
        elif packet['stage'] == 3:
            request = pending.pop(token, None)
            if request:
                completed[request['frame']] = packet['status']
                if request['setup'][:3] == (0x80, 6, 0x100) and len(payload) >= 18:
                    if payload[:2] == b'\x12\x01' and struct.unpack_from('<HH', payload, 8) == (0x1a2c, 0x434d):
                        target.add(packet['key'])
        elif packet['stage'] in (1, 2):
            raise ValueError('Legacy multi-stage USBPcap control records are not supported')
    if not target:
        raise ValueError('No CSL 1a2c:434d device descriptor found; capture enumeration first')
    display = [p for p in requests if p['key'] in target
               and p['setup'][:4] == (0x21, 9, 0x307, 1)]
    counts = Counter(p['setup'] for p in requests if p['key'] in target)
    sequence = []
    for packet in display:
        report = packet['report']
        numeric = (len(report) in (64, 65) and report[:3] == b'\x07\xff\xff'
                   and report[3] <= 1 and report[4] <= 9 and report[5] <= 9 and not any(report[6:]))
        sequence.append(dict(frame=packet['frame'],
                             seconds=round(packet['time'] - display[0]['time'], 6),
                             prefix=report[:6].hex(' '), bytes=len(report),
                             wLength=packet['setup'][4],
                             numeric_candidate=100 * report[3] + 10 * report[4] + report[5] if numeric else None,
                             nonzero_tail=any(report[6:]),
                             completion_status=completed.get(packet['frame'])))
    gaps = [b['time'] - a['time'] for a, b in zip(display, display[1:])]
    target_packets = [p for p in all_packets if p['key'] in target]
    return dict(sha256=hashlib.sha256(data).hexdigest(), usb_packets=len(all_packets),
                target_devices=[dict(section=k[0], capture_interface=k[1], bus=k[2], device=k[3])
                                for k in sorted(target)],
                target_setups=[dict(bmRequestType=k[0], bRequest=k[1], wValue=k[2],
                                    wIndex=k[3], wLength=k[4], count=count)
                               for k, count in sorted(counts.items())],
                target_noncontrol_packets=sum(p['transfer'] != 2 for p in target_packets),
                display_reports=sequence,
                interval_seconds=dict(min=min(gaps), median=statistics.median(gaps), max=max(gaps)) if gaps else None,
                limitation='Numeric candidates are a static software interpretation, not proof of physical rendering.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    try:
        result = summarize(args.capture.read_bytes())
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(1, f'Capture analysis failed: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

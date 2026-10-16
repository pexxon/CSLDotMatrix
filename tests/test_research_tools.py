import unittest
import json
import struct

from tools.inspect_capture import summarize
from tools.inspect_hid import describe_reports
from tools.inspect_windows import direct_calls, parse_functions


class ResearchToolsTest(unittest.TestCase):
    def test_vendor_report_counts_id_once(self):
        descriptor = bytes.fromhex(
            '06 01 ff 09 01 a1 01 85 07 09 03 15 00 26 ff 00 '
            '75 08 95 3f b1 02 09 04 15 00 26 ff 00 75 08 95 3f 91 02 c0')
        reports = describe_reports(descriptor)
        self.assertEqual({r['kind'] for r in reports}, {'feature', 'output'})
        for report in reports:
            self.assertEqual(report['report_id'], 7)
            self.assertEqual(report['bits'], 504)
            self.assertEqual(report['report_bytes'], 64)

    def test_bitfields_and_global_stack(self):
        # Three data bits plus five constant bits comprise one unnumbered byte.
        reports = describe_reports(bytes.fromhex('75 01 95 03 a4 95 05 81 01 b4 81 02'))
        self.assertEqual(reports[0]['report_bytes'], 1)
        self.assertEqual(reports[0]['bits'], 8)

    def test_malformed_descriptors(self):
        for data in (b'\x76\x01', b'\xfe', b'\xfe\x03\x00\x01', b'\xb4'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                describe_reports(data)

    def test_pdb_offsets_are_decimal(self):
        symbols = ('0 | S_GPROC32 [size = 68] `DeviceMainDlg::Trd_SendData`\n'
                   'parent = 0, end = 5, addr = 0001:28784, code size = 375\n')
        functions = parse_functions(symbols, {'image_base': 0x400000,
                                              'sections': [{'rva': 0x1000}]})
        self.assertEqual(functions[0]['address'], 0x408070)
        calls = direct_calls('4081c6: e8 65 1f 00 00 call 0x40a130\n'
                             '4081d0: ff 15 bc 60 41 00 call dword ptr [0x4160bc]', functions)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['callers'], ['DeviceMainDlg::Trd_SendData'])
        self.assertEqual(calls[0]['target'], 0x40a130)


class CaptureTest(unittest.TestCase):
    def capture(self, endian='<'):
        def block(kind, body):
            body += bytes(-len(body) % 4)
            length = len(body) + 12
            return struct.pack(endian + 'II', kind, length) + body + struct.pack(endian + 'I', length)

        capture = block(0x0a0d0d0a, struct.pack(endian + 'IHHq', 0x1a2b3c4d, 1, 0, -1))
        capture += block(1, struct.pack(endian + 'HHI', 249, 0, 65535))

        def packet(stage, payload, timestamp, *, device=6, transfer=2, status=0):
            header = struct.pack('<HQIHBHHBBI', 28, 123, status, 0,
                                 int(stage == 3), 4, device, 0, transfer, len(payload))
            data = header + bytes([stage]) + payload
            return block(6, struct.pack(endian + 'IIIII', 0, 0, timestamp, len(data), len(data)) + data)

        setup = struct.pack('<BBHHH', 0x80, 6, 0x100, 0, 18)
        descriptor = bytes.fromhex('12 01 00 02 00 00 00 40 2c 1a 4d 43 00 01 01 02 00 01')
        capture += packet(0, setup, 0) + packet(3, descriptor, 100)
        setup = struct.pack('<BBHHH', 0x21, 9, 0x307, 1, 64)
        for timestamp, report, status in (
            (1000000, bytes.fromhex('07 ff ff 00 04 04') + bytes(58), 0),
            (2100000, bytes.fromhex('07 ff ff 01 01 01') + bytes(58), 1),
        ):
            # Reuse the same IRP: completions must pair with the current request.
            capture += packet(0, setup + report, timestamp)
            capture += packet(3, b'', timestamp + 100, status=status)
        capture += packet(0, b'unrelated keyboard payload', 2200000, device=8, transfer=1)
        return capture

    def test_filtered_reports_and_reused_irps(self):
        for endian in ('<', '>'):
            with self.subTest(endian=endian):
                summary = summarize(self.capture(endian))
                reports = summary['display_reports']
                self.assertEqual([p['numeric_candidate'] for p in reports], [44, 111])
                self.assertEqual([p['completion_status'] for p in reports], [0, 1])
                self.assertAlmostEqual(summary['interval_seconds']['median'], 1.1)
                self.assertNotIn('keyboard payload', json.dumps(summary))
                self.assertEqual(summary['target_noncontrol_packets'], 0)

    def test_truncated_capture_rejected(self):
        with self.assertRaises(ValueError):
            summarize(self.capture()[:-2])

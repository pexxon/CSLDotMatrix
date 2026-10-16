import unittest
from csl_dotmatrix.protocol import encode_temperature, find_device

class ProtocolTest(unittest.TestCase):
    def test_verified_44(self):
        packet = encode_temperature(44)
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[:6], bytes.fromhex('07 ff ff 00 04 04'))
        self.assertEqual(packet[6:], bytes(58))

    def test_limits(self):
        for n in (-1, 100, 101):
            with self.assertRaises(ValueError):
                encode_temperature(n)

    def test_zero_and_ninety_nine(self):
        self.assertEqual(encode_temperature(0)[4:6], b'\x00\x00')
        self.assertEqual(encode_temperature(99)[4:6], b'\x09\x09')

    def test_interface_filter(self):
        class FakeHid:
            @staticmethod
            def enumerate(*_args):
                return [
                    {'interface_number': 0, 'usage_page': 1, 'path': b'/dev/other'},
                    {'interface_number': 1, 'usage_page': 0xff01, 'path': b'/dev/csl'}
                ]
        self.assertEqual(find_device(FakeHid)['path'], b'/dev/csl')

if __name__ == '__main__':
    unittest.main()

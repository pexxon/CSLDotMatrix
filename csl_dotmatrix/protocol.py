"""Known-good subset of the CSL DotMatrix HID protocol."""
VID = 0x1A2C
PID = 0x434D
INTERFACE = 1
USAGE_PAGE = 0xFF01
REPORT_LENGTH = 64


def encode_temperature(value: int) -> bytes:
    """Encode a *displayed* two-digit integer; only 00..99 is verified."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 99:
        raise ValueError("Display protocol only supports verified values 00..99")
    return bytes([0x07, 0xFF, 0xFF, 0x00, value // 10, value % 10]) + bytes(REPORT_LENGTH - 6)


def find_device(hid):
    candidates = [d for d in hid.enumerate(VID, PID)
                  if d.get("interface_number") == INTERFACE
                  and d.get("usage_page") == USAGE_PAGE]
    if not candidates:
        raise RuntimeError("CSL controller not found (1a2c:434d, interface 1, usage 0xff01)")
    if len(candidates) > 1:
        raise RuntimeError("Multiple matching HID devices; refusing to choose arbitrarily")
    return candidates[0]

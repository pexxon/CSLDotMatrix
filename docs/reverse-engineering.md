# CSL Digital static analysis and the pixel-control question

Analysis date: 2026-10-16. No Windows executables were run and no new HID
commands were transmitted. This describes one Windows software build, not a
complete specification of the controller firmware.

## Findings

The inspected Windows application builds a numeric report, not a framebuffer.
There is strong static evidence that byte 3 is a **hundreds digit**. The
previously unexplained `07 FF FF 01 01 03` and `07 FF FF 01 01 01` prefixes
are consistent with **113** and **111** respectively. Their interpretation as
CPU/GPU or unit mode switches is not supported by this sender's code.

Physical rendering above 99 is still unverified. The Linux sender retains
its tested 00–99 range, clamping/strict-range behavior, and exact 64-byte packet.
No pixel-write, font-upload, or animation command has been established.

## Inputs and identity

Local references reside in `CSL DotMatrix Digital/CSL Digital/`. These proprietary
files are ignored by Git and excluded from release sources.

| File | SHA-256 |
| --- | --- |
| `CSL Digital.exe` | `ed058ec5f497d5c73b34a88a6e770e68ae393d858db1053fd0d454357584d2e5` |
| `DeviceDriver.pdb` | `2ebcc3f4d895a2268eaced497a161c83a742e8fde85dd54c55d666fce7ab2354` |
| `DeviceDriver.iobj` | `2da5045452e25b06dd3a39a0b7d0b0dcee6c50ec99f2ea8603de0d2b5421f01c` |

The EXE is x86 PE32 with image base `0x400000`. Its CodeView GUID
`AC7E8A2E-0804-4480-A4E5-EC051D1B3C7C`, age 2, matches the PDB. The embedded
software-version string is `1.0.1.1`. PDB offsets printed by llvm-pdbutil are
decimal; map them through the EXE's section RVAs rather than treating them as hex.

## Packet construction

| Function | Preferred virtual address | Length |
| --- | --- | --- |
| `DeviceMainDlg::Trd_SendData` | `0x408070` | 375 bytes |
| `DriverComm::SetDeviceData` | `0x40a130` | 202 bytes |
| `DriverComm::GetDeviceFWVersion` | `0x40a200` | 402 bytes |
| `hid_send_feature_report` | `0x40b620` | 153 bytes |

These are addresses in this particular EXE at its preferred image base.

`Trd_SendData` reads CPU/GPU temperatures from shared data. PDB class members
identify `this+0x36c` as `m_dev_type`, `this+0x370` as `m_temp_type`, and
`this+0x328` as `m_led_switch`. Source and unit selection occur on the host.
The unit-conversion branch uses floating-point constants 1.8 and 32; the
converted values are truncated to integers. The sender caps positive values at
199 (`0x408116`–`0x408126`). Its numeric-buffer construction is equivalent,
for ordinary nonnegative input, to:

```text
n = selected host-computed temperature, capped at 199
buffer[0:3] = 07 FF FF
buffer[3] = (n // 100) % 10
buffer[4] = (n // 10) % 10
buffer[5] = n % 10
remaining buffer bytes = 0
```

Evidence in the disassembly:

- `0x408144`, `0x408156`: write `07 FF FF`.
- `0x408164`–`0x40817b`: optimized division by 100, remainder by 10, store byte 3.
- `0x40817e`–`0x408197`: division by 10, remainder by 10, store byte 4.
- `0x408190`–`0x40819e`: subtract ten times the quotient, store byte 5.
- `0x4081ae`–`0x4081b4`: the LED-switch branch clears the three digit bytes.
  This is evidence of a zero-valued numeric report, not proof of a general
  screen-clear command.
- `0x4081c6`: calls `SetDeviceData`.
- `0x4081cb`–`0x4081d0`: sleeps 1000 ms after the send.

Static xrefs found one direct caller of `SetDeviceData`: `Trd_SendData`.
`hid_send_feature_report` has two direct callers: `SetDeviceData` and
`GetDeviceFWVersion`. A scan found no absolute pointers to the first two
send functions in this EXE. `HidD_SetFeature`'s function-pointer call at
`0x40b639` is inside the known HID wrapper. Indirect/dynamic calls and different
software or firmware versions are outside this result; this is not proof
that hidden firmware commands do not exist.

## Report length and descriptor

The local device was identified through sysfs as VID/PID `1a2c:434d`.
The vendor collection on interface 1 uses page `0xff01`, usage 1, report ID 7.
Its descriptor contains:

```text
06 01 FF 09 01 A1 01 85 07
09 03 15 00 26 FF 00 75 08 95 3F B1 02
09 04 15 00 26 FF 00 75 08 95 3F 91 02 C0
```

This declares both Feature and Output reports with 63 payload bytes plus
the report ID: **64 bytes in total**. It describes capacity, not pixel semantics.
The Output path is a possible research lead, but it is not evidence that
Output reports provide a framebuffer.

The Windows PDB declares 65-byte buffers (`LF_ARRAY 0x862e`). At `0x40a1a8`,
`SetDeviceData` passes length 65 to `hid_send_feature_report` and then
`HidD_SetFeature`; it copies 64 source bytes into a zero-padded 65-byte buffer.
The Linux packet length agrees with the descriptor and physical tests. Do not
copy the Windows API length into Linux without a capture and a separate test.

## Firmware query and updater lead

`GetDeviceFWVersion` builds a report starting `07 FD`, sends it, then attempts
Feature reads. It forms a version integer from response bytes 1 and 2.
This identifies a second command family in the application; its real-device
behavior has not been tested here and the Linux service does not send it.

The application embeds the update base URL:

```text
https://upgrade-1318931438.cos.ap-beijing.myqcloud.com/045i1/firmware/
```

It references a `version` resource and downloads a separately named
`FirmwareUpdateTool-%s.zip` / `.exe`. The firmware `version` URL returned
HTTP 404 during this investigation. No updater or MCU firmware image was
retrieved. GUI strings about lighting effects and startup animation occur in
shared language resources and do not establish device capabilities.

## Reproduce locally

Install Arch's LLVM tools if necessary (`llvm`), then run:

```sh
python3 tools/inspect_windows.py 'CSL DotMatrix Digital/CSL Digital' \
    --output /tmp/csl-analysis
python3 tools/inspect_hid.py
```

The Windows tool checks EXE/PDB identity, writes hashes, function addresses,
direct call sites, symbols, full disassembly, and packet-function excerpts.
The HID tool only reads sysfs metadata and cached report descriptors; it never
opens `/dev/hidraw*`. For a saved descriptor:

```sh
python3 tools/inspect_hid.py --descriptor /path/to/report-descriptor.bin
```

The original `csl-dotmatrix.pcapng` was subsequently supplied in the repository
root. It is ignored by Git because it also contains unrelated USB traffic.
Its SHA-256 is
`a1d1c31ae9998a93951e2c7c027b805fe89b4beb89590450e0c9ad882dccdf5d`.
An independent parser using the documented USBPcap format found:

- 18,088 USBPcap packet records across four capture interfaces.
- The matching device descriptor identifies `1a2c:434d` at capture interface 3,
  USB bus 4, address 6. These capture coordinates are not persistent IDs.
- 19 `SET_REPORT` requests: `bmRequestType=0x21`, request 9, `wValue=0x0307`,
  `wIndex=1`, **`wLength=64` and 64 captured report bytes**.
- Every report has prefix `07 FF FF`, three decimal digits, and an all-zero tail.
  Every matched completion status is zero (success).
- Numeric candidates, in order:
  `48, 47, 47, 46, 46, 45, 45, 45, 44, 44, 44, 113, 113, 113, 111, 111, 44, 44, 44`.
  45°C converts to 113°F; 44°C converts to 111°F under the Windows truncation.
  Together with the sender's code, this strongly supports numeric updates
  across a unit change, rather than separate mode packets. The capture alone
  does not show what the panel physically rendered.
- The display-write span is 20.551 seconds. Intervals range from 1.116 to
  1.158 seconds, with median 1.145 seconds.
- Other requests for this device are standard enumeration/configuration
  requests. No non-control packets, firmware-version queries, or other
  application commands for this device occur in this recording.

Reproduce the filtered summary with:

```sh
python3 tools/inspect_capture.py csl-dotmatrix.pcapng > /tmp/csl-capture-summary.json
```

This standard-library tool checks pcapng framing, byte order, timestamp
resolution, USBPcap headers, descriptor identity, report lengths, and request /
completion pairing (including reused IRP IDs). It summarizes only the identified
cooler; it does not export other devices' payloads. It requires enumeration and
modern USBPcap enhanced packet blocks; legacy multi-stage records are explicitly
rejected. The recording resolves the 64-byte wire length but cannot establish
why this Windows API implementation passed 65 bytes internally.

## What would establish individual-dot control?

1. Capture additional application actions, especially display toggle and the
   firmware-update check, limited to the identified cooler interface. The
   existing capture's numeric updates contain no pixel protocol.
2. Obtain the separate firmware updater or a firmware image. Inspect its
   transport routines, command dispatcher, digit-font tables, and LED-driver
   writes offline. Digit rendering in firmware does not imply the USB protocol
   exposes those underlying LED writes.
3. If no additional software is available, identify the MCU and LED driver from
   existing board documentation or photographs. This helps determine whether
   there is a writable framebuffer and a documented firmware-reading path.
4. Before any hardware experiment, document the exact candidate, its evidence,
   expected response, and recovery path. Stop the existing service before a
   deliberate single-sender experiment; do not probe random report IDs/opcodes
   or interrupt pump power.

With a proven frame-write command, animations could be produced by streaming
frames from Linux even without a firmware animation engine. No such command
has been found yet. The current evidence supports numbers rendered by the
controller; it cannot establish either availability or impossibility of custom
pixels.

Tool/format references: [LLVM llvm-pdbutil](https://llvm.org/docs/CommandGuide/llvm-pdbutil.html),
[USB HID specification](https://www.usb.org/sites/default/files/hid1_11.pdf),
[USBPcap capture format](https://desowin.org/usbpcap/captureformat.html).

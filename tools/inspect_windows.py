#!/usr/bin/env python3
"""Map CSL Digital's matching PDB functions to disassembly, entirely offline."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid

FUNCTIONS = (
    'DeviceMainDlg::Trd_SendData', 'DriverComm::SetDeviceData',
    'DriverComm::GetDeviceFWVersion', 'hid_send_feature_report',
    'hid_get_feature_report',
)


def pe_info(data):
    """Read the PE32 section map and CodeView identity without executing the file."""
    if data[:2] != b'MZ':
        raise ValueError('Not a PE executable')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE signature')
    machine, count = struct.unpack_from('<HH', data, pe + 4)
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    optional = pe + 24
    if machine != 0x14c or struct.unpack_from('<H', data, optional)[0] != 0x10b:
        raise ValueError('This analysis tool supports x86 PE32 only')
    base = struct.unpack_from('<I', data, optional + 28)[0]
    sections = []
    for index in range(count):
        entry = optional + optional_size + 40 * index
        name, virtual_size, rva, raw_size, raw = struct.unpack_from('<8sIIII', data, entry)
        sections.append(dict(name=name.rstrip(b'\0').decode('ascii'), rva=rva,
                             virtual_size=virtual_size, raw_size=raw_size, raw=raw))

    def file_offset(rva):
        for section in sections:
            if section['rva'] <= rva < section['rva'] + section['raw_size']:
                return section['raw'] + rva - section['rva']
        raise ValueError(f'Unmapped RVA {rva:#x}')

    debug_rva, debug_size = struct.unpack_from('<II', data, optional + 96 + 6 * 8)
    if not debug_rva:
        raise ValueError('No PE debug directory')
    debug = file_offset(debug_rva)
    for entry in range(debug, debug + debug_size, 28):
        debug_type, size, _, raw = struct.unpack_from('<IIII', data, entry + 12)
        if debug_type == 2 and data[raw:raw + 4] == b'RSDS' and size >= 24:
            return dict(image_base=base, sections=sections,
                        guid=str(uuid.UUID(bytes_le=data[raw + 4:raw + 20])).upper(),
                        age=struct.unpack_from('<I', data, raw + 20)[0])
    raise ValueError('No RSDS CodeView identity')


def parse_functions(symbols, info):
    pattern = (r'S_[GL]PROC32(?:_ID)?[^\n]*`([^`\n]+)`\n'
               r'[^\n]*addr = (\d+):(\d+), code size = (\d+)')
    result = []
    for match in re.finditer(pattern, symbols):
        name, section, offset, size = match.groups()
        # llvm-pdbutil's segment offsets and sizes are DECIMAL, not hex.
        index = int(section) - 1
        if not 0 <= index < len(info['sections']):
            continue
        address = info['image_base'] + info['sections'][index]['rva'] + int(offset)
        result.append(dict(name=name, address=address, size=int(size)))
    return sorted(result, key=lambda row: (row['address'], row['name']))


def direct_calls(disassembly, functions):
    result = []
    for line in disassembly.splitlines():
        match = re.match(r'\s*([0-9a-f]+):.*?\b(call|jmp)\s+0x([0-9a-f]+)\b', line)
        if not match:
            continue
        address, operation, target = match.groups()
        address, target = int(address, 16), int(target, 16)
        result.append(dict(address=address, operation=operation, target=target,
                           callers=[f['name'] for f in functions
                                    if f['address'] <= address < f['address'] + f['size']],
                           callees=[f['name'] for f in functions if f['address'] == target]))
    return result


def run(*args):
    return subprocess.run(args, text=True, capture_output=True, check=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Folder containing CSL Digital.exe and DeviceDriver.pdb')
    parser.add_argument('--output', type=Path, required=True, help='Private output directory, e.g. /tmp/csl-analysis')
    args = parser.parse_args()
    exe, pdb = args.directory / 'CSL Digital.exe', args.directory / 'DeviceDriver.pdb'
    try:
        info = pe_info(exe.read_bytes())
        summary = run('llvm-pdbutil', 'dump', '--summary', str(pdb))
        guid = re.search(r'GUID: \{([^}]+)\}', summary)
        age = re.search(r'^\s*Age: (\d+)', summary, re.M)
        if not guid or not age or (guid[1].upper(), int(age[1])) != (info['guid'], info['age']):
            raise ValueError('EXE/PDB GUID or age mismatch; refusing to map symbols')
        symbols = run('llvm-pdbutil', 'dump', '--symbols', '--jmc', str(pdb))
        disassembly = run('llvm-objdump', '-d', '--x86-asm-syntax=intel', str(exe))
        functions = parse_functions(symbols, info)
        if not functions:
            raise ValueError('No function symbols parsed; check the LLVM output format')
        calls = direct_calls(disassembly, functions)
        selected = [f for f in functions if f['name'] in FUNCTIONS]
        if len({f['name'] for f in selected}) != len(FUNCTIONS):
            raise ValueError('Expected CSL functions missing; inspect this software version manually')
        report = dict(pe=info, sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in (exe, pdb)},
                      functions=selected,
                      direct_calls=[c for c in calls if set(c['callees']) & set(FUNCTIONS)],
                      limitation='Direct branches only; indirect calls and firmware behavior need separate analysis.')
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
        (args.output / 'symbols.txt').write_text(symbols)
        (args.output / 'disassembly.txt').write_text(disassembly)
        excerpts = []
        for function in selected:
            excerpts.append(f"\n{function['name']} @ {function['address']:#x}\n")
            for line in disassembly.splitlines():
                match = re.match(r'\s*([0-9a-f]+):', line)
                if match and function['address'] <= int(match[1], 16) < function['address'] + function['size']:
                    excerpts.append(line + '\n')
        (args.output / 'packet-functions.txt').write_text(''.join(excerpts))
    except (OSError, ValueError, struct.error, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Analysis failed: {exc}\n')
    print(f'PDB identity matched. Wrote offline analysis to {args.output}')


if __name__ == '__main__':
    main()

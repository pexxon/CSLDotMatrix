#!/usr/bin/env python3
"""Generate a source asset and matching Arch metadata for the exact checkout."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys


def validate_version(version, package_version, tag=None):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Release version must have the form MAJOR.MINOR.PATCH')
    if package_version != version:
        raise ValueError(f'PKGBUILD version {package_version!r} does not match project version {version!r}')
    if tag is not None and tag != f'v{version}':
        raise ValueError(f'Tag {tag!r} must match project version v{version}')


def package_metadata(template, version, checksum, tag=None):
    match = re.search(r'^pkgver=([^\n]+)$', template, re.M)
    if not match:
        raise ValueError('PKGBUILD pkgver missing')
    validate_version(version, match[1], tag)
    if not re.fullmatch(r'[0-9a-f]{64}', checksum):
        raise ValueError('Expected a SHA-256 checksum')
    result, count = re.subn(r"^sha256sums=\('[^']*'\)$",
                            f"sha256sums=('{checksum}')", template, flags=re.M)
    if count != 1:
        raise ValueError('Expected exactly one source checksum in PKGBUILD')
    return result


def main():
    import tomllib  # Release tooling uses Python 3.11+; the app still supports 3.9+.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--tag', help='Require this tag to match the project version')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
    template = (root / 'packaging/aur/PKGBUILD').read_text()
    # Reject wrong tags/versions before creating any release files.
    package_metadata(template, version, '0' * 64, args.tag)
    subprocess.run([sys.executable, str(root / 'tools/make_release.py'),
                    '--output', str(output)], check=True)
    archive = output / f'csldotmatrix-{version}.tar.gz'
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / 'PKGBUILD').write_text(package_metadata(template, version, checksum, args.tag))
    result = subprocess.run(['makepkg', '--printsrcinfo'], cwd=output,
                            text=True, capture_output=True, check=True)
    (output / '.SRCINFO').write_text(result.stdout)
    print(f'Prepared source archive, PKGBUILD, and .SRCINFO in {output}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build a reproducible source asset, excluding proprietary files and package metadata."""
import argparse
import gzip
import hashlib
from pathlib import Path
import tarfile
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
    files = []
    for folder in ('csl_dotmatrix', 'tests', 'desktop', 'systemd', 'udev', 'tools', 'docs'):
        files.extend(p for p in (root / folder).rglob('*')
                     if p.is_file() and not p.is_symlink()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files.extend(root / name for name in (
        'pyproject.toml', 'README.md', 'LICENSE', 'AGENTS.md', 'install.sh',
        'uninstall.sh', 'csl-dotmatrix', 'csl-dotmatrix-settings', 'csl-dotmatrix-tray',
        'packaging/aur/README.md'))
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f'csldotmatrix-{version}.tar.gz'
    with archive.open('wb') as output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as tar:
                for path in sorted(files):
                    name = f'CSLDotMatrix-{version}/{path.relative_to(root)}'
                    info = tar.gettarinfo(str(path), arcname=name)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    info.mode = 0o755 if info.mode & 0o111 else 0o644
                    with path.open('rb') as source:
                        tar.addfile(info, source)
    print(hashlib.sha256(archive.read_bytes()).hexdigest(), archive)


if __name__ == '__main__':
    main()

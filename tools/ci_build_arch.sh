#!/bin/bash
# Run as an unprivileged user with Arch build/runtime dependencies installed.
set -euo pipefail
PROJECT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

arguments=(--output "$PROJECT_DIR/dist")
if [[ -n ${RELEASE_TAG:-} ]]; then
    arguments+=(--tag "$RELEASE_TAG")
fi
python tools/prepare_package.py "${arguments[@]}"
desktop-file-validate desktop/*.desktop

cd dist
makepkg --cleanbuild --force --noconfirm
mapfile -t expected_packages < <(makepkg --packagelist)
packages=()
for candidate in "${expected_packages[@]}"; do
    # Arch also lists a possible -debug package even when no ELF code creates it.
    if [[ -f "$candidate" ]]; then
        packages+=("$candidate")
    fi
done
if (( ${#packages[@]} != 1 )); then
    printf 'Expected exactly one built package\n' >&2
    exit 1
fi
package_file=${packages[0]}
namcap PKGBUILD "$package_file" | tee namcap.log
if grep -q ' E: ' namcap.log; then
    printf 'namcap reported errors; see namcap.log\n' >&2
    exit 1
fi

# Exercise the installed entry points from outside the source checkout.
smoke_dir=$(mktemp -d)
trap 'rm -rf "$smoke_dir"' EXIT
bsdtar -xf "$package_file" -C "$smoke_dir"
printf '44000\n' > "$smoke_dir/temp1_input"
site_packages=$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
for command in csldotmatrix csl-dotmatrix; do
    result=$(cd "$smoke_dir" && \
        PYTHONPATH="$smoke_dir$site_packages" XDG_CONFIG_HOME="$smoke_dir/config" \
        "$smoke_dir/usr/bin/$command" --source cpu --unit C --dry-run --once \
        --sensor "$smoke_dir/temp1_input")
    printf '%s\n' "$result"
    case "$result" in
        *'44.0°C => 44°C'*) ;;
        *) printf 'Installed CLI smoke test failed\n' >&2; exit 1 ;;
    esac
done
package_name=$(basename -- "$package_file")
if [[ "$package_file" != "$PWD/$package_name" && "$package_file" != "$package_name" ]]; then
    cp -- "$package_file" "$package_name"
fi
source_archive=$(python -c 'import tomllib; from pathlib import Path; print("csldotmatrix-" + tomllib.loads(Path("../pyproject.toml").read_text())["project"]["version"] + ".tar.gz")')
sha256sum "$package_name" "$source_archive" PKGBUILD .SRCINFO namcap.log > SHA256SUMS
sha256sum --check SHA256SUMS

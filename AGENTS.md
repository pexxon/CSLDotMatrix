# Repository guidance

## Project and layout

This is an unofficial Linux controller for the CSL DotMatrix aRGB 240 mm AIO
temperature display. It uses Python 3.9+, Linux hwmon, hidapi, and optional
PySide6 desktop interfaces. `pyproject.toml` defines setuptools wheel packaging
and console entry points; development can also run directly from the checkout.

- `csl_dotmatrix/__main__.py`: CLI, config overrides, sensor reads, unit
  conversion, range handling, signals, and the periodic HID writer.
- `csl_dotmatrix/protocol.py`: verified packet encoding and HID device selection.
- `csl_dotmatrix/sensors.py`: hwmon discovery/ranking and NVIDIA GPU 0 through
  `nvidia-smi`; explicit paths and stable `pci:ADDRESS/LABEL` or
  `hwmon:CHIP/LABEL` selectors override automatic selection.
- `csl_dotmatrix/config.py`: shared defaults, validation, and atomic JSON saves.
- `csl_dotmatrix/gui.py`: PySide6 settings window and systemd user service control.
- `csl_dotmatrix/tray.py`: PySide6 tray, single-instance lock, tray-host startup
  retry, and source/unit choices. Changes use `try-restart` on the service.
- `csl_dotmatrix/session.py`: packaged desktop startup; enables defaults only
  when no config exists, then runs the tray. Preserve existing service choices.
- `csl-dotmatrix`, `csl-dotmatrix-settings`, `csl-dotmatrix-tray`: entry scripts.
- `install.sh`, `uninstall.sh`: manual per-user installation/removal.
- `systemd/`, `udev/`, `desktop/`: Linux integration files.
- `packaging/aur/`: `csldotmatrix` release PKGBUILD, generated `.SRCINFO`, and
  publication instructions. The referenced release tag and exact source asset
  must be published before remote builds work. Generate the asset with
  `python3 tools/make_release.py`; refresh the SHA-256 and `.SRCINFO` after source edits.
- `.github/workflows/build.yml`: Python tests, containerized Arch builds,
  downloadable artifacts, and GitHub releases on pushed matching version tags.
- `tools/prepare_package.py` generates the exact source asset and matching
  metadata in `dist/`; `tools/ci_build_arch.sh` runs the Arch CI build locally.
  See `docs/releases.md`. AUR submission remains manual.
- `tests/`: standard-library `unittest` tests for config, protocol, tray logic,
  first-session service initialization, stable sensors, and offline research tools.
- `tools/inspect_windows.py`, `tools/inspect_hid.py`, `tools/inspect_capture.py`:
  offline binary/PDB, read-only sysfs descriptor, and filtered USBPcap analysis.
  Do not execute proprietary references or publish raw peripheral captures.
- `docs/reverse-engineering.md`: evidence, sample identities, and remaining
  pixel-control questions. Keep software-derived findings separate from physical tests.

## Development and verification

Run from the repository root:

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 -m csl_dotmatrix --help
```

Optional checks that read local sensors without opening HID:

```sh
PYTHONPATH=. python3 -m csl_dotmatrix --list-sensors
PYTHONPATH=. python3 -m csl_dotmatrix --source cpu --dry-run --once
```

The unit tests need neither Qt nor hidapi nor attached hardware. The dry run
requires an identifiable local sensor and reads the user's saved configuration.
For isolated config checks, point `XDG_CONFIG_HOME` at a temporary directory.
Use temporary hwmon fixtures and mock subprocess/HID calls for automated tests.

GUI/tray checks require PySide6 and a graphical session:
`PYTHONPATH=. python3 -m csl_dotmatrix.gui` or
`PYTHONPATH=. python3 -m csl_dotmatrix.tray`. Report desktop and hardware checks
separately from unit tests; unit tests do not prove physical display behavior.
For shell changes, run `sh -n install.sh uninstall.sh`.

## Invariants to preserve

- Keep Qt optional and imported inside GUI/tray entry functions. Headless CLI
  use and tests must not require PySide6; dry runs must not require hidapi.
- Only the CLI/service writes HID. The GUI and tray save settings and control
  `csl-dotmatrix.service`; quitting the tray leaves the service running.
- Match VID/PID `1a2c:434d`, interface `1`, usage page `0xff01`. Refuse multiple
  matching devices rather than choosing arbitrarily. The reported keyboard
  identity alone does not establish that a device is this cooler.
- The verified feature report is exactly 64 bytes: `07 FF FF 00 TT UU` followed
  by 58 zero bytes, with separate decimal tens/ones digits. Only `00`–`99` and
  the degree symbol are verified. Do not invent commands for unit letters,
  pixels, RGB, pump control, firmware, or other unverified reports.
  Windows static analysis identifies byte 3 as a hundreds digit and a separate
  `07 FD` firmware-version query; neither extends the physically verified Linux
  protocol. See the research document before interpreting old unknown packets.
- The display times out after approximately 12 seconds. Valid update intervals
  are 0.2–9 seconds. Celsius/Fahrenheit conversion is numeric; out-of-range
  readings are clamped with a warning unless `--strict-range` is used.
- Shared settings live at
  `${XDG_CONFIG_HOME:-~/.config}/csl-dotmatrix/config.json`. Preserve validation,
  defaults, private file permissions, and atomic replacement. CLI overrides
  apply only to that invocation. Tray choices preserve unrelated settings.
- Never run an additional HID sender alongside the service. Use dry runs for
  routine development. Do not unplug pump power to refresh device permissions.
- Installation affects the user's home and service state; do not run installers,
  uninstallers, or change udev/service settings merely to validate source edits.
  Uninstall preserves personal settings; udev rule installation is separate.

## Existing inconsistencies

Confirm behavior against code when touching these areas:

- `install.sh` generates desktop entries with absolute executable paths; the
  checked-in `desktop/` entries use PATH and are installed by the AUR package.
- Manual installation uses a home-directory service; the package installs a
  separate unit with `/usr/bin/csl-dotmatrix` as `csl-dotmatrix.service`.
  The old home-directory unit overrides it, so migration requires uninstalling
  the manual installation first. Never install both variants together.

Keep changes focused on the requested task. Update README when changing public
behavior or installation instructions, and preserve the distinction between
implemented support and hardware-verified support.

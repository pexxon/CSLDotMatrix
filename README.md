# CSL DotMatrix Linux v0.6.0

A native Qt application and Linux HID temperature controller for the **CSL DotMatrix aRGB 240 mm AIO**. Unofficial community project, not affiliated with CSL.

## Download an Arch package

Once a release is published, download its `.pkg.tar.zst` file from
[GitHub Releases](https://github.com/pexxon/CSLDotMatrix/releases), then run:

```sh
sudo pacman -S --needed python-hidapi pyside6
sudo pacman -U ./csldotmatrix-*.pkg.tar.zst
csl-dotmatrix-session
```

If migrating from `./install.sh`, run `./uninstall.sh` first to remove the old
home-directory service; settings are preserved. Existing users enable the
display service through Settings. A fresh installation starts with CPU/Celsius
defaults and opens the tray, with automatic startup at future desktop logins.

GitHub Actions tests each push/PR and builds a downloadable package artifact.
Pushing a matching version tag also creates a release with the package, source
archive, and checksums. See [build and release instructions](docs/releases.md).

## Arch Linux / AUR (prepared for publication)

The `csldotmatrix` package is prepared in `packaging/aur/`; it is not yet
published. Once v0.6.0 and the AUR package have been published, install with:

```sh
yay -S csldotmatrix
```

The package includes Python/hidapi/Qt dependencies, the udev permission rule,
application menu entries, a systemd **user** service, and desktop autostart.
At the next graphical login, a fresh installation enables the display service
with CPU/Celsius defaults and opens the tray. To start immediately after
installation, launch **CSL DotMatrix** from the application menu, or run
`csl-dotmatrix-session`. This requires an active local desktop session; it does
not start the display before login. NVIDIA temperature reads additionally need
`nvidia-utils` and a working NVIDIA driver.

Existing configuration is preserved and does not automatically enable the
service. Use **CSL DotMatrix Settings** to enable it. To disable tray autostart,
create `~/.config/autostart/csl-dotmatrix.desktop` containing:

```ini
[Desktop Entry]
Type=Application
Name=CSL DotMatrix
Hidden=true
```

To migrate from `./install.sh`, run `./uninstall.sh` **before** installing the
package. This removes the old home-directory service that would override the
packaged service, and preserves settings. Re-enable the service in Settings
after migration. Remove an old manually installed
`/etc/udev/rules.d/70-csl-dotmatrix.rules` if you want to use only the packaged
rule. Remove packaged installations with `yay -Rns csldotmatrix`, rather than
the manual uninstaller. User settings and per-user systemd enablement links
remain in your home directory; stop the service and quit the tray before removal.

The `csldotmatrix` and `csl-dotmatrix` commands both run the CLI.
See [AUR release instructions](packaging/aur/README.md) for building and publishing.

## What's new in v0.6.0 (unreleased)

- System-wide Arch packaging, with a reproducible source asset and SHA-256.
- GitHub Actions tests, Arch package artifacts, and automatic tagged releases.
- Stable hwmon/PCI sensor selectors and a detected-sensor picker in Settings.
- Warnings when automatic hwmon GPU selection has multiple devices to choose from.
- Offline Windows/PDB and HID descriptor analysis tools, with documented
  [protocol findings and pixel-control research](docs/reverse-engineering.md).

## What's new in v0.5.0

- Redesigned Qt settings window, using your Qt/KDE palette rather than a forced dark theme.
- Fixed XDG desktop autostart launcher: an explicit absolute `Exec` path instead of shell command quoting.
- Tray startup waits for Plasma's system tray host (up to 60 seconds) and prevents duplicate tray instances.
- Added `./uninstall.sh` to remove user-installed application components while keeping personal settings by default.

### Upgrade from an earlier manually installed version

```sh
sudo pacman -S python-hidapi pyside6 # Arch Linux
./install.sh
```

If you have a stale tray process from v0.4.0, quit it from its menu, then log out and back in. To test the new tray immediately, run `~/.local/bin/csl-dotmatrix-tray` in a terminal. Confirm Plasma's **System Tray** widget is enabled and that hidden icons are visible. The Qt tray relies on a working Status Notifier host; desktop autostart cannot force Plasma to display an icon.

### Uninstall (manual installation only)

```sh
./uninstall.sh
```

This stops and disables the user service; removes the user-installed launchers, Python application folder, desktop entries, tray autostart entry, and service unit. Your settings in `~/.config/csl-dotmatrix/config.json` are **preserved**. A tray already running in memory may remain until you choose **Quit tray** or log out.

Optional complete cleanup **only if no other installation still uses the files**:

```sh
rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/csl-dotmatrix"
sudo rm /etc/udev/rules.d/70-csl-dotmatrix.rules
sudo udevadm control --reload-rules
```

Do not run this uninstaller against an AUR/pacman installation; use `sudo pacman -Rns csldotmatrix` for packaged releases.

---

## Status and compatibility

- **CPU temperature:** confirmed working on Linux (AMD `k10temp`). Intel `coretemp` sensor selection is implemented but not yet field-tested.
- **GPU temperature:** confirmed working on the original tester's AMD GPU. NVIDIA support via `nvidia-smi` is implemented but not yet field-tested.
- **Autostart:** confirmed to survive a reboot using a systemd user service.
- **GUI:** previous Tkinter version tested; the Qt GUI confirmed working in v0.4.0; redesigned layout in v0.5.0 awaits desktop testing.
- **Qt system tray:** implemented with PySide6 / QSystemTrayIcon for KDE Plasma; other desktops depend on tray availability. Hardware test of v0.5.0 is pending.
- **Units:** numeric Celsius and Fahrenheit conversion is supported. The verified command draws **two numbers and a degree symbol**, not an explicit C or F letter.
- **Range:** only `00`–`99` is verified. Values outside this range are clamped with a warning; no three-digit rendering is claimed.

### Hardware

| Item | Verified value |
| --- | --- |
| Cooler | CSL DotMatrix aRGB 240 mm AIO |
| USB ID | `1a2c:434d` |
| USB identification string | `SEMICO USB Gaming Keyboard` |
| HID interface / usage page | `1` / `0xff01` |
| Report type / ID | 64-byte HID feature report / `0x07` |
| Keepalive behavior | Display switches off ~12 seconds after last update |

The USB identification string is surprising but was **verified by sending a known packet and observing the cooler display change**. Do not use this project with an unrelated device sharing the same identifiers.

## Screenshots

The native Qt UI is included. Add an authentic screenshot from KDE Plasma once v0.5.0 has been tested on hardware; no mock screenshots are presented as real.

## Requirements

- Linux with `/dev/hidraw*` and Python 3.9+
- `hidapi` Python bindings (`import hid`)
- PySide6 (Qt 6) for the settings GUI and tray icon; the headless display daemon does not require Qt
- `systemd --user` for autostart control
- Optional: `nvidia-smi` for NVIDIA GPU temperatures

Arch Linux:

```sh
sudo pacman -S python-hidapi pyside6
```

Debian/Ubuntu (Qt package names depend on distro release):

```sh
sudo apt install python3-hid python3-pyside6.qtwidgets
```

On systems without a packaged PySide6, install it in a Python virtual environment and make sure the GUI/tray launchers use that Python interpreter. Avoid system-wide `pip --break-system-packages` installs. On Arch/KDE Plasma, `pyside6` uses the distro's Qt6 installation and follows the desktop theme. Qt platform plugins must be available for your X11 or Wayland session.

**KDE Plasma:** Qt's `QSystemTrayIcon` integrates with Plasma's System Tray. Make sure the System Tray widget is enabled. The service/CLI runs independently if Qt isn't installed.

## Installation

```sh
git clone https://github.com/pexxon/CSLDotMatrix.git
cd CSLDotMatrix
./install.sh
```

The manual installer copies the CLI, GUI and tray launcher into `~/.local/bin/`, the Python package into `~/.local/lib/`, desktop entries into `~/.local/share/applications/`, a tray autostart entry into `~/.config/autostart/`, and a user service into `~/.config/systemd/user/`. It does not require root, install packages, or change device permissions. Do not combine manual and packaged installations.

### Allow display access without root

If you have not installed the rule before:

```sh
sudo install -m 644 udev/70-csl-dotmatrix.rules /etc/udev/rules.d/70-csl-dotmatrix.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw
```

Log out and back in, or reboot. This uses `TAG+="uaccess"` so the active local seat user can access matching HID devices. It will not necessarily work in a headless session. If access is denied, run `getfacl /dev/hidrawX` (identify the device path from the CLI logs; it can change after reboot). Avoid running the background service as root. **Never unplug the pump power just to refresh device permissions.**

### First-run check

```sh
~/.local/bin/csl-dotmatrix --list-sensors
~/.local/bin/csl-dotmatrix --source cpu --dry-run --once
~/.local/bin/csl-dotmatrix --source cpu --once
```

A single successful report lights the display temporarily. The screen should switch off after ~12 seconds unless the service continues updating it.

## Graphical settings

Open **CSL DotMatrix Settings** from your application launcher, or run:

```sh
~/.local/bin/csl-dotmatrix-settings
```

The window lets you change:

- Temperature source: **CPU** or **GPU**
- Unit: **°C** or **°F** (numeric conversion, not a C/F letter on the device)
- Update interval (0.2–9 seconds; default 1)
- A detected sensor picker or an explicit stable selector / Linux `hwmon` path
- **Start automatically at Linux login**

Click **Save and apply** to write `~/.config/csl-dotmatrix/config.json` (or `$XDG_CONFIG_HOME/csl-dotmatrix/config.json`), then enable/restart or disable/stop the background service. **Do not run a separate CLI sender alongside the service.** The GUI does not write arbitrary HID bytes or control the pump.

To run the GUI, you need a graphical desktop and PySide6; on headless systems use the CLI and edit the JSON configuration instead.

## Native Qt system tray (v0.5.0)

Launch **CSL DotMatrix Tray** from your applications menu, or run:

```sh
~/.local/bin/csl-dotmatrix-tray
```

Right-click the tray icon to select **CPU**, **GPU**, **Celsius (°C)** or **Fahrenheit (°F)**. The active choice is checked. The menu also offers **Open settings…** and **Quit tray**. Menu selections update the shared JSON config and restart the running display service so the choice takes effect. If the service is stopped, the saved choice takes effect the next time it starts; the tray never sends HID data itself.

The installer creates `~/.config/autostart/csl-dotmatrix-tray.desktop` so the tray appears after desktop login. This is **independent** of the systemd user service: the tray is UI only, and quitting the tray does **not** stop the cooler's display. To disable the tray's login autostart, remove that `.desktop` file. To stop the display, disable/stop the user service in the settings window or via `systemctl --user`.

If the tray icon or right-click menu does not appear, check `python3 -c "from PySide6.QtWidgets import QSystemTrayIcon; print(QSystemTrayIcon.isSystemTrayAvailable())"` in a graphical session. Launch `csl-dotmatrix-tray` from a terminal to read errors. In Plasma, check the tray widget and hidden icons. You can still use **CSL DotMatrix Settings** from the app launcher. The Qt tray uses the same config and never opens the HID device.

## Autostart and service controls

The background service reads the same configuration as the GUI. It runs when the user logs in, not necessarily before login.

```sh
systemctl --user enable --now csl-dotmatrix.service
systemctl --user status csl-dotmatrix.service
journalctl --user -u csl-dotmatrix.service -f
systemctl --user disable --now csl-dotmatrix.service
```

**Upgrading from v0.1.0–v0.3.0:** Pull or extract the new project and run `./install.sh` again. The installer replaces the old service with a version that reads the saved settings. Your existing enabled service remains enabled and is restarted if active. You do **not** need to change udev permissions again.

## Command-line interface

```sh
csl-dotmatrix --list-sensors
csl-dotmatrix --source cpu --unit C
csl-dotmatrix --source gpu --unit F
csl-dotmatrix --sensor /sys/class/hwmon/hwmon4/temp1_input
csl-dotmatrix --sensor 'pci:0000:03:00.0/edge'
csl-dotmatrix --sensor 'hwmon:k10temp/Tctl'
csl-dotmatrix --dry-run --once
```

Explicit command-line flags override saved settings **for that invocation only**. Without flags, the CLI and service use settings from `config.json`, falling back to CPU, Celsius and a 1-second interval.

Stop the background service before manual testing:

```sh
systemctl --user stop csl-dotmatrix.service
csl-dotmatrix --source gpu --unit C
# press Ctrl+C, then:
systemctl --user start csl-dotmatrix.service
```

**Sensor selection:** CPU selection prefers `k10temp` or `coretemp`; GPU selection uses `nvidia-smi` when available, otherwise an `amdgpu` or other recognized `hwmon` sensor. On multi-GPU systems, automatic GPU selection may not match the GPU you intended; multiple hwmon GPU devices produce a warning. Inspect `--list-sensors` or Settings' detected-sensor picker and choose a stable `pci:ADDRESS/LABEL` selector to identify a specific GPU across hwmon renumbering. `hwmon:CHIP/LABEL` also works when that combination is unique. Selectors fail explicitly if missing or ambiguous. Raw sensor paths remain supported; their `hwmonN` number can change at boot. PCI addresses can also change after hardware/topology changes. Explicit selectors take precedence over `nvidia-smi`.

## Reverse-engineered protocol

Captured on Windows and successfully replayed on Linux:

```text
07 FF FF 00 TT UU 00 00 ... (64 bytes in total)
```

- `07` = HID feature report ID
- `FF FF 00` = observed constant bytes (precise semantics unknown)
- `TT` = tens digit, 0–9
- `UU` = ones digit, 0–9
- 58 trailing zero bytes

Example: `07 FF FF 00 04 04` displays `44°`. Transmission uses `send_feature_report` on HID interface 1, usage page `0xff01`. The original USB control request was `SET_REPORT` (`bmRequestType=0x21`, `bRequest=0x09`, `wValue=0x0307`, `wIndex=1`). A periodic update keeps the screen on.

Static analysis of the matching Windows EXE/PDB now shows byte 3 being filled
with a hundreds digit: the previously unexplained `07 FF FF 01 01 01` and
`07 FF FF 01 01 03` prefixes fit 111 and 113. This is evidence from software;
three-digit rendering remains unverified on the physical display and these
packets are not sent by the Linux controller. See the
[analysis report](docs/reverse-engineering.md) for addresses, hashes, report
length details, and reproducible inspection commands. No arbitrary letters,
individual dot-matrix pixels, animations, firmware updates, pump controls, or
explicit CPU/GPU labels are supported.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `HID error: open failed` | Install/reload udev rule; inspect `getfacl` for the selected `/dev/hidrawX`; log in again |
| Cooler not found | Run `lsusb`; verify `1a2c:434d` and the physical USB connection |
| GUI won't open | Install PySide6 (`pyside6` on Arch); use a graphical Linux session |
| GUI saves but display stays off | Run `systemctl --user status csl-dotmatrix.service` and check `journalctl --user -u csl-dotmatrix.service -n 50` |
| Wrong temperature | Run `csl-dotmatrix --list-sensors`; select the correct sensor |
| Fahrenheit shows 99° repeatedly | Actual value may exceed 99; the Windows hundreds-digit format has not yet been physically verified |
| Two processes contend for the display | Stop the service before manually running the CLI |

## Development and contributions

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 -m csl_dotmatrix --source cpu --dry-run --once
PYTHONPATH=. python3 -m csl_dotmatrix.gui
```

Hardware-free tests verify packet encoding and configuration validation. The GUI and service need field testing on your Linux desktop. Please open issues with your distro, `lsusb` device ID, and non-sensitive error logs. **Do not upload unfiltered USB traffic containing unrelated keyboard or peripheral data.**

## License

[MIT](LICENSE). Contributions welcome.

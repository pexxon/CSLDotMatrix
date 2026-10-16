# Local review and remaining release checks

The checkout contains the CLI/HID loop, shared config, sensor discovery,
PySide6 settings and tray, desktop/session startup, manual installers, and
unpublished v0.6.0 Arch packaging. The handover's v0.5.0 refers to the existing
Git tag; these working-tree changes are the next release, not a published tag.

## Issues addressed

- Multi-GPU selection previously depended on hwmon enumeration order without
  identifying the chosen GPU clearly. Existing defaults remain, with a warning
  for multiple hwmon GPUs and explicit PCI/chip-plus-label selectors.
- Settings now offers detected sensors, including PCI identities, while retaining
  an editable override and the desktop's Qt palette.
- `encode_temperature` now rejects booleans and derives padding from the report
  length constant. It still accepts only integer 00–99 temperatures.
- Manual install/uninstall scripts now guard against accidentally operating on
  a system-wide installation. A manual user unit still overrides a packaged
  unit; remove the manual install before installing the package.
- Packaging uses an exact reproducible release asset and SHA-256 instead of a
  VCS source with `SKIP`. Sources exclude proprietary references and captures.
- Old protocol assumptions were revised using a matched Windows EXE/PDB.

## Checks performed

- Unit tests cover config validation, the existing packet, interface filtering,
  tray settings, first-session initialization, sensor identity across hwmon
  renumbering, ambiguous selectors, and research-tool parsers.
- The updated settings window was constructed with Qt's offscreen platform;
  selecting an AMD GPU populated the stable selector. Config saves and service
  controls were mocked. This does not test desktop theme appearance.
- Sysfs descriptors were read without opening hidraw; report 7 has 63-byte
  Feature/Output payloads plus one report-ID byte.
- The EXE/PDB identity and offline analysis tool were checked against the actual
  supplied files. No experimental HID commands were sent.
- The active installed user service was observed running with
  `/usr/bin/csl-dotmatrix` and the unit in `/usr/lib/systemd/user/`.
- The local environment reports Hyprland/Wayland, not KDE Plasma. Current Arch
  Qt6 packages provide the Wayland platform plugin in `qt6-base`, already a
  dependency of PySide6; an extra `qt6-wayland` dependency is not needed for it.
- The GitHub Actions package script passed in a fresh Arch Linux container:
  source-checksum verification, all 26 tests, package creation, desktop-file
  validation, `namcap`, and both installed CLI dry runs. `namcap` reported no
  errors; warnings include missing AUR maintainer details and heuristic Python
  entry-point/systemd dependency checks. The entry points were exercised from
  an extracted package, independently of the checkout. GitHub-hosted execution
  and publication still require pushing the workflow to the repository.

## Still required before publication

- Prefer a clean Arch `devtools` chroot build before AUR submission; the CI
  container build and `namcap` checks are already available.
- In a test desktop session, exercise installation (`makepkg -si`), real cooler
  output, package upgrade/removal, and migration from the manual installer.
  Source/staging checks do not substitute for those system-changing tests.
- Verify Plasma Wayland login autostart, tray-host retries, duplicate prevention,
  Settings changes, explicit stop choices, and logout/login. This session
  cannot establish KDE behavior.
- Test Intel/NVIDIA, a missing selected sensor, and hardware topology changes.
- Publish the approved v0.6.0 tag and exact source asset; verify the checksum
  against a fresh download before submitting the AUR metadata. Nothing has
  been published automatically.
- The original USB capture has now been independently parsed: 19 successful
  64-byte numeric reports and no other application commands for the cooler.
  Obtain a firmware updater/image or additional relevant captures to investigate
  individual-dot access. No framebuffer command is known.

References: [Arch Qt6 base file list](https://archlinux.org/packages/extra/x86_64/qt6-base/files/),
[PySide6 dependencies](https://archlinux.org/packages/extra/x86_64/pyside6/).

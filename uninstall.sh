#!/bin/sh
# Remove only paths installed by install.sh; preserve config by default.
set -eu
BIN="$HOME/.local/bin"
APP="$HOME/.local/share/applications"
AUTO="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
UNIT="$HOME/.config/systemd/user/csl-dotmatrix.service"
systemctl --user disable --now csl-dotmatrix.service 2>/dev/null || true
# Close only this user's tray launched from our installed application.
# Old tray can be quit from its menu; don't indiscriminately kill Python processes.
for item in csl-dotmatrix csl-dotmatrix-settings csl-dotmatrix-tray; do
    rm -f "$BIN/$item"
done
rm -rf "$HOME/.local/lib/csl_dotmatrix"
rm -f "$APP/csl-dotmatrix-settings.desktop" "$APP/csl-dotmatrix-tray.desktop"
rm -f "$AUTO/csl-dotmatrix-tray.desktop" "$UNIT"
systemctl --user daemon-reload 2>/dev/null || true
printf 'CSL DotMatrix application files and user service removed.\n'
printf 'Configuration preserved: %s/csl-dotmatrix/config.json\n' "${XDG_CONFIG_HOME:-$HOME/.config}"
printf 'Optional: remove configuration and the system-wide udev rule separately; see README.\n'

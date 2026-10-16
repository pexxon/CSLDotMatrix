#!/bin/sh
set -eu
if [ -f /usr/lib/systemd/user/csl-dotmatrix.service ]; then
    printf 'A system-wide installation exists. Upgrade it with pacman instead of install.sh.\n' >&2
    exit 1
fi
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BIN="$HOME/.local/bin"
APP="$HOME/.local/share/applications"
AUTO="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
mkdir -p "$BIN" "$HOME/.local/lib" "$APP" "$AUTO" "$HOME/.config/systemd/user"
# Remove only the application's own Python package before copying new files.
rm -rf "$HOME/.local/lib/csl_dotmatrix"
cp -R "$PROJECT_DIR/csl_dotmatrix" "$HOME/.local/lib/"
for item in csl-dotmatrix csl-dotmatrix-settings csl-dotmatrix-tray; do
    cp "$PROJECT_DIR/$item" "$BIN/$item"
    chmod 755 "$BIN/$item"
done
cat > "$APP/csl-dotmatrix-settings.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CSL DotMatrix Settings
Comment=Configure your CSL AIO temperature display
Exec=$BIN/csl-dotmatrix-settings
Icon=utilities-system-monitor
Terminal=false
Categories=Settings;HardwareSettings;
EOF
cat > "$AUTO/csl-dotmatrix-tray.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CSL DotMatrix Tray
Comment=CSL DotMatrix controls in the system tray
Exec=$BIN/csl-dotmatrix-tray
Icon=utilities-system-monitor
Terminal=false
OnlyShowIn=KDE;GNOME;XFCE;LXQt;
X-GNOME-Autostart-enabled=true
EOF
cp "$AUTO/csl-dotmatrix-tray.desktop" "$APP/csl-dotmatrix-tray.desktop"
cp "$PROJECT_DIR/systemd/csl-dotmatrix.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload 2>/dev/null || true
if systemctl --user is-active --quiet csl-dotmatrix.service 2>/dev/null; then
    systemctl --user restart csl-dotmatrix.service
fi
printf '\nInstalled CSL DotMatrix v0.6.0.\n'
printf 'Tray: log out/in, or run %s/csl-dotmatrix-tray now.\n' "$BIN"
printf 'To remove: ./uninstall.sh (udev rule removal is optional/manual).\n'

"""Qt / KDE Plasma system tray. Never opens the cooler's HID interface."""
import subprocess
import sys
import os
import fcntl
from pathlib import Path
from .config import load_settings, save_settings

SERVICE = 'csl-dotmatrix.service'


def service_action(action):
    return subprocess.run(['systemctl', '--user', action, SERVICE],
                          text=True, capture_output=True, timeout=15, check=False)


def apply_choice(key, value):
    """Save only one setting, then restart the service if it's running."""
    if key not in ('source', 'unit'):
        raise ValueError('Unsupported tray setting')
    settings = load_settings()
    if settings[key] == value:
        return False
    settings[key] = value
    save_settings(settings)
    result = service_action('try-restart')
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Unable to restart display service')
    return True


def run():
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
        from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon
    except ImportError:
        print('PySide6 is required for the Qt tray. See README.md.', file=sys.stderr)
        return 2

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('CSL DotMatrix')
    app.setQuitOnLastWindowClosed(False)
    # Keep a process-level lock to avoid duplicate tray icons across upgrades/logins.
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/csl-dotmatrix-{os.getuid()}'))
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_file = open(runtime / 'csl-dotmatrix-tray.lock', 'w')
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('CSL DotMatrix tray is already running.')
        return 0

    # Draw a scale-aware monochrome-ish dot matrix icon using Qt, no external image assets.
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#26323f'))
    painter.drawRoundedRect(3, 3, 58, 58, 12, 12)
    for r in range(3):
        for c in range(3):
            painter.setBrush(QColor('#f0bd69') if (r, c) == (1, 1) else QColor('#60dbb7'))
            painter.drawEllipse(13 + 14 * c, 13 + 14 * r, 10, 10)
    painter.end()
    icon = QIcon(pix)
    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip('CSL DotMatrix')
    menu = QMenu()
    source_group = QActionGroup(menu)
    source_group.setExclusive(True)
    unit_group = QActionGroup(menu)
    unit_group.setExclusive(True)
    actions = {}

    def make_choice(label, key, value, group):
        action = QAction(label, menu)
        action.setCheckable(True)
        group.addAction(action)
        menu.addAction(action)
        actions[(key, value)] = action
        def on_triggered(_checked=False):
            try:
                apply_choice(key, value)
                refresh()
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                QMessageBox.warning(None, 'CSL DotMatrix', str(exc))
                refresh()
        action.triggered.connect(on_triggered)

    make_choice('CPU', 'source', 'cpu', source_group)
    make_choice('GPU', 'source', 'gpu', source_group)
    menu.addSeparator()
    make_choice('Celsius (°C)', 'unit', 'C', unit_group)
    make_choice('Fahrenheit (°F)', 'unit', 'F', unit_group)
    menu.addSeparator()
    settings_action = menu.addAction('Open settings…')
    settings_action.triggered.connect(lambda: subprocess.Popen(
        [sys.executable, '-m', 'csl_dotmatrix.gui'],
        start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    menu.addSeparator()
    quit_action = menu.addAction('Quit tray')
    quit_action.triggered.connect(app.quit)

    def refresh():
        try:
            settings = load_settings()
            for (key, value), action in actions.items():
                action.setChecked(settings[key] == value)
        except (OSError, ValueError) as exc:
            tray.showMessage('CSL DotMatrix', str(exc), QSystemTrayIcon.MessageIcon.Warning)

    menu.aboutToShow.connect(refresh)
    refresh()
    tray.setContextMenu(menu)
    # Plasma's status notifier host can start after XDG autostart apps.
    # Retry rather than exiting and missing the whole session.
    attempts = [0]
    timer = QTimer(app)
    def try_show():
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray.show()
            timer.stop()
        else:
            attempts[0] += 1
            if attempts[0] >= 60:
                print('Tray host unavailable after 60 seconds. Check Plasma System Tray settings.', file=sys.stderr)
                timer.stop()
                app.quit()
    timer.timeout.connect(try_show)
    timer.start(1000)
    try_show()
    result = app.exec()
    tray.hide()
    return result


if __name__ == '__main__':
    raise SystemExit(run())

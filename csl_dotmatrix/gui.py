"""Native Qt settings window (PySide6), separate from the HID-writing service."""
import subprocess
import sys
from .config import load_settings, save_settings

SERVICE = 'csl-dotmatrix.service'


def systemctl(*args):
    return subprocess.run(['systemctl', '--user', *args, SERVICE], text=True,
                          capture_output=True, check=False, timeout=15)


def enabled():
    result = systemctl('is-enabled')
    return result.returncode == 0 and result.stdout.strip() == 'enabled'


def main():
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
            QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
            QPushButton, QVBoxLayout, QWidget)
    except ImportError:
        print('PySide6 is required for the Qt settings app. See README.md.', file=sys.stderr)
        return 2

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('CSL DotMatrix')
    app.setDesktopFileName('csl-dotmatrix-settings')

    class SettingsWindow(QWidget):
        def __init__(self):
            super().__init__()
            from PySide6.QtWidgets import QGroupBox, QGridLayout, QSizePolicy
            self.setWindowTitle('CSL DotMatrix · Settings')
            self.setMinimumSize(540, 440)
            self.setObjectName('settingsWindow')
            settings = load_settings()
            root = QVBoxLayout(self)
            root.setContentsMargins(30, 26, 30, 26)
            root.setSpacing(16)

            header = QHBoxLayout()
            badge = QLabel('▦')
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(56, 56)
            badge.setStyleSheet('background: palette(midlight); border-radius: 14px; font-size: 32px;')
            header.addWidget(badge)
            identity = QVBoxLayout()
            title = QLabel('CSL DotMatrix')
            font = title.font()
            font.setPointSize(font.pointSize() + 8)
            font.setBold(True)
            title.setFont(font)
            identity.addWidget(title)
            subtitle = QLabel('Temperature display · Linux control center')
            subtitle.setStyleSheet('color: palette(placeholder-text);')
            identity.addWidget(subtitle)
            header.addLayout(identity, 1)
            root.addLayout(header)

            group = QGroupBox('Display')
            form = QFormLayout(group)
            form.setContentsMargins(18, 20, 18, 18)
            form.setSpacing(14)
            self.source = QComboBox()
            self.source.addItem('CPU temperature', 'cpu')
            self.source.addItem('GPU temperature', 'gpu')
            self.source.setCurrentIndex(max(0, self.source.findData(settings['source'])))
            form.addRow('Sensor source', self.source)
            self.unit = QComboBox()
            self.unit.addItem('Celsius (°C)', 'C')
            self.unit.addItem('Fahrenheit (°F)', 'F')
            self.unit.setCurrentIndex(max(0, self.unit.findData(settings['unit'])))
            form.addRow('Temperature unit', self.unit)
            self.interval = QDoubleSpinBox()
            self.interval.setRange(0.2, 9.0)
            self.interval.setSingleStep(0.2)
            self.interval.setDecimals(1)
            self.interval.setSuffix(' seconds')
            self.interval.setValue(settings['interval'])
            form.addRow('Refresh every', self.interval)
            self.sensor = QLineEdit(settings['sensor'])
            self.sensor.setPlaceholderText('Automatic detection (recommended)')
            form.addRow('Sensor path (optional)', self.sensor)
            root.addWidget(group)

            startup = QGroupBox('Startup')
            startup_layout = QVBoxLayout(startup)
            self.autostart = QCheckBox('Start temperature monitor when I log in')
            self.autostart.setChecked(enabled())
            startup_layout.addWidget(self.autostart)
            tip = QLabel('The tray icon starts separately with your Plasma desktop session.')
            tip.setWordWrap(True)
            tip.setStyleSheet('color: palette(placeholder-text);')
            startup_layout.addWidget(tip)
            root.addWidget(startup)
            self.status = QLabel('Ready · Confirmed display range: 00–99°. Unit letters are not supported yet.')
            self.status.setWordWrap(True)
            root.addWidget(self.status)
            root.addStretch()
            actions = QHBoxLayout()
            actions.addStretch()
            self.save_button = QPushButton('Save and apply')
            self.save_button.setMinimumWidth(150)
            self.save_button.setDefault(True)
            self.save_button.clicked.connect(self.apply)
            actions.addWidget(self.save_button)
            root.addLayout(actions)

        def apply(self):
            try:
                path = save_settings({
                    'source': self.source.currentData(), 'unit': self.unit.currentData(),
                    'interval': self.interval.value(), 'sensor': self.sensor.text().strip(),
                })
                change = systemctl('enable', '--now') if self.autostart.isChecked() else systemctl('disable', '--now')
                if change.returncode:
                    raise RuntimeError(change.stderr.strip() or 'Unable to change systemd service')
                if self.autostart.isChecked():
                    result = systemctl('restart')
                    if result.returncode:
                        raise RuntimeError(result.stderr.strip() or 'Unable to restart display service')
                    self.status.setText('✓ Saved and applied · Display service running')
                else:
                    self.status.setText('✓ Saved · Display service stopped')
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                QMessageBox.critical(self, 'CSL DotMatrix', str(exc))

    try:
        window = SettingsWindow()
    except (OSError, ValueError) as exc:
        QMessageBox.critical(None, 'CSL DotMatrix', str(exc))
        return 1
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())

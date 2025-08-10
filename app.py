from ui.login import LoginDialog
from ui.main_window import MainWindow
from core.auth import load_tokens
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication
import sys

import pyqtgraph as pg
from PySide6.QtCore import Qt
# Fuerza backend software y 2D estable
QGuiApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, on=True)
pg.setConfigOptions(useOpenGL=False, antialias=True)


def main():
    app = QApplication(sys.argv)
    dlg = LoginDialog()

    # === Auto-login si se puede ===
    can, user = dlg.should_autologin()
    if can and user:
        access, refresh = load_tokens(user)
        if access or refresh:  # hay algo para intentar (el cliente refresca si 401)
            w = MainWindow(user)
            w.show()
            sys.exit(app.exec())

    # Fallback: login tradicional
    if dlg.exec():
        if dlg.ok and dlg.username:
            w = MainWindow(dlg.username)
            w.show()
            sys.exit(app.exec())

if __name__ == "__main__":
    main()

import sys
from PySide6.QtWidgets import QApplication
from ui.login import LoginDialog
from ui.main_window import MainWindow

try:
    import truststore  # type: ignore[import]
    truststore.inject_into_ssl()
except Exception:
    pass

def main():
    app = QApplication(sys.argv)
    dlg = LoginDialog()
    if dlg.exec() == 0 or not dlg.ok:
        sys.exit(0)
    mw = MainWindow(dlg.username) # type: ignore
    mw.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

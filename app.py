from PySide6.QtWidgets import QApplication
from ui.login import LoginDialog
from ui.main_window import MainWindow
from core.auth import load_tokens
import sys

def run_main(username: str, app: QApplication):
    # callback para volver al login cuando el usuario cierra sesión
    def back_to_login():
        dlg = LoginDialog()
        if dlg.exec() and dlg.ok and dlg.username:
            w = MainWindow(dlg.username, on_logout=back_to_login)
            w.show()
        else:
            app.quit()

    w = MainWindow(username, on_logout=back_to_login)
    w.show()

def main():
    app = QApplication(sys.argv)

    dlg = LoginDialog()
    can, user = dlg.should_autologin()
    if can and user:
        access, refresh = load_tokens(user)
        if access or refresh:
            run_main(user, app)
            sys.exit(app.exec())

    if dlg.exec() and dlg.ok and dlg.username:
        run_main(dlg.username, app)
        sys.exit(app.exec())

if __name__ == "__main__":
    main()

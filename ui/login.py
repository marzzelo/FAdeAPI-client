from PySide6.QtWidgets import QDialog, QLineEdit, QVBoxLayout, QLabel, QPushButton, QMessageBox
from core.auth import login, save_tokens
from core.config import Config
import asyncio

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FADEAPI – Login")
        self.u = QLineEdit()
        self.u.setPlaceholderText("Usuario")
        self.p = QLineEdit()
        self.p.setEchoMode(QLineEdit.Password)
        self.p.setPlaceholderText("Contraseña")
        self.btn = QPushButton("Ingresar")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Ingrese sus credenciales"))
        lay.addWidget(self.u)
        lay.addWidget(self.p)
        lay.addWidget(self.btn)
        self.btn.clicked.connect(self._do_login)
        self.ok = False
        self.username = None

    def _do_login(self):
        base_url = Config().base_url()
        username = self.u.text().strip()
        password = self.p.text()
        try:
            access, refresh = asyncio.run(login(base_url, username, password))
            save_tokens(username, access, refresh)
            self.username = username
            self.ok = True
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login fallido:\n{e}")

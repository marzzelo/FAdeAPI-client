from PySide6.QtWidgets import QDialog, QLineEdit, QVBoxLayout, QLabel, QPushButton, QMessageBox, QCheckBox
from core.auth import login, save_tokens
from core.config import Config
import asyncio
from datetime import datetime, timezone


REMEMBER_DAYS_DEFAULT = Config().get_remember_days_default()



class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FADEAPI – Login")
        self.u = QLineEdit(); self.u.setPlaceholderText("Usuario")
        self.p = QLineEdit(); self.p.setEchoMode(QLineEdit.Password); self.p.setPlaceholderText("Contraseña")
        self.chk = QCheckBox("Recordar mis credenciales (30 días)")
        self.btn = QPushButton("Ingresar")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Ingrese sus credenciales"))
        lay.addWidget(self.u); lay.addWidget(self.p); lay.addWidget(self.chk); lay.addWidget(self.btn)
        self.btn.clicked.connect(self._do_login)
        self.ok = False
        self.username = None

        # Prefill username si existe
        cfg = Config()
        last_user = cfg.get_last_username()
        if last_user:
            self.u.setText(last_user)

    def should_autologin(self) -> tuple[bool, str | None]:
        """Permite que app.py consulte si puede saltar el login."""
        cfg = Config()
        user = cfg.get_last_username()
        if not user:
            return False, None
        until = cfg.remember_until(user)
        if until and datetime.now(timezone.utc) <= until:
            return True, user
        return False, user

    def _do_login(self):
        base_url = Config().base_url()
        username = self.u.text().strip()
        password = self.p.text()
        try:
            access, refresh = asyncio.run(login(base_url, username, password))
            save_tokens(username, access, refresh)
            cfg = Config()
            cfg.set_last_username(username)
            if self.chk.isChecked():
                cfg.set_remember_days(username, REMEMBER_DAYS_DEFAULT)
            else:
                cfg.clear_remember(username)
            self.username = username
            self.ok = True
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login fallido:\n{e}")

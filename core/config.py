from datetime import datetime, timedelta, timezone
from PySide6.QtCore import QSettings


DEFAULT_BASE_URL = "http://localhost:8000"
# DEFAULT_BASE_URL = "https://fadeapi-498d1e85e7e4.herokuapp.com/"


class Config:
    def __init__(self):
        self.q = QSettings("FAdeA", "FADEAPI-Client")

    def base_url(self) -> str:
        return self.q.value("base_url", DEFAULT_BASE_URL, str)

    def set_base_url(self, url: str):
        self.q.setValue("base_url", url)

    # ======== Nuevo: recordar credenciales ========
    def set_last_username(self, username: str):
        self.q.setValue("last_username", username)

    def get_last_username(self) -> str | None:
        v = self.q.value("last_username")
        return str(v) if v else None

    def remember_until(self, username: str) -> datetime | None:
        key = f"remember_until/{username}"
        ts = self.q.value(key)
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return None

    def set_remember_days(self, username: str, days: int = 30):
        key = f"remember_until/{username}"
        until = datetime.now(timezone.utc) + timedelta(days=days)
        self.q.setValue(key, until.isoformat())

    def clear_remember(self, username: str):
        self.q.remove(f"remember_until/{username}")
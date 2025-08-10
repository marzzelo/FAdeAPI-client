from PySide6.QtCore import QSettings
from datetime import datetime, timedelta, timezone

_CLOUD_URL     = "https://fadeapi-498d1e85e7e4.herokuapp.com/"
_LOCALHOST_URL = "http://localhost:8000/"

class Config:
    def __init__(self):
        self.q = QSettings("FAdeA", "FADEAPI-Client")

    # === API base ===
    def base_url(self) -> str:
        v = self.q.value("base_url", _CLOUD_URL)
        return v if str(v).endswith("/") else str(v) + "/"

    def set_base_url(self, url: str):
        self.q.setValue("base_url", url if url.endswith("/") else url + "/")

    # Guardamos una preferencia “simpática” de selección de entorno
    def get_api_env(self) -> str:
        # "cloud" | "localhost" | "custom"
        return self.q.value("api_env", "cloud")

    def set_api_env(self, env: str):
        self.q.setValue("api_env", env)

    def cloud_url(self) -> str:
        return _CLOUD_URL

    def localhost_url(self) -> str:
        return _LOCALHOST_URL

    # === Recordarme ===
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

    def set_remember_days(self, username: str, days: int):
        key = f"remember_until/{username}"
        until = datetime.now(timezone.utc) + timedelta(days=days)
        self.q.setValue(key, until.isoformat())

    def clear_remember(self, username: str):
        self.q.remove(f"remember_until/{username}")

    # valor por defecto (global) para días de “Recordarme”
    def get_remember_days_default(self) -> int:
        try:
            return int(self.q.value("remember_days_default", 30))
        except Exception:
            return 30

    def set_remember_days_default(self, days: int):
        self.q.setValue("remember_days_default", int(days))

    # === Preferencias varias ===
    def get_default_limit(self) -> int:
        try:
            return int(self.q.value("default_limit", 1000))
        except Exception:
            return 1000

    def set_default_limit(self, n: int):
        self.q.setValue("default_limit", int(n))

    def get_auto_check_updates(self) -> bool:
        return bool(self.q.value("auto_check_updates", True, type=bool))

    def set_auto_check_updates(self, v: bool):
        self.q.setValue("auto_check_updates", bool(v))

    # === Tema UI ===
    def get_theme(self) -> str:
        # "light" | "dark"
        return self.q.value("theme", "light")

    def set_theme(self, theme: str):
        self.q.setValue("theme", theme)
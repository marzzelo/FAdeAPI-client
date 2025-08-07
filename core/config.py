from PySide6.QtCore import QSettings

class Config:
    def __init__(self):
        self.q = QSettings("FAdeA", "FADEAPI-Client")

    def base_url(self) -> str:
        return self.q.value("base_url", "https://fadeapi-498d1e85e7e4.herokuapp.com/")

    def set_base_url(self, url: str):
        self.q.setValue("base_url", url)

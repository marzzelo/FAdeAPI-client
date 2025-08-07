from PySide6.QtWidgets import QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from core.api import ApiClient
from ui.about import AboutDialog
import asyncio

class MainWindow(QMainWindow):
    def __init__(self, username: str):
        super().__init__()
        self.setWindowTitle("FADEAPI Client")
        self.api = ApiClient(username)

        tabs = QTabWidget()
        tabs.addTab(self._build_status_tab(), "Status")
        tabs.addTab(QWidget(), "Registros")  # placeholder
        tabs.addTab(QWidget(), "Usuarios")   # placeholder

        about_btn = QPushButton("Acerca de")
        about_btn.clicked.connect(lambda: AboutDialog().exec())

        c = QWidget(); lay = QVBoxLayout(c)
        lay.addWidget(tabs); lay.addWidget(about_btn)
        self.setCentralWidget(c)

    def _build_status_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        label = QLabel("Servidor: (sin consultar)")
        btn = QPushButton("Consultar /status")
        async def do_status():
            try:
                r = await self.api.request("GET", "status")
                data = r.json()
                label.setText(str(data))
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        btn.clicked.connect(lambda: asyncio.run(do_status()))
        lay.addWidget(btn); lay.addWidget(label)
        return w

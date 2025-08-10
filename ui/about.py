from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from core.__version__ import VERSION

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acerca de FADEAPI Client")
        t = (
            f"<h1>FADEAPI Client v{VERSION}</h1><br>"
            "Autor: <b>Marcelo A. Valdez</b> · Contacto: <i>valdez@fadeasa.com.ar</i><br>"
            "Colabora: <i>Arisa</i><br>"
            "Actualizaciones: descarga directa disponible desde el cliente.<br>"
            "<i>© FAdeA - Todos los Derechos reservados</i>"
        )
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t))

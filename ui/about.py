from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from core.__version__ import VERSION

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acerca de FADEAPI Client")
        t = (
            f"<b>FADEAPI Client v{VERSION}</b><br>"
            "Autor: Marcelo A. Valdez · Contacto: <i>valdez@fadeasa.com.ar</i><br>"
            "Colabora: <i>Arisa</i><br>"
            "© FAdeA - Todos los Derechos reservados"
        )
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t))

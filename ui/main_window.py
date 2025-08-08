# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton, QLabel,
    QMessageBox, QHBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog,
    QSpinBox, QLineEdit, QFormLayout, QGroupBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from ui.about import AboutDialog
from core.api import ApiClient
import asyncio

class RegistrosTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.limit = QSpinBox(); self.limit.setRange(1, 10000); self.limit.setValue(50)
        self.hasta = QLineEdit(); self.hasta.setPlaceholderText("YYYY-MM-DDTHH:MM:SS (opcional)")

        btn_refresh = QPushButton("Actualizar")
        btn_csv     = QPushButton("Descargar CSV")
        btn_delete  = QPushButton("Borrar TODOS (admin)")

        btn_refresh.clicked.connect(lambda: asyncio.run(self.load()))
        btn_csv.clicked.connect(self.download_csv)
        btn_delete.clicked.connect(self.delete_all)

        top = QHBoxLayout()
        top.addWidget(QLabel("limit:")); top.addWidget(self.limit)
        top.addWidget(QLabel("hasta:")); top.addWidget(self.hasta)
        top.addStretch(1); top.addWidget(btn_refresh); top.addWidget(btn_csv); top.addWidget(btn_delete)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table)

    async def load(self):
        try:
            data = await self.api.get_registros(limit=self.limit.value(), hasta_iso=self.hasta.text().strip() or None)
            # data: [{ "ts": "...", "sensores": [..] }, ...]
            max_s = max((len(r.get("sensores", [])) for r in data), default=0)
            headers = ["ts"] + [f"s{i+1}" for i in range(max_s)]
            self.table.setRowCount(len(data))
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            for row, r in enumerate(data):
                self.table.setItem(row, 0, QTableWidgetItem(str(r.get("ts",""))))
                sensores = r.get("sensores", [])
                for i in range(max_s):
                    val = "" if i >= len(sensores) else str(sensores[i])
                    self.table.setItem(row, i+1, QTableWidgetItem(val))
            self.table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar registros:\n{e}")

    def download_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "registros.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            content = asyncio.run(self.api.download_csv())
            with open(path, "wb") as f:
                f.write(content)
            QMessageBox.information(self, "OK", f"CSV guardado en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo descargar CSV:\n{e}")

    def delete_all(self):
        if QMessageBox.question(self, "Confirmar", "¿Eliminar TODOS los registros? Esta acción no se puede deshacer.") != QMessageBox.Yes:
            return
        try:
            res = asyncio.run(self.api.delete_registros())
            QMessageBox.information(self, "OK", str(res))
            asyncio.run(self.load())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")


class UsuariosTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        # --- Lista ---
        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        btn_refresh = QPushButton("Actualizar lista")
        btn_refresh.clicked.connect(lambda: asyncio.run(self.load()))

        # --- Alta ---
        grp_new = QGroupBox("Nuevo usuario")
        self.u_username = QLineEdit(); self.u_nombre = QLineEdit(); self.u_apellido = QLineEdit()
        self.u_email = QLineEdit(); self.u_password = QLineEdit(); self.u_password.setEchoMode(QLineEdit.Password)
        self.u_role = QLineEdit(); self.u_role.setPlaceholderText("admin|user (por defecto user)")

        form_new = QFormLayout()
        form_new.addRow("username*", self.u_username)
        form_new.addRow("nombre*", self.u_nombre)
        form_new.addRow("apellido*", self.u_apellido)
        form_new.addRow("email*", self.u_email)
        form_new.addRow("password*", self.u_password)
        form_new.addRow("role", self.u_role)
        btn_create = QPushButton("Crear")
        btn_create.clicked.connect(self.create_user)
        box_new = QVBoxLayout(); box_new.addLayout(form_new); box_new.addWidget(btn_create)
        grp_new.setLayout(box_new)

        # --- Edición rápida (PUT) ---
        grp_edit = QGroupBox("Editar usuario (requiere ID seleccionado)")
        self.e_id = QLineEdit(); self.e_id.setReadOnly(True)
        self.e_nombre = QLineEdit(); self.e_apellido = QLineEdit(); self.e_email = QLineEdit()
        self.e_password = QLineEdit(); self.e_password.setEchoMode(QLineEdit.Password)
        self.e_role = QLineEdit(); self.e_role.setPlaceholderText("admin|user")
        self.e_active = QLineEdit(); self.e_active.setPlaceholderText("true|false")

        form_edit = QFormLayout()
        form_edit.addRow("id", self.e_id)
        form_edit.addRow("nombre", self.e_nombre)
        form_edit.addRow("apellido", self.e_apellido)
        form_edit.addRow("email", self.e_email)
        form_edit.addRow("password (opcional)", self.e_password)
        form_edit.addRow("role", self.e_role)
        form_edit.addRow("is_active", self.e_active)
        btn_update = QPushButton("Guardar cambios")
        btn_update.clicked.connect(self.update_user)
        box_edit = QVBoxLayout(); box_edit.addLayout(form_edit); box_edit.addWidget(btn_update)
        grp_edit.setLayout(box_edit)

        self.table.itemSelectionChanged.connect(self._on_table_select)

        lay = QVBoxLayout(self)
        lay.addWidget(btn_refresh)
        lay.addWidget(self.table)
        lay.addWidget(grp_new)
        lay.addWidget(grp_edit)

    async def _ensure_admin(self):
        me = await self.api.get_me()
        role = me.get("role", "user")
        if role != "admin":
            raise RuntimeError("Sólo un administrador puede acceder a esta sección.")

    async def load(self):
        try:
            await self._ensure_admin()
            users = await self.api.list_usuarios()
            # users: [{id, username, nombre, apellido, email, created_at, is_active, role}, ...]
            headers = ["id", "username", "nombre", "apellido", "email", "created_at", "is_active", "role"]
            self.table.setRowCount(len(users))
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            for r, u in enumerate(users):
                for c, k in enumerate(headers):
                    self.table.setItem(r, c, QTableWidgetItem(str(u.get(k, ""))))
            self.table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo listar usuarios:\n{e}")

    def _on_table_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        self.e_id.setText(self.table.item(r, 0).text())            # id
        self.e_nombre.setText(self.table.item(r, 2).text())        # nombre
        self.e_apellido.setText(self.table.item(r, 3).text())      # apellido
        self.e_email.setText(self.table.item(r, 4).text())         # email
        self.e_role.setText(self.table.item(r, 7).text())          # role
        # is_active en col 6 (no lo ponemos en el form por defecto)

    def create_user(self):
        payload = {
            "username": self.u_username.text().strip(),
            "password": self.u_password.text(),
            "nombre": self.u_nombre.text().strip(),
            "apellido": self.u_apellido.text().strip(),
            "email": self.u_email.text().strip(),
        }
        role = self.u_role.text().strip()
        if role:
            payload["role"] = role
        try:
            res = asyncio.run(self.api.create_usuario(payload))
            QMessageBox.information(self, "OK", f"Usuario creado: {res.get('username')}")
            self.u_username.clear(); self.u_password.clear()
            asyncio.run(self.load())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear:\n{e}")

    def update_user(self):
        if not self.e_id.text():
            QMessageBox.information(self, "Atención", "Seleccioná primero un usuario en la tabla.")
            return
        payload = {}
        if self.e_nombre.text().strip():   payload["nombre"] = self.e_nombre.text().strip()
        if self.e_apellido.text().strip(): payload["apellido"] = self.e_apellido.text().strip()
        if self.e_email.text().strip():    payload["email"] = self.e_email.text().strip()
        if self.e_password.text():         payload["password"] = self.e_password.text()
        if self.e_role.text().strip():     payload["role"] = self.e_role.text().strip()
        if self.e_active.text().strip():   payload["is_active"] = self.e_active.text().strip().lower() == "true"
        try:
            res = asyncio.run(self.api.update_usuario(int(self.e_id.text()), payload))
            QMessageBox.information(self, "OK", f"Actualizado: {res.get('username')}")
            asyncio.run(self.load())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar:\n{e}")


class MainWindow(QMainWindow):
    def __init__(self, username: str):
        super().__init__()
        self.setWindowTitle("FADEAPI Client")
        self.api = ApiClient(username)

        tabs = QTabWidget()
        tabs.addTab(self._build_status_tab(), "Status")
        tabs.addTab(RegistrosTab(self.api), "Registros")
        tabs.addTab(UsuariosTab(self.api), "Usuarios (admin)")

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

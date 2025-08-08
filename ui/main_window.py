# ui/main_window.py
import asyncio
import numpy as np
import pyqtgraph as pg
from core.api import ApiClient
from core.workers import run_bg
from ui.about import AboutDialog
from core.__version__ import VERSION
from core.updater import check_update, open_release
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton, QLabel,
    QMessageBox, QHBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog,
    QSpinBox, QLineEdit, QFormLayout, QGroupBox, QAbstractItemView
)

# flake8: noqa: E701,E702
class RegistrosTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.limit = QSpinBox(); self.limit.setRange(1, 10000); self.limit.setValue(200)
        self.hasta = QLineEdit(); self.hasta.setPlaceholderText("YYYY-MM-DDTHH:MM:SS (opcional)")

        btn_refresh = QPushButton("Actualizar")
        btn_csv     = QPushButton("Descargar CSV")
        btn_delete  = QPushButton("Borrar TODOS (admin)")

        btn_refresh.clicked.connect(self.load_async)
        btn_csv.clicked.connect(self.download_csv_async)
        btn_delete.clicked.connect(self.delete_all_async)

        top = QHBoxLayout()
        top.addWidget(QLabel("limit:")); top.addWidget(self.limit)
        top.addWidget(QLabel("hasta:")); top.addWidget(self.hasta)
        top.addStretch(1); top.addWidget(btn_refresh); top.addWidget(btn_csv); top.addWidget(btn_delete)

        # === Plot ===
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.addLegend()
        self.plot.setLabel("left", "Valor")
        self.plot.setLabel("bottom", "Tiempo")
        # Eje temporal (opcional): se puede usar DateAxisItem si preferís, por simplicidad dejamos el eje default

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.plot)   # 👈 gráfico arriba
        lay.addWidget(self.table)  # tabla abajo

    # ---------- Helpers UI-safe ----------
    def _err(self, msg: str):
        QMessageBox.critical(self, "Error", msg)

    def _update_ui_with_data(self, data: list[dict]):
        # Tabla
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

        # Plot
        self.plot.clear()
        if not data:
            return

        # Convertir ts ISO → epoch (segundos)
        def to_epoch(ts_str: str) -> float:
            from datetime import datetime, timezone
            s = ts_str.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(s)
            except ValueError:
                dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()

        xs = np.array([to_epoch(r["ts"]) for r in data], dtype=float)

        # Crear series por sensor
        for idx in range(max_s):
            ys = []
            for r in data:
                sensores = r.get("sensores", [])
                ys.append(float(sensores[idx]) if idx < len(sensores) else np.nan)
            ys = np.array(ys, dtype=float)
            self.plot.plot(xs, ys, pen=pg.intColor(idx), name=f"s{idx+1}", connect="finite")

        # Zoom a datos
        self.plot.enableAutoRange()

    # ---------- Background actions ----------
    def load_async(self):
        limit = self.limit.value()
        hasta_str = self.hasta.text().strip() or None
        # correr la corrutina en un thread:
        run_bg(lambda: asyncio.run(self.api.get_registros(limit=limit, hasta_iso=hasta_str)),
               on_result=self._update_ui_with_data,
               on_error=self._err)

    def download_csv_async(self):
        def work():
            return asyncio.run(self.api.download_csv())
        def done(content: bytes):
            path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "registros.csv", "CSV (*.csv)")
            if not path:
                return
            try:
                with open(path, "wb") as f:
                    f.write(content)
                QMessageBox.information(self, "OK", f"CSV guardado en:\n{path}")
            except Exception as e:
                self._err(str(e))
        run_bg(work, on_result=done, on_error=self._err)

    def delete_all_async(self):
        if QMessageBox.question(self, "Confirmar", "¿Eliminar TODOS los registros? Esta acción no se puede deshacer.") != QMessageBox.Yes:
            return
        run_bg(lambda: asyncio.run(self.api.delete_registros()),
               on_result=lambda _: self.load_async(),
               on_error=self._err)


class UsuariosTab(QWidget):
    def __init__(self, api: ApiClient):
        """Inicializa la pestaña de administración de usuarios.

        Args:
            api (ApiClient): Cliente de la API autenticado que se utilizará para gestionar usuarios.
        """
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
        """Verifica que el usuario actual tenga rol de administrador.

        Raises:
            RuntimeError: Si el usuario autenticado no es administrador.
        """
        me = await self.api.get_me()
        role = me.get("role", "user")
        if role != "admin":
            raise RuntimeError("Sólo un administrador puede acceder a esta sección.")

    async def load(self):
        """Obtiene la lista de usuarios desde la API y la muestra en la tabla.

        Requiere privilegios de administrador. Maneja errores mostrando un QMessageBox.

        Returns:
            None
        """
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
        """Rellena el formulario de edición con los datos del usuario seleccionado en la tabla.

        Returns:
            None
        """
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
        """Crea un nuevo usuario con los datos del formulario.

        Construye el payload, llama a la API, muestra el resultado y recarga la lista.

        Returns:
            None
        """
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
        """Actualiza el usuario seleccionado with los campos modificados en el formulario.

        Solo envía los campos presentes. Muestra el resultado y recarga la lista.

        Returns:
            None
        """
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
        """Crea la ventana principal de la aplicación.

        Configura las pestañas (Status, Registros, Usuarios), el diálogo Acerca de y
        el verificador de actualizaciones.

        Args:
            username (str): Nombre de usuario autenticado para inicializar el ApiClient.
        """
        super().__init__()
        self.setWindowTitle("FADEAPI Client")
        self.api = ApiClient(username)

        tabs = QTabWidget()
        tabs.addTab(self._build_status_tab(), "Status")
        tabs.addTab(RegistrosTab(self.api), "Registros")
        tabs.addTab(UsuariosTab(self.api), "Usuarios (admin)")

        about_btn = QPushButton("Acerca de")
        about_btn.clicked.connect(lambda: AboutDialog().exec())

        update_btn = QPushButton("Buscar actualizaciones")

        def _check_updates():
            try:
                hay, latest, url = asyncio.run(check_update(VERSION))
                if hay:
                    if QMessageBox.question(
                        self, "Actualización disponible",
                        f"Versión instalada: {VERSION}\nÚltima versión: {latest}\n\n¿Abrir la página de descarga?"
                    ) == QMessageBox.Yes:
                        open_release(url)
                else:
                    QMessageBox.information(self, "Actualizaciones", "Estás en la última versión.")
            except Exception as e:
                QMessageBox.warning(self, "Actualizaciones", f"No se pudo verificar:\n{e}")

        update_btn.clicked.connect(_check_updates)

        c = QWidget(); lay = QVBoxLayout(c)
        lay.addWidget(tabs); lay.addWidget(about_btn)
        lay.addWidget(update_btn)
        self.setCentralWidget(c)

        

    def _build_status_tab(self):
        """Construye y devuelve la pestaña de estado del servidor.

        Incluye un botón para consultar /status y una etiqueta para mostrar la respuesta.

        Returns:
            QWidget: Contenedor con controles de la pestaña de estado.
        """
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

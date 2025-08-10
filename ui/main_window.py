# ui/main_window.py
import asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+; en Windows conviene instalar 'tzdata'
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QSpinBox,
    QLineEdit,
    QFormLayout,
    QGroupBox,
    QAbstractItemView,
    QRadioButton,
    QCheckBox,
    QTextEdit,
    QDialog,
)

from core.api import ApiClient
from core.workers import run_bg
from core.__version__ import VERSION
from core.updater import check_update, download_and_get_path_sync, run_installer
from ui.about import AboutDialog

from PySide6.QtCore import Signal
from core.config import Config



# flake8: noqa: E701,E702
class GraficoTab(QWidget):
    """Pestaña de gráfico con Matplotlib ocupando todo el espacio."""
    def __init__(self):
        super().__init__()
        self.fig = Figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(self.canvas)

    @staticmethod
    def _parse_iso(ts_str: str) -> datetime:
        s = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def update_plot(self, data: list[dict]):
        """Redibuja todas las series con los datos provistos (timezone Córdoba)."""
        tz = ZoneInfo("America/Argentina/Cordoba")

        self.fig.clear()
        ax = self.fig.add_subplot(111)

        if not data:
            ax.set_xlabel("Tiempo")
            ax.set_ylabel("Valor")
            ax.grid(True)
            self.canvas.draw()
            return

        max_s = max((len(r.get("sensores", [])) for r in data), default=0)
        if max_s == 0:
            self.canvas.draw()
            return

        # Timestamps → datetime local Córdoba
        x_dt_local = [self._parse_iso(r["ts"]).astimezone(tz) for r in data]
        x_num = mdates.date2num(x_dt_local)

        # Curvas
        for idx in range(max_s):
            y_vals = []
            for r in data:
                sensores = r.get("sensores", [])
                y_vals.append(sensores[idx] if idx < len(sensores) else None)
            ax.plot_date(x_num, y_vals, "-", marker="o", label=f"s{idx+1}")

        # Formato de fechas: locator+Concise para que no ensucie
        locator = mdates.AutoDateLocator(tz=tz)
        formatter = mdates.ConciseDateFormatter(locator, tz=tz)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

        ax.set_ylabel("Valor")
        ax.set_xlabel("Tiempo (Córdoba)")
        ax.grid(True)
        ax.legend()

        # Padding Y
        try:
            ymin, ymax = ax.get_ybound()
            if ymin == ymax:
                ymin, ymax = ymin - 0.5, ymax + 0.5
            ax.set_ybound(ymin - 0.05*(ymax-ymin), ymax + 0.05*(ymax-ymin))
        except Exception:
            pass

        self.canvas.draw()


class StatusViewDialog(QDialog):
    """Dialogo formateado para mostrar el /status de la API."""
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Estado del servidor")
        self.resize(560, 420)

        lay = QVBoxLayout(self)

        # --- resumen clave-valor (si existen)
        api_name        = data.get("api_name", "—")
        version     = data.get("version", "—")
        status       = data.get("status", "—")
        hostname    = data.get("server_name", "—")
        server_time = data.get("server_time", data.get("time", "—"))

        resumen_html = (
            f"<h3 style='margin:0'>FAdeAPI</h3>"
            f"<div style='margin-top:6px'>"
            f"<b>Nombre de la API:</b> {api_name}<br>"
            f"<b>Versión:</b> {version}<br>"
            f"<b>Estado:</b> {status}<br>"
            f"<b>Hostname:</b> {hostname}<br>"
            f"<b>Hora del servidor:</b> {server_time}"
            f"</div>"
        )
        lay.addWidget(QLabel(resumen_html))

        # --- JSON completo, bonito y scrolleable
        import json
        raw = QTextEdit()
        raw.setReadOnly(True)
        raw.setFontFamily("Consolas, Menlo, monospace")
        raw.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
        lay.addWidget(raw)

        btns = QHBoxLayout()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        btns.addStretch(1); btns.addWidget(btn_cerrar)
        lay.addLayout(btns)


class ConfigTab(QWidget):
    
    theme_changed = Signal(str)   # "light" | "dark"
    
    """Preferencias del usuario."""
    def __init__(self):
        super().__init__()
        self.cfg = Config()

        # === API destino ===
        grp_api = QGroupBox("API destino")
        self.rb_cloud = QRadioButton("Cloud ☁")
        self.rb_localhost = QRadioButton(f"Localhost ({self.cfg.localhost_url()})")
        self.rb_custom    = QRadioButton("Personalizada")
        self.ed_custom    = QLineEdit(); self.ed_custom.setPlaceholderText("https://mi-servidor/api/ ...")

        env = self.cfg.get_api_env()
        if env == "localhost":
            self.rb_localhost.setChecked(True)
        elif env == "custom":
            self.rb_custom.setChecked(True)
            self.ed_custom.setText(self.cfg.base_url())
        else:
            self.rb_cloud.setChecked(True)

        # Habilitar campo custom only si corresponde
        def _toggle_custom():
            self.ed_custom.setEnabled(self.rb_custom.isChecked())
        _toggle_custom()
        self.rb_custom.toggled.connect(_toggle_custom)

        lay_api = QFormLayout()
        lay_api.addRow(self.rb_cloud)
        lay_api.addRow(self.rb_localhost)
        lay_api.addRow(self.rb_custom, self.ed_custom)
        grp_api.setLayout(lay_api)

        # === Preferencias varias ===
        grp_prefs = QGroupBox("Preferencias")
        self.cb_auto_update = QCheckBox("Buscar actualizaciones al iniciar")
        self.cb_auto_update.setChecked(self.cfg.get_auto_check_updates())

        self.sp_limit = QSpinBox(); self.sp_limit.setRange(1, 1_000_000); self.sp_limit.setValue(self.cfg.get_default_limit())
        self.sp_rem   = QSpinBox(); self.sp_rem.setRange(1, 365); self.sp_rem.setValue(self.cfg.get_remember_days_default())

        lay_prefs = QFormLayout()
        lay_prefs.addRow("Límite por defecto (Registros)", self.sp_limit)
        lay_prefs.addRow("Recordarme (días)", self.sp_rem)
        lay_prefs.addRow(self.cb_auto_update)
        grp_prefs.setLayout(lay_prefs)
        
        # === Tema ===
        grp_theme = QGroupBox("Tema de la interfaz")
        self.rb_light = QRadioButton("Claro")
        self.rb_dark = QRadioButton("Oscuro")

        theme = self.cfg.get_theme()
        if theme == "dark":
            self.rb_dark.setChecked(True)
        else:
            self.rb_light.setChecked(True)

        lay_theme = QVBoxLayout()
        lay_theme.addWidget(self.rb_light)
        lay_theme.addWidget(self.rb_dark)
        grp_theme.setLayout(lay_theme)


        # === Botones ===
        btn_save = QPushButton("Guardar")
        btn_test = QPushButton("Probar /status")

        btn_save.clicked.connect(self._save)
        btn_test.clicked.connect(self._test_status)

        # === Layout principal ===
        root = QVBoxLayout(self)
        root.addWidget(grp_api)
        root.addWidget(grp_prefs)
        root.addWidget(grp_theme)


        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn_test)
        row.addWidget(btn_save)
        root.addLayout(row)
        root.addStretch(1)

    def _save(self):
        # API env + base_url
        if self.rb_cloud.isChecked():
            self.cfg.set_api_env("cloud")
            self.cfg.set_base_url(self.cfg.cloud_url())
        elif self.rb_localhost.isChecked():
            self.cfg.set_api_env("localhost")
            self.cfg.set_base_url(self.cfg.localhost_url())
        else:
            url = (self.ed_custom.text() or "").strip()
            if not url:
                QMessageBox.warning(self, "Configuración", "Ingresá una URL para el modo personalizado.")
                return
            self.cfg.set_api_env("custom")
            self.cfg.set_base_url(url)

        # Prefs
        self.cfg.set_auto_check_updates(self.cb_auto_update.isChecked())
        self.cfg.set_default_limit(int(self.sp_limit.value()))
        self.cfg.set_remember_days_default(int(self.sp_rem.value()))
        # Tema
        theme = "dark" if self.rb_dark.isChecked() else "light"
        self.cfg.set_theme(theme)
        self.theme_changed.emit(theme)   # 👈 avisamos al resto de la app


        QMessageBox.information(self, "Configuración", "Preferencias guardadas.\nLos cambios aplican a nuevas conexiones.")

    def _test_status(self):
        # pequeño test síncrono usando httpx (sin ApiClient para no depender de auth)
        try:
            import httpx
            url = self.cfg.base_url()
            with httpx.Client(base_url=url, timeout=10, follow_redirects=True) as c:
                r = c.get("status")
                r.raise_for_status()
                data = r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text}
            # Mostrar con formato lindo
            dlg = StatusViewDialog(data, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Status ERROR", str(e))



class RegistrosTab(QWidget):
    """Pestaña de registros: SOLO la tabla. Emite señal con los datos para el gráfico."""
    data_updated = Signal(list)  # emite la lista de dicts [{ts, sensores}, ...]

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._data: list[dict] = []  # cache local ordenado asc por ts

        # --- Tabla ---
        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # --- Controles ---
        self.limit = QSpinBox()
        self.limit.setRange(1, 1_000_000)
        # self.limit.setValue(10_000)
        self.limit.setValue(Config().get_default_limit())
        self.hasta = QLineEdit(); self.hasta.setPlaceholderText("YYYY-MM-DDTHH:MM:SS (opcional)")

        btn_refresh = QPushButton("Actualizar (incremental)")
        btn_csv     = QPushButton("Descargar CSV")
        btn_delete  = QPushButton("Borrar TODOS (admin)")
        btn_refresh.clicked.connect(self.load_async)
        btn_csv.clicked.connect(self.download_csv_async)
        btn_delete.clicked.connect(self.delete_all_async)

        top = QHBoxLayout()
        top.addWidget(QLabel("limit:")); top.addWidget(self.limit)
        top.addWidget(QLabel("hasta:")); top.addWidget(self.hasta)
        top.addStretch(1); top.addWidget(btn_refresh); top.addWidget(btn_csv); top.addWidget(btn_delete)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table)  # 👈 tabla ocupa todo

    # ----------------- helpers -----------------
    def _err(self, msg: str):
        QMessageBox.critical(self, "Error", msg)

    @staticmethod
    def _parse_iso(ts_str: str) -> datetime:
        s = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _max_ts_plus_eps_iso(self) -> str | None:
        if not self._data:
            return None
        mx = max(self._parse_iso(r["ts"]) for r in self._data if r.get("ts"))
        return (mx + timedelta(microseconds=1)).isoformat()

    def _merge_new_data(self, new: list[dict]):
        if not new:
            return
        seen = {r["ts"] for r in self._data if r.get("ts")}
        for r in new:
            ts = r.get("ts")
            if ts and ts not in seen:
                self._data.append(r)
        self._data.sort(key=lambda r: self._parse_iso(r["ts"]))  # ascendente

    # ----------------- UI update -----------------
    def _update_table(self):
        data = self._data
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

        # Notificar a la pestaña de Gráfico
        self.data_updated.emit(self._data)

    # ----------------- acciones en background -----------------
    def load_async(self):
        limit = self.limit.value()
        hasta_str = self.hasta.text().strip() or None
        desde_iso = self._max_ts_plus_eps_iso()  # incremental

        def work():
            # usa API con desde/hasta
            return asyncio.run(self.api.get_registros(limit=limit, desde_iso=desde_iso, hasta_iso=hasta_str))

        def done(new_data: list[dict]):
            self._merge_new_data(new_data)
            self._update_table()

        run_bg(work, on_result=done, on_error=self._err)

    def download_csv_async(self):
        def work(): return asyncio.run(self.api.download_csv())
        def done(content: bytes):
            path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "registros.csv", "CSV (*.csv)")
            if not path: return
            try:
                with open(path, "wb") as f: f.write(content)
                QMessageBox.information(self, "OK", f"CSV guardado en:\n{path}")
            except Exception as e:
                self._err(str(e))
        run_bg(work, on_result=done, on_error=self._err)

    def delete_all_async(self):
        if QMessageBox.question(self, "Confirmar", "¿Eliminar TODOS los registros? Esta acción no se puede deshacer.") != QMessageBox.Yes:
            return
        def done(_):
            self._data.clear()
            self._update_table()
        run_bg(lambda: asyncio.run(self.api.delete_registros()),
               on_result=done, on_error=self._err)


class MainWindow(QMainWindow):
    def __init__(self, username: str, on_logout=None):
        """Crea la ventana principal de la aplicación.

        Configura las pestañas (Status, Registros, Usuarios), el diálogo Acerca de y
        el verificador de actualizaciones.

        Args:
            username (str): Nombre de usuario autenticado para inicializar el ApiClient.
        """
        super().__init__()
        self.setWindowTitle("FAdeAPI Client")
        self.username = username              # 👈 guardamos usuario actual
        self.on_logout = on_logout            # 👈 callback para volver al login
        self.api = ApiClient(username)

        tabs = QTabWidget()
        self.reg_tab = RegistrosTab(self.api)
        self.graph_tab = GraficoTab()
        config_tab = ConfigTab()
        
        # Conectar: cuando llegan/ cambian datos en "Registros", actualizamos "Gráfico"
        self.reg_tab.data_updated.connect(self.graph_tab.update_plot)
        config_tab.theme_changed.connect(lambda _: self._apply_theme())
        
        self._apply_theme()

        tabs.addTab(self.reg_tab, "Registros")
        tabs.addTab(self.graph_tab, "Gráfico")
        tabs.addTab(UsuariosTab(self.api), "Usuarios (admin)")
        tabs.addTab(ConfigTab(), "Configuración")

        about_btn = QPushButton("Acerca de")
        about_btn.clicked.connect(lambda: AboutDialog().exec())

        logout_btn = QPushButton("Cerrar sesión")
        
        def _logout():
            from core.auth import delete_tokens
            from core.config import Config
            try:
                delete_tokens(self.username)
                Config().clear_remember(self.username)
            except Exception:
                pass
            QMessageBox.information(self, "Sesión cerrada", "Se cerró la sesión. Volverás a la pantalla de login.")
            # cerrar esta ventana y disparar callback
            if callable(self.on_logout):
                self.close()
                self.on_logout()
            else:
                self.close()

        logout_btn.clicked.connect(_logout)

        update_btn = QPushButton("Buscar actualizaciones")

        def _do_update_check_and_run():
            try:
                hay, latest = asyncio.run(check_update(VERSION))
                if not hay:
                    QMessageBox.information(self, "Actualizaciones", f"Estás en la última versión ({VERSION}).")
                    return

                if QMessageBox.question(
                    self, "Actualizar",
                    f"Versión instalada: {VERSION}\nNueva versión disponible: {latest}\n\n¿Descargar e instalar ahora?"
                ) != QMessageBox.Yes:
                    return

                # Descarga en background
                def work():
                    # descarga asset y devuelve la ruta local
                    return download_and_get_path_sync(latest)

                def done(path: str):
                    try:
                        # Lanzar instalador y cerrar app
                        run_installer(path)
                        QMessageBox.information(self, "Actualización",
                                                "Se lanzó el instalador. La aplicación se cerrará ahora.")
                    except Exception as e:
                        QMessageBox.critical(self, "Actualización", f"No se pudo lanzar el instalador:\n{e}")
                        return
                    # cerrar UI
                    from PySide6.QtWidgets import QApplication
                    QApplication.quit()

                run_bg(work, on_result=done, on_error=lambda err: QMessageBox.critical(self, "Actualización", err))

            except Exception as e:
                QMessageBox.warning(self, "Actualizaciones", f"No se pudo verificar:\n{e}")

        update_btn.clicked.connect(_do_update_check_and_run)

        c = QWidget(); lay = QVBoxLayout(c)
        
        lay.addWidget(tabs)
        lay.addWidget(about_btn)
        lay.addWidget(update_btn)
        lay.addWidget(logout_btn)     
        
        self.setCentralWidget(c)
        
        # Auto-check de actualizaciones al iniciar
        if Config().get_auto_check_updates():
            def _silent_check():
                try:
                    hay, latest = asyncio.run(check_update(VERSION))
                    if hay:
                        # Notificación muy sutil (no intrusiva)
                        QMessageBox.information(self, "Actualización disponible",
                            f"Hay una nueva versión: {latest}.\nUsá el botón 'Buscar actualizaciones' para descargarla.")
                except Exception:
                    pass
                
            run_bg(_silent_check)
        
    def _apply_theme(self):
            theme = Config().get_theme()
            if theme == "dark":
                dark_palette = self._make_dark_palette()
                self.setPalette(dark_palette)
            else:
                self.setPalette(self.style().standardPalette())

    def _make_dark_palette(self):
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        return palette


class UsuariosTab(QWidget):
    def __init__(self, api: ApiClient):
        """Pestaña de administración de usuarios (100% no bloqueante)."""
        super().__init__()
        self.api = api

        # --- Lista ---
        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        btn_refresh = QPushButton("Actualizar lista")
        btn_refresh.clicked.connect(self.load_async)

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
        btn_create.clicked.connect(self.create_user_async)
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
        btn_update.clicked.connect(self.update_user_async)
        box_edit = QVBoxLayout(); box_edit.addLayout(form_edit); box_edit.addWidget(btn_update)
        grp_edit.setLayout(box_edit)

        self.table.itemSelectionChanged.connect(self._on_table_select)

        lay = QVBoxLayout(self)
        lay.addWidget(btn_refresh)
        lay.addWidget(self.table)
        lay.addWidget(grp_new)
        lay.addWidget(grp_edit)

    # ---------- Helpers UI ----------
    def _err(self, msg: str):
        QMessageBox.critical(self, "Error", msg)

    def _fill_table(self, users: list[dict]):
        headers = ["id", "username", "nombre", "apellido", "email", "created_at", "is_active", "role"]
        self.table.setRowCount(len(users))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        for r, u in enumerate(users):
            for c, k in enumerate(headers):
                self.table.setItem(r, c, QTableWidgetItem(str(u.get(k, ""))))
        self.table.resizeColumnsToContents()

    # ---------- Background actions ----------
    def load_async(self):
        """Lista usuarios (verifica admin) en background."""
        def work():
            # Ejecuta flujo async dentro del worker
            async def flow():
                me = await self.api.get_me()
                if me.get("role") != "admin":
                    raise RuntimeError("Sólo un administrador puede acceder a esta sección.")
                return await self.api.list_usuarios()
            return asyncio.run(flow())

        run_bg(work, on_result=self._fill_table, on_error=self._err)

    def create_user_async(self):
        """Crea usuario en background y refresca la lista."""
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

        def work():
            async def flow():
                # opcional: validar admin antes de crear
                me = await self.api.get_me()
                if me.get("role") != "admin":
                    raise RuntimeError("Sólo un administrador puede crear usuarios.")
                return await self.api.create_usuario(payload)
            return asyncio.run(flow())

        def done(res: dict):
            QMessageBox.information(self, "OK", f"Usuario creado: {res.get('username')}")
            self.u_username.clear(); self.u_password.clear()
            self.load_async()

        run_bg(work, on_result=done, on_error=self._err)

    def update_user_async(self):
        """Actualiza usuario en background y refresca la lista."""
        if not self.e_id.text():
            QMessageBox.information(self, "Atención", "Seleccioná primero un usuario en la tabla.")
            return
        payload: dict = {}
        if self.e_nombre.text().strip():   payload["nombre"] = self.e_nombre.text().strip()
        if self.e_apellido.text().strip(): payload["apellido"] = self.e_apellido.text().strip()
        if self.e_email.text().strip():    payload["email"] = self.e_email.text().strip()
        if self.e_password.text():         payload["password"] = self.e_password.text()
        if self.e_role.text().strip():     payload["role"] = self.e_role.text().strip()
        if self.e_active.text().strip():   payload["is_active"] = self.e_active.text().strip().lower() == "true"

        user_id = int(self.e_id.text())

        def work():
            async def flow():
                me = await self.api.get_me()
                if me.get("role") != "admin":
                    raise RuntimeError("Sólo un administrador puede actualizar usuarios.")
                return await self.api.update_usuario(user_id, payload)
            return asyncio.run(flow())

        def done(res: dict):
            QMessageBox.information(self, "OK", f"Actualizado: {res.get('username')}")
            self.load_async()

        run_bg(work, on_result=done, on_error=self._err)

    # ---------- UI wiring ----------
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

# core/api.py
import httpx
from core.config import Config
from core.auth import load_tokens, refresh, save_tokens

class ApiClient:
    def __init__(self, username: str):
        """Inicializa el cliente de la API con configuración y tokens.

        Args:
            username (str): Nombre de usuario con el que se asocian los tokens.
        """
        self.cfg = Config()
        self.username = username
        self._access, self._refresh = load_tokens(username)

    @property
    def base_url(self) -> str:
        """Obtiene la URL base asegurando la barra final.

        Returns:
            str: URL base de la API terminada en '/'.
        """
        url = self.cfg.base_url()
        return url if url.endswith("/") else url + "/"

    async def _ensure_token(self, r: httpx.Response) -> bool:
        """Refresca el token de acceso si la respuesta fue 401 y existe refresh token.

        Args:
            r (httpx.Response): Respuesta HTTP que originó el chequeo.

        Returns:
            bool: True si se refrescó el token y se guardó; False en caso contrario.

        Raises:
            Exception: Si falla el flujo de refresh (propaga excepciones de red).
        """
        if r.status_code != 401 or not self._refresh:
            return False
        new_access, new_refresh = await refresh(self.base_url, self._refresh)
        self._access, self._refresh = new_access, new_refresh
        save_tokens(self.username, new_access, new_refresh)
        return True

    async def request(self, method: str, path: str, **kwargs):
        """Realiza una solicitud HTTP autenticada y reintenta tras refrescar token si es 401.

        Args:
            method (str): Método HTTP (GET, POST, etc.).
            path (str): Ruta relativa dentro de la API.
            **kwargs: Parámetros adicionales aceptados por httpx.AsyncClient.request.

        Returns:
            httpx.Response: Respuesta HTTP con estado exitoso.

        Raises:
            httpx.HTTPStatusError: Si la respuesta final no es exitosa.
            Exception: Errores de red u otros durante la solicitud.
        """
        headers = kwargs.pop("headers", {})
        if self._access:
            headers["Authorization"] = f"Bearer {self._access}"
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60, follow_redirects=True) as c:
            r = await c.request(method, path, headers=headers, **kwargs)
            if r.status_code == 401 and await self._ensure_token(r):
                headers["Authorization"] = f"Bearer {self._access}"
                r = await c.request(method, path, headers=headers, **kwargs)
            r.raise_for_status()
            return r

    # -------- Registros --------
    async def get_registros(self, limit: int = 100, desde_iso: str | None = None, hasta_iso: str | None = None):
        """Obtiene registros con paginado y filtro opcional por fecha/hora.

        Args:
            limit (int): Cantidad máxima de registros a devolver.
            desde_iso (str | None): Fecha/hora ISO límite inferior (opcional).
            hasta_iso (str | None): Fecha/hora ISO límite superior (opcional).

        Returns:
            list[dict]: Lista de registros con campos como 'ts' y 'sensores'.
        """
        params = {"limit": limit}
        if desde_iso:
            params["desde"] = desde_iso
        if hasta_iso:
            params["hasta"] = hasta_iso
        r = await self.request("GET", "registros/", params=params)
        return r.json()

    async def download_csv(self) -> bytes:
        """Descarga el CSV de registros.

        Returns:
            bytes: Contenido del archivo CSV.
        """
        r = await self.request("GET", "registros/csv")
        return r.content

    async def delete_registros(self):
        """Elimina todos los registros.

        Returns:
            dict: Respuesta del servidor con el resultado de la operación.
        """
        return (await self.request("DELETE", "registros/")).json()

    # -------- Usuarios --------
    async def get_me(self):
        """Obtiene los datos del usuario autenticado.

        Returns:
            dict: Información del usuario actual.
        """
        r = await self.request("GET", "usuarios/me")
        return r.json()

    async def list_usuarios(self):
        """Lista todos los usuarios (requiere permisos adecuados).

        Returns:
            list[dict]: Lista de usuarios.
        """
        r = await self.request("GET", "usuarios/")
        return r.json()

    async def create_usuario(self, payload: dict):
        """Crea un nuevo usuario.

        Args:
            payload (dict): Datos del usuario a crear.

        Returns:
            dict: Usuario creado devuelto por la API.
        """
        r = await self.request("POST", "usuarios/", json=payload)
        return r.json()

    async def update_usuario(self, user_id: int, payload: dict):
        """Actualiza un usuario existente por ID.

        Args:
            user_id (int): Identificador del usuario.
            payload (dict): Campos a actualizar.

        Returns:
            dict: Usuario actualizado devuelto por la API.
        """
        r = await self.request("PUT", f"usuarios/{user_id}", json=payload)
        return r.json()
    

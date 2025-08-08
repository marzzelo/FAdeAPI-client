# core/api.py
import httpx
from core.config import Config
from core.auth import load_tokens, refresh, save_tokens

class ApiClient:
    def __init__(self, username: str):
        self.cfg = Config()
        self.username = username
        self._access, self._refresh = load_tokens(username)

    @property
    def base_url(self) -> str:
        url = self.cfg.base_url()
        return url if url.endswith("/") else url + "/"

    async def _ensure_token(self, r: httpx.Response) -> bool:
        if r.status_code != 401 or not self._refresh:
            return False
        new_access, new_refresh = await refresh(self.base_url, self._refresh)
        self._access, self._refresh = new_access, new_refresh
        save_tokens(self.username, new_access, new_refresh)
        return True

    async def request(self, method: str, path: str, **kwargs):
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
    async def get_registros(self, limit: int = 50, hasta_iso: str | None = None):
        params = {"limit": limit}
        if hasta_iso:
            params["hasta"] = hasta_iso
        r = await self.request("GET", "registros/", params=params)
        return r.json()  # [{ts, sensores}, ...]

    async def download_csv(self) -> bytes:
        r = await self.request("GET", "registros/csv")
        return r.content

    async def delete_registros(self):
        return (await self.request("DELETE", "registros/")).json()

    # -------- Usuarios --------
    async def get_me(self):
        r = await self.request("GET", "usuarios/me")
        return r.json()

    async def list_usuarios(self):
        r = await self.request("GET", "usuarios/")
        return r.json()

    async def create_usuario(self, payload: dict):
        r = await self.request("POST", "usuarios/", json=payload)
        return r.json()

    async def update_usuario(self, user_id: int, payload: dict):
        r = await self.request("PUT", f"usuarios/{user_id}", json=payload)
        return r.json()

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
        # Si 401, intenta refrescar
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
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as c:
            r = await c.request(method, path, headers=headers, **kwargs)
            if r.status_code == 401 and await self._ensure_token(r):
                headers["Authorization"] = f"Bearer {self._access}"
                r = await c.request(method, path, headers=headers, **kwargs)
            r.raise_for_status()
            return r

import httpx, webbrowser
from packaging.version import Version
from core.__version__ import VERSION

GITHUB_API = "https://api.github.com/repos/<TU_USUARIO>/<TU_REPO_CLIENTE>/releases/latest"

async def check_update() -> tuple[bool, str, str]:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(GITHUB_API)
        r.raise_for_status()
        data = r.json()
        latest = data["tag_name"].lstrip("v")
        url = data["html_url"]
        return Version(latest) > Version(VERSION), latest, url

def open_release(url: str):
    webbrowser.open(url)

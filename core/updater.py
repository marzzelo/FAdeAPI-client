import httpx, webbrowser
from packaging.version import Version
from core.__version__ import VERSION

REPO = "marzzelo/FAdeAPI-client"
GITHUB_API = f"https://api.github.com/repos/{REPO}/releases/latest"


async def check_update(current_version: str) -> tuple[bool, str, str]:
    """
    Devuelve (hay_update, latest_version, url_release)
    """
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        r = await c.get(GITHUB_API)
        r.raise_for_status()
        data = r.json()
        # acepta tags tipo "v0.1.2" o "0.1.2"
        latest = str(data.get("tag_name", "")).lstrip("v")
        url = data.get("html_url", "")
        try:
            return Version(latest) > Version(current_version), latest, url
        except Exception:
            return False, latest or "", url or ""

def open_release(url: str):
    if url:
        webbrowser.open(url)
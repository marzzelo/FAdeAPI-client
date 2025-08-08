# core/updater.py
import httpx, webbrowser
from packaging.version import Version

REPO = "marzzelo/FAdeAPI-client"  # 👈 repo del CLIENTE
API_LATEST  = f"https://api.github.com/repos/{REPO}/releases/latest"
API_LIST    = f"https://api.github.com/repos/{REPO}/releases"  # incluye prereleases y draft (estos últimos sin assets públicos)
# results in https://api.github.com/repos/marzzelo/FAdeAPI-client/releases/latest

def _parse_version(tag: str) -> str:
    return str(tag or "").lstrip("v").strip()

async def check_update(current_version: str) -> tuple[bool, str, str]:
    """
    Devuelve (hay_update, latest_version, url_a_mostrar).
    - Intenta /releases/latest
    - Si 404, cae a /releases y toma el primero no-draft (aunque sea prerelease)
    """
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        r = await c.get(API_LATEST)
        if r.status_code == 404:
            # No hay releases "published" => buscar el primero de la lista (prerelease OK)
            rl = await c.get(API_LIST)
            rl.raise_for_status()
            releases = rl.json()
            # elegir el primero que NO sea draft; si todos draft, no hay update público
            first = next((x for x in releases if not x.get("draft")), None)
            if not first:
                return False, "", ""    
            latest = _parse_version(first.get("tag_name", ""))
            url = first.get("html_url") or f"https://github.com/{REPO}/releases"
            try:
                return Version(latest) > Version(current_version), latest, url
            except Exception:
                return False, latest, url

        r.raise_for_status()
        data = r.json()
        latest = _parse_version(data.get("tag_name", ""))
        url = data.get("html_url") or f"https://github.com/{REPO}/releases"
        try:
            return Version(latest) > Version(current_version), latest, url
        except Exception:
            return False, latest, url

def open_release(url: str):
    if url:
        webbrowser.open(url)

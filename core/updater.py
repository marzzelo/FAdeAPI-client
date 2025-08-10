# core/updater.py
from __future__ import annotations
import os
import re
import subprocess
import sys
import asyncio
from typing import Optional
import httpx
from packaging.version import Version

# En entornos corporativos con inspección TLS
try:
    import truststore 
    truststore.inject_into_ssl()
except Exception:
    pass

REPO = "marzzelo/FAdeAPI-client"
API_LATEST  = f"https://api.github.com/repos/{REPO}/releases/latest"
API_LIST    = f"https://api.github.com/repos/{REPO}/releases"

def _parse_version(tag: str) -> str:
    return str(tag or "").lstrip("v").strip()

async def _get_latest_release_json() -> dict:
    """Devuelve el JSON del release más reciente. Fallback a la lista si /latest no existe."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(API_LATEST)
        if r.status_code == 404:
            rl = await c.get(API_LIST)
            rl.raise_for_status()
            releases = [x for x in rl.json() if not x.get("draft")]
            if not releases:
                raise RuntimeError("No hay releases públicos")
            return releases[0]
        r.raise_for_status()
        return r.json()

async def check_update(current_version: str) -> tuple[bool, str]:
    """¿Hay una versión más nueva? -> (True/False, latest_str)"""
    j = await _get_latest_release_json()
    latest = _parse_version(j.get("tag_name", ""))
    try:
        return Version(latest) > Version(current_version), latest
    except Exception:
        # Si el parse falla, no forzamos update
        return False, latest

def _pick_asset(assets: list[dict], version: str, prefer_installer: bool = True) -> Optional[dict]:
    """Elige el asset .exe (installer) o, si no hay, el .zip."""
    ver_pat = re.escape(version)
    exe_re  = re.compile(rf"setup[_-]?{ver_pat}.*\.exe$", re.IGNORECASE)
    zip_re  = re.compile(rf"v?{ver_pat}.*\.zip$", re.IGNORECASE)

    exe = None
    zip_ = None
    for a in assets or []:
        name = a.get("name","")
        if exe_re.search(name) or ("setup" in name.lower() and name.lower().endswith(".exe")):
            exe = a
        if zip_re.search(name) or (name.lower().endswith(".zip") and version in name):
            zip_ = a

    if prefer_installer and exe:
        return exe
    return exe or zip_

def _updates_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "FADEAPI-Client", "updates")
    os.makedirs(d, exist_ok=True)
    return d

async def download_latest_asset(version: str) -> str:
    """Descarga el asset preferido del release más reciente y devuelve la ruta local."""
    j = await _get_latest_release_json()
    assets = j.get("assets") or []
    a = _pick_asset(assets, version, prefer_installer=True)
    if not a:
        raise RuntimeError("No se encontró asset .exe ni .zip para esta versión")

    url = a.get("browser_download_url")
    name = a.get("name") or f"FADEAPI-Client_{version}.bin"
    out_path = os.path.join(_updates_dir(), name)

    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as c:
        async with c.stream("GET", url) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                async for chunk in r.aiter_bytes(1024 * 128):
                    f.write(chunk)

    return out_path

def run_installer(path: str):
    """Ejecuta el instalador (si es .exe, en modo silencioso) y sale de la app."""
    try:
        if path.lower().endswith(".exe"):
            # Flags comunes de Inno Setup silencioso
            subprocess.Popen([path, "/SILENT", "/NORESTART"], close_fds=True)
        else:
            # Si fuera ZIP, abrimos carpeta para que el usuario lo instale/copìe
            folder = os.path.dirname(path)
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
        # Nota: el cierre de la app lo maneja la UI llamando a QApplication.quit()
    except Exception as e:
        raise RuntimeError(f"No se pudo ejecutar el instalador: {e}")

# Helpers para la UI (sincronizar con run_bg desde Qt)
def download_and_get_path_sync(version: str) -> str:
    return asyncio.run(download_latest_asset(version))

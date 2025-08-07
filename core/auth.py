import keyring
import time
from typing import Optional
import httpx

SERVICE = "FADEAPI-Client"

def save_tokens(username: str, access: str, refresh: str):
    keyring.set_password(SERVICE, f"{username}:access", access)
    keyring.set_password(SERVICE, f"{username}:refresh", refresh)

def load_tokens(username: str) -> tuple[Optional[str], Optional[str]]:
    return (
        keyring.get_password(SERVICE, f"{username}:access"),
        keyring.get_password(SERVICE, f"{username}:refresh"),
    )

async def login(base_url: str, username: str, password: str) -> tuple[str, str]:
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as c:
        r = await c.post("token", data={"username": username, "password": password})
        r.raise_for_status()
        j = r.json()
        return j["access_token"], j["refresh_token"]

async def refresh(base_url: str, refresh_token: str) -> tuple[str, str]:
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as c:
        r = await c.post("token/refresh", json={"refresh_token": refresh_token})
        r.raise_for_status()
        j = r.json()
        return j["access_token"], j["refresh_token"]

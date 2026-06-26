import time
import requests
from config import AUTH_URL, CLIENT_ID, CLIENT_SECRET

_token_cache = {"token": None, "expires_at": 0}


def get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    response = requests.get(AUTH_URL, params={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, timeout=15)
    response.raise_for_status()
    # API devuelve el token como texto plano (UUID), no como JSON
    _token_cache["token"] = response.text.strip()
    _token_cache["expires_at"] = time.time() + 3600 - 60

    return _token_cache["token"]

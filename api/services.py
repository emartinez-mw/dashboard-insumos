from datetime import date
import requests
import pandas as pd
from api.auth import get_token
from config import (
    STOCK_URL, ANALISIS_LOTE_URL, PENDIENTE_URL,
    STOCK_FIXED_PARAMS, ANALISIS_LOTE_FIXED_PARAMS, PENDIENTE_FIXED_PARAMS,
)

_ANALISIS_LOTE_GROUP_COLS = [
    "LABORPRODUCTO", "EMPRESA", "EMPRESAPADRE",
    "FAMILIA", "SUBFAMILIA", "PRINCIPIOACTIVO", "FORMULACION", "CENTROLOGISTICO",
]


def _fetch(url: str, params: dict) -> pd.DataFrame:
    token = get_token()
    all_params = {"ACCESS_TOKEN": token, **params}
    response = requests.get(url, params=all_params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    data = payload if isinstance(payload, list) else payload.get("data", [])
    return pd.DataFrame(data)


def fetch_stock() -> pd.DataFrame:
    return _fetch(STOCK_URL, STOCK_FIXED_PARAMS)


def fetch_analisis_lote() -> pd.DataFrame:
    from api.db import fetch_analisis_lote_db
    return fetch_analisis_lote_db()


def fetch_analisis_lote_monthly() -> pd.DataFrame:
    from api.db import fetch_analisis_lote_monthly_db
    return fetch_analisis_lote_monthly_db()


def fetch_analisis_lote_raw() -> pd.DataFrame:
    from api.db import fetch_analisis_lote_raw_db
    return fetch_analisis_lote_raw_db()


def fetch_pendiente() -> pd.DataFrame:
    today = date.today().strftime("%Y-%m-%d")
    params = {**PENDIENTE_FIXED_PARAMS, "PARAMWEBREPORT_FechaHasta": today}
    return _fetch(PENDIENTE_URL, params)

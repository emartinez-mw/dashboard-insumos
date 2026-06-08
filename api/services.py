from datetime import date
import requests
import pandas as pd
from api.auth import get_token
from config import (
    STOCK_URL, PRESUPUESTADO_URL, PENDIENTE_URL,
    STOCK_FIXED_PARAMS, PRESUPUESTADO_FIXED_PARAMS, PENDIENTE_FIXED_PARAMS,
)


def _fetch(url: str, params: dict) -> pd.DataFrame:
    token = get_token()
    all_params = {"ACCESS_TOKEN": token, **params}
    response = requests.get(url, params=all_params)
    response.raise_for_status()
    data = response.json().get("data", [])
    return pd.DataFrame(data)


def fetch_stock() -> pd.DataFrame:
    today = date.today().strftime("%Y-%m-%d")
    params = {**STOCK_FIXED_PARAMS, "PARAMWEBREPORT_fecha": today}
    return _fetch(STOCK_URL, params)


def fetch_presupuestado() -> pd.DataFrame:
    today = date.today().strftime("%Y-%m-%d")
    params = {**PRESUPUESTADO_FIXED_PARAMS, "PARAMWEBREPORT_fechaHasta": today}
    return _fetch(PRESUPUESTADO_URL, params)


def fetch_pendiente() -> pd.DataFrame:
    today = date.today().strftime("%Y-%m-%d")
    params = {**PENDIENTE_FIXED_PARAMS, "PARAMWEBREPORT_FechaHasta": today}
    return _fetch(PENDIENTE_URL, params)

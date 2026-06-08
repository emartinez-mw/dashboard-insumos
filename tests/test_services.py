import pytest
import pandas as pd
from datetime import date
from unittest.mock import patch, MagicMock
from api.services import fetch_stock, fetch_presupuestado, fetch_pendiente


SAMPLE_RESPONSE = {
    "data": [
        {"producto": "HERBICIDA A", "empresa": "AED", "rubro": "INSAGR",
         "principio_activo": "Glifosato", "sucursal": "DUHAU", "cantidad": 100}
    ]
}


def _mock_get(url, params=None):
    mock = MagicMock()
    mock.json.return_value = SAMPLE_RESPONSE
    mock.raise_for_status.return_value = None
    return mock


def test_fetch_stock_uses_today_date():
    today = date.today().strftime("%Y-%m-%d")
    with patch("api.services.requests.get", side_effect=_mock_get) as mock_get:
        with patch("api.services.get_token", return_value="token123"):
            df = fetch_stock()
    call_params = mock_get.call_args[1]["params"]
    assert call_params["PARAMWEBREPORT_fecha"] == today
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1


def test_fetch_presupuestado_uses_today_as_hasta():
    today = date.today().strftime("%Y-%m-%d")
    with patch("api.services.requests.get", side_effect=_mock_get) as mock_get:
        with patch("api.services.get_token", return_value="token123"):
            df = fetch_presupuestado()
    call_params = mock_get.call_args[1]["params"]
    assert call_params["PARAMWEBREPORT_fechaHasta"] == today
    assert call_params["PARAMWEBREPORT_fechaDesde"] == "2025-01-01"
    assert isinstance(df, pd.DataFrame)


def test_fetch_pendiente_uses_today_as_hasta():
    today = date.today().strftime("%Y-%m-%d")
    with patch("api.services.requests.get", side_effect=_mock_get) as mock_get:
        with patch("api.services.get_token", return_value="token123"):
            df = fetch_pendiente()
    call_params = mock_get.call_args[1]["params"]
    assert call_params["PARAMWEBREPORT_FechaHasta"] == today
    assert isinstance(df, pd.DataFrame)


def test_fetch_returns_empty_dataframe_on_empty_response():
    with patch("api.services.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"data": []}
        mock_get.return_value.raise_for_status.return_value = None
        with patch("api.services.get_token", return_value="token123"):
            df = fetch_stock()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0

import pytest
import pandas as pd
from datetime import date
from unittest.mock import patch, MagicMock
from api.services import (
    fetch_stock, fetch_analisis_lote, fetch_pendiente,
    fetch_producto_id_map, fetch_relacion_principio_activo,
)


def _mock_empty(url, params=None, **kwargs):
    mock = MagicMock()
    mock.json.return_value = []
    mock.raise_for_status.return_value = None
    return mock


def test_fetch_stock_sends_only_token():
    with patch("api.services.requests.get", side_effect=_mock_empty) as mock_get:
        with patch("api.services.get_token", return_value="token123"):
            df = fetch_stock()
    call_params = mock_get.call_args[1]["params"]
    assert call_params == {"ACCESS_TOKEN": "token123"}
    assert isinstance(df, pd.DataFrame)


def test_fetch_analisis_lote_returns_dataframe_from_db():
    sample = pd.DataFrame([{
        "PRODUCTO": "HERB A", "EMPRESA": "AED", "EMPRESAPADRE": "GD",
        "FAMILIA": "F1", "SUBFAMILIA": "SF1", "PRINCIPIOACTIVO": "PA1",
        "FORMULACION": "FO1", "CENTROLOGISTICO": "CL1",
        "planificado_qty": 100.0, "ejecutado_qty": 60.0,
    }])
    with patch("api.db.fetch_analisis_lote_db", return_value=sample):
        df = fetch_analisis_lote()
    assert "planificado_qty" in df.columns
    assert "ejecutado_qty" in df.columns
    assert df["planificado_qty"].iloc[0] == 100.0


def test_fetch_analisis_lote_pasa_fecha_corte_a_la_db():
    with patch("api.db.fetch_analisis_lote_db", return_value=pd.DataFrame()) as mock_db:
        fetch_analisis_lote(fecha_corte="2026-08-15")
    mock_db.assert_called_once_with("2026-08-15")


def test_fetch_pendiente_uses_today_as_hasta():
    today = date.today().strftime("%Y-%m-%d")
    with patch("api.services.requests.get", side_effect=_mock_empty) as mock_get:
        with patch("api.services.get_token", return_value="token123"):
            df = fetch_pendiente()
    call_params = mock_get.call_args[1]["params"]
    assert call_params["PARAMWEBREPORT_FechaHasta"] == today
    assert isinstance(df, pd.DataFrame)


def test_fetch_returns_empty_dataframe_on_empty_response():
    with patch("api.services.requests.get", side_effect=_mock_empty):
        with patch("api.services.get_token", return_value="token123"):
            df = fetch_stock()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_fetch_producto_id_map_returns_dataframe_from_db():
    sample = pd.DataFrame([{"PRODUCTO": "HERB A", "PRODUCTOID": "123"}])
    with patch("api.db.fetch_producto_id_map_db", return_value=sample):
        df = fetch_producto_id_map()
    assert "PRODUCTOID" in df.columns
    assert df["PRODUCTOID"].iloc[0] == "123"


def test_fetch_relacion_principio_activo_returns_dataframe_from_db():
    sample = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0.61"}])
    with patch("api.db.fetch_relacion_principio_activo_db", return_value=sample):
        df = fetch_relacion_principio_activo()
    assert "FACTOR_PA_RAW" in df.columns
    assert df["FACTOR_PA_RAW"].iloc[0] == "0.61"

import pytest
import pandas as pd
from data.transform import merge_services, add_cobertura, prepare_anio_mes

MERGE_KEYS = ["PRODUCTO", "EMPRESA", "RUBRO"]


def _stock_row(**kwargs):
    row = {"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED", "RUBRO": "INSAGR", "CANTIDAD1": 100.0, "DEPOSITO": "DEP1"}
    row.update(kwargs)
    return row


def _presup_row(**kwargs):
    row = {"LABORPRODUCTO": "HERBICIDA A", "EMPRESA": "AED", "RUBRO": "INSAGR", "CANTIDAD": 150.0, "ANO-MES": "2026-04"}
    row.update(kwargs)
    return row


def _pendiente_row(**kwargs):
    row = {"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED", "RUBRO": "INSAGR", "PENDIENTERECEPCION": 30.0, "ANO-MES": "2026-04", "SUCURSAL": "SUC1"}
    row.update(kwargs)
    return row


def test_merge_normalizes_laborproducto():
    stock = pd.DataFrame([_stock_row()])
    presup = pd.DataFrame([_presup_row()])
    pendiente = pd.DataFrame([_pendiente_row()])

    result = merge_services(stock, presup, pendiente)

    assert "PRODUCTO" in result.columns
    assert "LABORPRODUCTO" not in result.columns
    assert len(result) == 1


def test_merge_has_qty_columns():
    stock = pd.DataFrame([_stock_row()])
    presup = pd.DataFrame([_presup_row()])
    pendiente = pd.DataFrame([_pendiente_row()])

    result = merge_services(stock, presup, pendiente)

    assert "stock_qty" in result.columns
    assert "presupuestado_qty" in result.columns
    assert "pendiente_qty" in result.columns
    assert result["stock_qty"].iloc[0] == 100.0
    assert result["presupuestado_qty"].iloc[0] == 150.0
    assert result["pendiente_qty"].iloc[0] == 30.0


def test_merge_fills_missing_with_zero():
    stock = pd.DataFrame([_stock_row()])
    presup = pd.DataFrame([_presup_row()])
    pendiente = pd.DataFrame()  # sin datos

    result = merge_services(stock, presup, pendiente)

    assert result["pendiente_qty"].iloc[0] == 0.0


def test_add_cobertura_deficit():
    df = pd.DataFrame([{"stock_qty": 100.0, "presupuestado_qty": 150.0, "pendiente_qty": 30.0}])
    result = add_cobertura(df)
    # 100 + 30 - 150 = -20
    assert result["cobertura"].iloc[0] == -20.0


def test_add_cobertura_surplus():
    df = pd.DataFrame([{"stock_qty": 200.0, "presupuestado_qty": 150.0, "pendiente_qty": 10.0}])
    result = add_cobertura(df)
    # 200 + 10 - 150 = 60
    assert result["cobertura"].iloc[0] == 60.0


def test_prepare_anio_mes_returns_three_series():
    stock = pd.DataFrame([_stock_row()])
    presup = pd.DataFrame([_presup_row()])
    pendiente = pd.DataFrame([_pendiente_row()])

    result = prepare_anio_mes(stock, presup, pendiente)

    assert isinstance(result, pd.DataFrame)
    assert "ANO-MES" in result.columns
    assert "cantidad" in result.columns
    assert "servicio" in result.columns
    assert set(result["servicio"].unique()).issubset({"Presupuestado", "Pendiente"})


def test_prepare_anio_mes_empty_when_no_date_column():
    stock = pd.DataFrame([_stock_row()])
    presup = pd.DataFrame([{"LABORPRODUCTO": "X", "EMPRESA": "AED", "RUBRO": "R", "CANTIDAD": 10.0}])  # no ANO-MES
    pendiente = pd.DataFrame([{"PRODUCTO": "X", "EMPRESA": "AED", "RUBRO": "R", "PENDIENTERECEPCION": 5.0}])  # no ANO-MES

    result = prepare_anio_mes(stock, presup, pendiente)

    assert len(result) == 0

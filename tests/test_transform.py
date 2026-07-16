import pytest
import pandas as pd
from data.transform import (
    merge_services, add_proyeccion, add_factor_principio_activo,
    apply_factor_principio_activo,
)

MERGE_KEYS = ["PRODUCTO", "EMPRESA"]


def _analisis_lote_row(**kwargs):
    row = {
        "PRODUCTO": "HERBICIDA A", "EMPRESA": "AED",
        "EMPRESAPADRE": "GD", "FAMILIA": "F1", "SUBFAMILIA": "SF1",
        "PRINCIPIOACTIVO": "PA1", "FORMULACION": "FO1", "CENTROLOGISTICO": "CL1",
        "planificado_qty": 150.0, "ejecutado_qty": 50.0,
    }
    row.update(kwargs)
    return row


def _stock_row(**kwargs):
    row = {"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED", "CANTIDAD1": 100.0}
    row.update(kwargs)
    return row


def _pendiente_row(**kwargs):
    row = {"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED", "PENDIENTERECEPCION": 30.0}
    row.update(kwargs)
    return row


def test_merge_has_all_qty_columns():
    al = pd.DataFrame([_analisis_lote_row()])
    stock = pd.DataFrame([_stock_row()])
    pendiente = pd.DataFrame([_pendiente_row()])

    result = merge_services(stock, al, pendiente)

    assert "stock_qty" in result.columns
    assert "planificado_qty" in result.columns
    assert "ejecutado_qty" in result.columns
    assert "pendiente_qty" in result.columns
    assert result["stock_qty"].iloc[0] == 100.0
    assert result["planificado_qty"].iloc[0] == 150.0
    assert result["ejecutado_qty"].iloc[0] == 50.0
    assert result["pendiente_qty"].iloc[0] == 30.0


def test_merge_fills_missing_with_zero():
    al = pd.DataFrame([_analisis_lote_row()])
    stock = pd.DataFrame([_stock_row()])
    pendiente = pd.DataFrame()

    result = merge_services(stock, al, pendiente)

    assert result["pendiente_qty"].iloc[0] == 0.0


def test_merge_keeps_context_columns():
    al = pd.DataFrame([_analisis_lote_row()])
    stock = pd.DataFrame([_stock_row()])
    pendiente = pd.DataFrame([_pendiente_row()])

    result = merge_services(stock, al, pendiente)

    assert "EMPRESAPADRE" in result.columns
    assert "FAMILIA" in result.columns
    assert "CENTROLOGISTICO" in result.columns


def test_add_proyeccion_formula():
    # Proyección = stock + pendiente - (planificado - ejecutado)
    # = 100 + 30 - (150 - 50) = 130 - 100 = 30
    df = pd.DataFrame([{
        "stock_qty": 100.0,
        "planificado_qty": 150.0,
        "ejecutado_qty": 50.0,
        "pendiente_qty": 30.0,
    }])
    result = add_proyeccion(df)
    assert result["proyeccion"].iloc[0] == 30.0


def test_add_proyeccion_deficit():
    # = 10 + 5 - (200 - 0) = 15 - 200 = -185
    df = pd.DataFrame([{
        "stock_qty": 10.0,
        "planificado_qty": 200.0,
        "ejecutado_qty": 0.0,
        "pendiente_qty": 5.0,
    }])
    result = add_proyeccion(df)
    assert result["proyeccion"].iloc[0] == -185.0


def test_merge_aggregates_multi_deposit_stock():
    # El mismo producto en 2 depósitos → una sola fila sumada
    al = pd.DataFrame([_analisis_lote_row()])
    stock = pd.DataFrame([
        _stock_row(CANTIDAD1=500.0, DEPOSITO="DEP1"),
        _stock_row(CANTIDAD1=300.0, DEPOSITO="DEP2"),
    ])
    pendiente = pd.DataFrame([_pendiente_row()])

    result = merge_services(stock, al, pendiente)

    assert len(result) == 1
    assert result["stock_qty"].iloc[0] == 800.0


def test_merge_fills_desc_cols_for_stock_only_rows():
    # Stock tiene un producto que no está en AnalisisLote → le faltan desc cols
    # Se enriquecen desde la referencia de Stock
    al = pd.DataFrame()
    stock = pd.DataFrame([{
        "PRODUCTO": "HERB B", "EMPRESA": "AED",
        "CANTIDAD1": 200.0,
        "EMPRESAPADRE": "GD", "FAMILIA": "F2",
    }])
    pendiente = pd.DataFrame()

    result = merge_services(stock, al, pendiente)

    assert result["EMPRESAPADRE"].iloc[0] == "GD"
    assert result["FAMILIA"].iloc[0] == "F2"


def test_merge_with_empty_analisis_lote():
    al = pd.DataFrame()
    stock = pd.DataFrame([_stock_row()])
    pendiente = pd.DataFrame([_pendiente_row()])

    result = merge_services(stock, al, pendiente)

    assert isinstance(result, pd.DataFrame)
    assert "stock_qty" in result.columns
    assert "pendiente_qty" in result.columns


def test_add_factor_principio_activo_usa_valor_real():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0.61"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 0.61


def test_add_factor_principio_activo_null_string_default_a_uno():
    # El DW guarda los nulos como el string literal "NULL", no como NULL real
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "NULL"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 1.0


def test_add_factor_principio_activo_cero_default_a_uno():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 1.0


def test_add_factor_principio_activo_producto_sin_match_default_a_uno():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA DESCONOCIDO", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0.61"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 1.0


def test_add_factor_principio_activo_mapas_vacios_default_a_uno():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    result = add_factor_principio_activo(df, pd.DataFrame(), pd.DataFrame())
    assert result["factor_pa"].iloc[0] == 1.0


def test_apply_factor_principio_activo_multiplica_columnas_indicadas():
    df = pd.DataFrame([{
        "stock_qty": 100.0, "planificado_qty": 150.0,
        "ejecutado_qty": 50.0, "pendiente_qty": 30.0,
        "factor_pa": 0.5,
    }])
    result = apply_factor_principio_activo(
        df, ["stock_qty", "planificado_qty", "ejecutado_qty", "pendiente_qty"]
    )
    assert result["stock_qty"].iloc[0] == 50.0
    assert result["planificado_qty"].iloc[0] == 75.0
    assert result["ejecutado_qty"].iloc[0] == 25.0
    assert result["pendiente_qty"].iloc[0] == 15.0


def test_apply_factor_principio_activo_no_toca_columnas_no_indicadas():
    df = pd.DataFrame([{
        "planificado_mes": 100.0, "ejecutado_mes": 40.0,
        "ANO_MES": "2026-08", "factor_pa": 2.0,
    }])
    result = apply_factor_principio_activo(df, ["planificado_mes", "ejecutado_mes"])
    assert result["planificado_mes"].iloc[0] == 200.0
    assert result["ejecutado_mes"].iloc[0] == 80.0
    assert result["ANO_MES"].iloc[0] == "2026-08"

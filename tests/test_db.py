from api.db import _build_analisis_lote_query


def test_build_query_sin_corte_no_agrega_condicion_de_fecha():
    query, params = _build_analisis_lote_query(None)
    assert params == ()
    assert "fecha::date" not in query
    assert "WHEN estado = 'Planificado' THEN" in query


def test_build_query_con_corte_agrega_condicion_de_fecha():
    query, params = _build_analisis_lote_query("2026-08-15")
    assert params == ("2026-08-15",)
    assert "WHEN estado = 'Planificado' AND fecha::date <= %s THEN" in query


def test_build_query_con_corte_no_afecta_la_suma_de_ejecutado():
    query, _ = _build_analisis_lote_query("2026-08-15")
    assert "WHEN estado = 'Ejecutado'   THEN cantidad::numeric END), 0) AS ejecutado_qty" in query

import os
import pandas as pd
import pg8000.dbapi
from dotenv import load_dotenv

load_dotenv()

_TABLE = "duhau_analisisloteejecutadoplanificado"

_QUERY = f"""
SELECT
    laborproducto                                                       AS "PRODUCTO",
    empresa                                                             AS "EMPRESA",
    empresapadre                                                        AS "EMPRESAPADRE",
    familia                                                             AS "FAMILIA",
    subfamilia                                                          AS "SUBFAMILIA",
    principioactivo                                                     AS "PRINCIPIOACTIVO",
    formulacion                                                         AS "FORMULACION",
    centrologistico                                                     AS "CENTROLOGISTICO",
    COALESCE(SUM(CASE WHEN estado = 'Planificado' THEN cantidad::numeric END), 0) AS planificado_qty,
    COALESCE(SUM(CASE WHEN estado = 'Ejecutado'   THEN cantidad::numeric END), 0) AS ejecutado_qty
FROM {_TABLE}
WHERE tipo     = '02 - Insumo'
  AND campania  = '26-27 Campaña'
  AND estado   != 'Ordenado'
GROUP BY
    laborproducto, empresa, empresapadre,
    familia, subfamilia, principioactivo,
    formulacion, centrologistico
"""


def _conn():
    return pg8000.dbapi.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=int(os.getenv("DB_PORT", 5432)),
    )


_QUERY_MONTHLY = f"""
SELECT
    laborproducto                                                        AS "PRODUCTO",
    empresa                                                              AS "EMPRESA",
    empresapadre                                                         AS "EMPRESAPADRE",
    familia                                                              AS "FAMILIA",
    subfamilia                                                           AS "SUBFAMILIA",
    principioactivo                                                      AS "PRINCIPIOACTIVO",
    centrologistico                                                      AS "CENTROLOGISTICO",
    ano_mes                                                              AS "ANO_MES",
    COALESCE(SUM(CASE WHEN estado = 'Planificado' THEN cantidad::numeric END), 0) AS planificado_mes,
    COALESCE(SUM(CASE WHEN estado = 'Ejecutado'   THEN cantidad::numeric END), 0) AS ejecutado_mes
FROM {_TABLE}
WHERE tipo    = '02 - Insumo'
  AND campania = '26-27 Campaña'
  AND estado  != 'Ordenado'
GROUP BY
    laborproducto, empresa, empresapadre, familia, subfamilia,
    principioactivo, centrologistico, ano_mes
ORDER BY empresa, ano_mes
"""


def fetch_analisis_lote_monthly_db() -> pd.DataFrame:
    _EMPTY = ["EMPRESA", "EMPRESAPADRE", "FAMILIA", "SUBFAMILIA",
              "PRINCIPIOACTIVO", "CENTROLOGISTICO", "ANO_MES",
              "planificado_mes", "ejecutado_mes"]
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(_QUERY_MONTHLY)
                cols = [desc[0] for desc in cur.description]
                df = pd.DataFrame(cur.fetchall(), columns=cols)
                for col in ["planificado_mes", "ejecutado_mes"]:
                    if col in df.columns:
                        df[col] = df[col].astype(float)
                return df
    except Exception as e:
        print(f"[db] Error en query mensual: {e}")
        return pd.DataFrame(columns=_EMPTY)


def fetch_analisis_lote_db() -> pd.DataFrame:
    _EMPTY_COLS = [
        "PRODUCTO", "EMPRESA", "EMPRESAPADRE",
        "FAMILIA", "SUBFAMILIA", "PRINCIPIOACTIVO",
        "FORMULACION", "CENTROLOGISTICO",
        "planificado_qty", "ejecutado_qty",
    ]
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(_QUERY)
                cols = [desc[0] for desc in cur.description]
                return pd.DataFrame(cur.fetchall(), columns=cols)
    except Exception as e:
        print(f"[db] Error conectando a PostgreSQL: {e}")
        return pd.DataFrame(columns=_EMPTY_COLS)

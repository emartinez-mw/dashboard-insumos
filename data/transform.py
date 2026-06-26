from datetime import date
import pandas as pd
from config import MERGE_KEYS

_ZONA_MAP = {
    "(AED) Pampa Chaco": "NEA",
    "(ECO) NEA": "NEA",
}

_DESC_COLS = [
    "EMPRESAPADRE", "FAMILIA", "SUBFAMILIA",
    "PRINCIPIOACTIVO", "FORMULACION", "CENTROLOGISTICO",
]


def _agg_qty(df: pd.DataFrame, raw_col: str, out_col: str) -> pd.DataFrame:
    """Sum a quantity column by MERGE_KEYS, return only MERGE_KEYS + out_col."""
    if df.empty or raw_col not in df.columns:
        return pd.DataFrame(columns=MERGE_KEYS + [out_col])
    return (
        df.rename(columns={raw_col: out_col})
        .groupby(MERGE_KEYS, as_index=False)[out_col]
        .sum()
    )


def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)
    return df


def _build_desc_ref(*frames: pd.DataFrame) -> pd.DataFrame:
    """
    Build a PRODUCTO+EMPRESA → descriptive-cols lookup.
    First frame wins (AnalisisLote has priority over Stock).
    """
    parts = []
    for df in frames:
        avail = [c for c in MERGE_KEYS + _DESC_COLS if c in df.columns]
        if avail and not df.empty:
            parts.append(_strip_strings(df[avail].copy()).drop_duplicates(subset=MERGE_KEYS))
    if not parts:
        return pd.DataFrame(columns=MERGE_KEYS + _DESC_COLS)
    return pd.concat(parts).drop_duplicates(subset=MERGE_KEYS, keep="first")


def merge_services(stock: pd.DataFrame, analisis_lote: pd.DataFrame,
                   pendiente: pd.DataFrame) -> pd.DataFrame:
    # Strip leading/trailing spaces from string columns in all services
    for df in [stock, analisis_lote, pendiente]:
        if not df.empty:
            _strip_strings(df)

    # 1. Aggregate quantities by MERGE_KEYS (collapses multi-deposit rows in Stock)
    s_qty  = _agg_qty(stock,     "CANTIDAD1",          "stock_qty")
    pe_qty = _agg_qty(pendiente, "PENDIENTERECEPCION",  "pendiente_qty")

    al_qty_cols = [c for c in MERGE_KEYS + ["planificado_qty", "ejecutado_qty"]
                   if c in analisis_lote.columns] if not analisis_lote.empty else []
    al_qty = analisis_lote[al_qty_cols] if al_qty_cols else pd.DataFrame(
        columns=MERGE_KEYS + ["planificado_qty", "ejecutado_qty"])

    # 2. Outer-merge quantities only
    merged = al_qty.merge(s_qty,  on=MERGE_KEYS, how="outer")
    merged = merged.merge(pe_qty, on=MERGE_KEYS, how="outer")

    for col in ["stock_qty", "planificado_qty", "ejecutado_qty", "pendiente_qty"]:
        merged[col] = merged.get(col, pd.Series(dtype=float)).astype(float).fillna(0.0)

    # 3. Enrich all rows with descriptive attributes (AnalisisLote > Stock > empty)
    ref = _build_desc_ref(analisis_lote, stock)
    merged = merged.merge(ref, on=MERGE_KEYS, how="left")

    return merged


def build_proyeccion_temporal(
    df_monthly: pd.DataFrame,
    df_base: pd.DataFrame,
    incluir_pendiente: bool,
    filters: dict,
) -> pd.DataFrame:
    """
    Devuelve un DataFrame con la proyección de stock acumulada por EMPRESA y ANO_MES.
    df_monthly : datos mensuales de planificado/ejecutado por empresa (sin filtrar)
    df_base    : datos merged ya filtrados (tiene stock_qty y pendiente_qty por producto)
    filters    : dict campo → lista de valores seleccionados (mismos filtros de la grilla)
    """
    if df_monthly.empty or df_base.empty:
        return pd.DataFrame()

    # Aplicar los mismos filtros al dataset mensual
    monthly = df_monthly.copy()
    _strip_strings(monthly)
    for field, selected in filters.items():
        if selected and field in monthly.columns:
            monthly = monthly[monthly[field].isin(selected)]

    if monthly.empty:
        return pd.DataFrame()

    # Stock base por Unidad de Negocios (EMPRESA)
    stock_dedup = (
        df_base.drop_duplicates(subset=MERGE_KEYS)[["EMPRESA", "stock_qty", "pendiente_qty"]]
    )
    base = stock_dedup.groupby("EMPRESA").agg(
        stock=("stock_qty", "sum"),
        pendiente=("pendiente_qty", "sum"),
    ).reset_index()
    base["stock_base"] = base["stock"] + (base["pendiente"] if incluir_pendiente else 0)

    # Neto mensual por empresa
    monthly_grp = (
        monthly.groupby(["EMPRESA", "ANO_MES"])
        .agg(planificado_mes=("planificado_mes", "sum"),
             ejecutado_mes=("ejecutado_mes", "sum"))
        .reset_index()
    )
    monthly_grp["neto_mes"] = monthly_grp["planificado_mes"] - monthly_grp["ejecutado_mes"]

    current_month = date.today().strftime("%Y-%m")
    all_months = sorted(monthly_grp["ANO_MES"].unique())

    # Proyección acumulada por empresa — cumsum sobre todos los meses, mostrar desde el actual
    frames = []
    for empresa, grp in monthly_grp.groupby("EMPRESA"):
        full = (
            pd.DataFrame({"ANO_MES": all_months})
            .merge(grp[["ANO_MES", "planificado_mes", "ejecutado_mes", "neto_mes"]],
                   on="ANO_MES", how="left")
            .fillna(0)
            .sort_values("ANO_MES")
        )
        stock_base = base.loc[base["EMPRESA"] == empresa, "stock_base"].sum()
        full["proyeccion"] = stock_base - full["neto_mes"].cumsum()
        full["EMPRESA"] = empresa
        frames.append(full[full["ANO_MES"] >= current_month])

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def add_zona(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ZONA"] = df["EMPRESA"].map(_ZONA_MAP).fillna("Zona Templada")
    return df


def add_proyeccion(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["proyeccion"] = df["stock_qty"] + df["pendiente_qty"] - (df["planificado_qty"] - df["ejecutado_qty"])
    return df

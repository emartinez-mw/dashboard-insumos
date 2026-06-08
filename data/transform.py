import pandas as pd
from config import MERGE_KEYS


def _normalize_presup(df: pd.DataFrame) -> pd.DataFrame:
    """Rename LABORPRODUCTO → PRODUCTO in Presupuestado DataFrame."""
    if df.empty:
        return df
    return df.rename(columns={"LABORPRODUCTO": "PRODUCTO"})


def merge_services(stock: pd.DataFrame, presup: pd.DataFrame,
                   pendiente: pd.DataFrame) -> pd.DataFrame:
    """Merge 3 DataFrames on MERGE_KEYS, rename qty columns, fill missing with 0."""
    # Normalize product column in presupuestado
    presup = _normalize_presup(presup)

    # Rename qty columns to logical names before merge
    s = stock.rename(columns={"CANTIDAD1": "stock_qty"}) if not stock.empty else pd.DataFrame(columns=MERGE_KEYS + ["stock_qty"])
    p = presup.rename(columns={"CANTIDAD": "presupuestado_qty"}) if not presup.empty else pd.DataFrame(columns=MERGE_KEYS + ["presupuestado_qty"])
    pe = pendiente.rename(columns={"PENDIENTERECEPCION": "pendiente_qty"}) if not pendiente.empty else pd.DataFrame(columns=MERGE_KEYS + ["pendiente_qty"])

    # Keep only merge keys + qty + useful context columns per service
    def _keep(df, qty_col, extra_cols):
        cols = [c for c in MERGE_KEYS + [qty_col] + extra_cols if c in df.columns]
        return df[cols]

    s  = _keep(s,  "stock_qty",        ["DEPOSITO"])
    p  = _keep(p,  "presupuestado_qty", ["DEPOSITO", "ANO-MES"])
    pe = _keep(pe, "pendiente_qty",     ["SUCURSAL", "ANO-MES"])

    merged = s.merge(p, on=MERGE_KEYS, how="outer")
    merged = merged.merge(pe, on=MERGE_KEYS, how="outer")

    for col in ["stock_qty", "presupuestado_qty", "pendiente_qty"]:
        if col not in merged.columns:
            merged[col] = 0.0
        else:
            merged[col] = merged[col].astype(float).fillna(0.0)

    return merged


def add_cobertura(df: pd.DataFrame) -> pd.DataFrame:
    """Add cobertura = stock_qty + pendiente_qty - presupuestado_qty."""
    df = df.copy()
    df["cobertura"] = df["stock_qty"] + df["pendiente_qty"] - df["presupuestado_qty"]
    return df


def prepare_anio_mes(stock: pd.DataFrame, presup: pd.DataFrame,
                     pendiente: pd.DataFrame) -> pd.DataFrame:
    """Aggregate qty by ANO-MES and servicio for the bar chart. Stock has no date."""
    presup = _normalize_presup(presup)
    frames = []

    for df, qty_col, label in [
        (presup,    "CANTIDAD",           "Presupuestado"),
        (pendiente, "PENDIENTERECEPCION", "Pendiente"),
    ]:
        if "ANO-MES" in df.columns and qty_col in df.columns:
            tmp = df[["ANO-MES", qty_col]].copy()
            tmp = tmp.rename(columns={qty_col: "cantidad"})
            tmp["servicio"] = label
            frames.append(tmp)

    if not frames:
        return pd.DataFrame(columns=["ANO-MES", "cantidad", "servicio"])

    result = pd.concat(frames, ignore_index=True)
    return result.groupby(["ANO-MES", "servicio"], as_index=False)["cantidad"].sum()

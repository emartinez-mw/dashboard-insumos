import os
import json
import streamlit as st

st.set_page_config(page_title="Análisis de Lotes", layout="wide")

try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and _k not in os.environ:
            os.environ[_k] = _v
except Exception:
    pass

import pandas as pd
from api.services import fetch_analisis_lote_raw
from data.transform import add_zona

FILTER_CHAIN = [
    ("ZONA",            "Zona"),
    ("EMPRESAPADRE",    "Empresa"),
    ("EMPRESA",         "Unidad de Negocios"),
    ("CENTROLOGISTICO", "Centro de Distribución"),
    ("FAMILIA",         "Familia"),
    ("SUBFAMILIA",      "Subfamilia"),
    ("PRINCIPIOACTIVO", "Principio Activo"),
    ("PRODUCTO",        "Producto"),
]


def _clear_downstream(changed_field: str) -> None:
    fields = [f for f, _ in FILTER_CHAIN]
    idx = fields.index(changed_field)
    for field in fields[idx + 1:]:
        st.session_state[f"al_filter_{field}"] = []


@st.cache_data(show_spinner="Cargando análisis de lotes...")
def load():
    df = fetch_analisis_lote_raw()
    return add_zona(df) if not df.empty else df


st.markdown("## Análisis de Lotes")

try:
    df = load()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# Inicializar session_state con query params
params_raw = st.query_params.get("f", "{}")
try:
    init_filters = json.loads(params_raw)
except Exception:
    init_filters = {}

for field, _ in FILTER_CHAIN:
    key = f"al_filter_{field}"
    if key not in st.session_state:
        st.session_state[key] = init_filters.get(field, [])

# Filtro Estado
if "al_filter_ESTADO" not in st.session_state:
    st.session_state["al_filter_ESTADO"] = []

cascade_df = df.copy()
for row_fields in [FILTER_CHAIN[:4], FILTER_CHAIN[4:]]:
    cols = st.columns(4)
    for col_widget, (field, label) in zip(cols, row_fields):
        with col_widget:
            if field in df.columns:
                options = sorted(cascade_df[field].dropna().unique().tolist())
                valid = [v for v in st.session_state[f"al_filter_{field}"] if v in options]
                if valid != st.session_state[f"al_filter_{field}"]:
                    st.session_state[f"al_filter_{field}"] = valid
                st.multiselect(label, options, key=f"al_filter_{field}",
                               placeholder="Seleccioná una opción",
                               on_change=_clear_downstream, args=(field,))
        if field in df.columns and st.session_state.get(f"al_filter_{field}"):
            cascade_df = cascade_df[cascade_df[field].isin(st.session_state[f"al_filter_{field}"])]

# Filtro Estado (independiente, no en cascada)
if "ESTADO" in df.columns:
    estado_options = sorted(df["ESTADO"].dropna().unique().tolist())
    st.multiselect("Estado", estado_options, key="al_filter_ESTADO",
                   placeholder="Todos los estados")
    if st.session_state["al_filter_ESTADO"]:
        cascade_df = cascade_df[cascade_df["ESTADO"].isin(st.session_state["al_filter_ESTADO"])]

st.markdown(f"**{len(cascade_df):,} registros**")
st.dataframe(cascade_df, use_container_width=True, hide_index=True)

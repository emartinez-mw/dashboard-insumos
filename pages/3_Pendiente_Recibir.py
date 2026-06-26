import io
import os
import json
import streamlit as st

st.set_page_config(page_title="Pendiente Recibir", layout="wide")

try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and _k not in os.environ:
            os.environ[_k] = _v
except Exception:
    pass

import pandas as pd
from api.services import fetch_pendiente
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
        st.session_state[f"p_filter_{field}"] = []


@st.cache_data(show_spinner="Cargando pendiente...")
def load():
    df = fetch_pendiente()
    return add_zona(df) if not df.empty else df


st.markdown("## Pendiente Recibir")

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
    key = f"p_filter_{field}"
    if key not in st.session_state:
        st.session_state[key] = init_filters.get(field, [])

cascade_df = df.copy()
for row_fields in [FILTER_CHAIN[:4], FILTER_CHAIN[4:]]:
    cols = st.columns(4)
    for col_widget, (field, label) in zip(cols, row_fields):
        with col_widget:
            if field in df.columns:
                options = sorted(cascade_df[field].dropna().unique().tolist())
                valid = [v for v in st.session_state[f"p_filter_{field}"] if v in options]
                if valid != st.session_state[f"p_filter_{field}"]:
                    st.session_state[f"p_filter_{field}"] = valid
                st.multiselect(label, options, key=f"p_filter_{field}",
                               placeholder="Seleccioná una opción",
                               on_change=_clear_downstream, args=(field,))
        if field in df.columns and st.session_state.get(f"p_filter_{field}"):
            cascade_df = cascade_df[cascade_df[field].isin(st.session_state[f"p_filter_{field}"])]

col_info, col_btn = st.columns([8, 2])
with col_info:
    st.markdown(f"**{len(cascade_df):,} registros**")
with col_btn:
    buffer = io.BytesIO()
    cascade_df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        "⬇️ Descargar Excel",
        data=buffer.getvalue(),
        file_name="pendiente_recibir.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
st.dataframe(cascade_df, use_container_width=True, hide_index=True)

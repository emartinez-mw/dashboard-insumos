from datetime import datetime
import base64
import json
import os
import urllib.parse
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Dashboard Insumos — Duhau", layout="wide")

# Streamlit Cloud: volcar st.secrets en os.environ antes de importar config/db
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and _k not in os.environ:
            os.environ[_k] = _v
except Exception:
    pass

import plotly.express as px
from api.services import fetch_stock, fetch_analisis_lote, fetch_analisis_lote_monthly, fetch_pendiente
from data.transform import merge_services, add_proyeccion, add_zona, build_proyeccion_temporal

pd.set_option("styler.render.max_elements", 5_000_000)


def _logo_b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    ext = p.suffix.lstrip(".")
    ext = "jpeg" if ext == "jpg" else ext
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/{ext};base64,{data}"


def _fmt(n: float) -> str:
    """Formato argentino: 1.234.567"""
    return f"{n:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


LOGO_SRC = _logo_b64(Path(__file__).parent / "assets" / "logo.jpg")


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Work+Sans:wght@400;500;600;700;800&display=swap');

[data-testid="stAppViewContainer"] { background-color: #f7f9f4; }
[data-testid="stHeader"]           { background-color: #f7f9f4; }
section[data-testid="stMain"] > div { padding-top: 2.5rem; }

/* Fuente base */
html, body, [class*="css"] {
    font-family: 'Work Sans', sans-serif;
}

/* Botón */
.stButton > button {
    background-color: #1a3a2a; color: #fff; border: none;
    font-family: 'Work Sans', sans-serif; font-weight: 600;
    font-size: 10px; letter-spacing: 1px; text-transform: uppercase;
    border-radius: 4px; padding: 4px 12px; height: auto;
    transition: background .2s;
}
.stButton > button:hover { background-color: #c49a1a; color: #111; border: none; }

/* Tabla — letra más chica para que entren los valores */
[data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
    font-size: 11px !important;
}

/* Labels de filtros */
label[data-testid="stWidgetLabel"] p {
    font-family: 'Work Sans', sans-serif !important;
    font-size: 11px !important; font-weight: 700 !important;
    letter-spacing: 1.5px !important; text-transform: uppercase !important;
    color: #6b7280 !important;
}

/* Tags del multiselect */
[data-baseweb="tag"] {
    background-color: #1a3a2a !important;
}
[data-baseweb="tag"] span { color: #fff !important; }

/* Radio buttons — texto en negro */
[data-testid="stRadio"] label p,
[data-testid="stRadio"] div[role="radiogroup"] label p {
    color: #111 !important; font-size: 12px !important; font-weight: 500 !important;
}

/* Toggle — texto en negro (Streamlit usa stCheckbox como testid para st.toggle) */
[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] span,
[data-testid="stToggle"] label p,
[data-testid="stToggle"] span,
.stCheckbox label p,
.stToggle label p {
    color: #111 !important; font-size: 12px !important; font-weight: 500 !important;
}

/* Separador de sección */
.duhau-section {
    display: flex; align-items: center; gap: 10px;
    margin-top: 32px; margin-bottom: 14px;
}
.duhau-bar  { width: 4px; height: 18px; background: #c49a1a; flex-shrink: 0; border-radius: 2px; }
.duhau-lbl  { font-size: 10px; font-weight: 800; letter-spacing: 3px; text-transform: uppercase; color: #c49a1a; }
.duhau-caption { font-size: 11px; color: #9ca3af; margin-top: 4px; font-family: 'Work Sans', sans-serif; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
logo_html = f'<img src="{LOGO_SRC}" style="height:44px;width:auto;object-fit:contain"/>' if LOGO_SRC else \
    '<div style="height:44px;width:44px;background:#c49a1a;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#111">AED</div>'

st.markdown(f"""
<div style="background:#111;border-bottom:3px solid #C49A1A;
            padding:18px 32px;display:flex;justify-content:space-between;
            align-items:center;border-radius:8px;margin-bottom:6px">
  <div style="display:flex;align-items:center;gap:18px">
    {logo_html}
    <div style="width:1px;height:38px;background:rgba(255,255,255,.15)"></div>
    <span style="font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
                 color:rgba(255,255,255,.4);font-family:'Work Sans',sans-serif">
      PROYECCIÓN DE INSUMOS
    </span>
  </div>
  <div style="text-align:right">
    <div style="font-family:'Libre Baskerville',serif;font-size:17px;color:#fff;font-weight:700">
      Dashboard de Insumos</div>
    <div style="font-size:11px;color:rgba(255,255,255,.35);margin-top:4px;font-family:'Work Sans',sans-serif">
      Campaña 26-27
    </div>
  </div>
</div>
<div class="duhau-caption" style="margin-left:4px;margin-bottom:4px">
  Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}
</div>
""", unsafe_allow_html=True)

# ── CARGA DE DATOS ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos desde Finnegans...")
def load_data():
    stock         = fetch_stock()
    analisis_lote = fetch_analisis_lote()
    pendiente     = fetch_pendiente()
    monthly       = fetch_analisis_lote_monthly()
    merged        = merge_services(stock, analisis_lote, pendiente)
    merged        = add_zona(merged)
    merged        = add_proyeccion(merged)
    return merged, monthly


col_ref, _ = st.columns([1, 11])
with col_ref:
    if st.button("↺  Actualizar"):
        st.cache_data.clear()
        st.rerun()

try:
    df, df_monthly = load_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# ── FILTROS ────────────────────────────────────────────────────────────────────
st.markdown('<div class="duhau-section"><div class="duhau-bar"></div><span class="duhau-lbl">Filtros</span></div>', unsafe_allow_html=True)

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
        st.session_state[f"filter_{field}"] = []

for field, _ in FILTER_CHAIN:
    if f"filter_{field}" not in st.session_state:
        st.session_state[f"filter_{field}"] = []

cascade_df = df.copy()
for row_fields in [FILTER_CHAIN[:4], FILTER_CHAIN[4:]]:
    cols = st.columns(4)
    for col_widget, (field, label) in zip(cols, row_fields):
        with col_widget:
            if field in df.columns:
                options = sorted(cascade_df[field].dropna().unique().tolist())
                valid = [v for v in st.session_state[f"filter_{field}"] if v in options]
                if valid != st.session_state[f"filter_{field}"]:
                    st.session_state[f"filter_{field}"] = valid
                st.multiselect(label, options, key=f"filter_{field}",
                               placeholder="Seleccioná una opción",
                               on_change=_clear_downstream, args=(field,))
        if field in df.columns and st.session_state.get(f"filter_{field}"):
            cascade_df = cascade_df[cascade_df[field].isin(st.session_state[f"filter_{field}"])]

filters = {field: st.session_state.get(f"filter_{field}", []) for field, _ in FILTER_CHAIN}
filtered = cascade_df

# ── KPI STRIP ─────────────────────────────────────────────────────────────────
stock_total     = filtered["stock_qty"].sum()
pendiente_total = filtered["pendiente_qty"].sum()
dif_plan_ejec   = filtered["planificado_qty"].sum() - filtered["ejecutado_qty"].sum()
proy_total      = filtered["proyeccion"].sum() if "proyeccion" in filtered.columns else 0.0

proy_color = "#1a6b3a" if proy_total >= 0 else "#dc2626"
proy_bg    = "#dcfce7" if proy_total >= 0 else "#fee2e2"
proy_label = "▲ Positiva" if proy_total >= 0 else "▼ Negativa"

st.markdown('<div class="duhau-section" style="margin-top:28px"><div class="duhau-bar"></div><span class="duhau-lbl">Resumen</span></div>', unsafe_allow_html=True)

st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);border:2px solid #111;
            border-radius:4px;overflow:hidden;margin-bottom:8px">

  <div style="padding:28px 28px 24px;border-right:1px solid #e5e7eb;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Stock Actual</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:#111;line-height:1">{_fmt(stock_total)}</div>
    <div style="font-size:13px;font-weight:600;color:#9ca3af;margin-top:6px;
                font-family:'Work Sans',sans-serif">kg</div>
  </div>

  <div style="padding:28px 28px 24px;border-right:1px solid #e5e7eb;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Pendiente Recepción</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:#111;line-height:1">{_fmt(pendiente_total)}</div>
    <div style="font-size:13px;font-weight:600;color:#9ca3af;margin-top:6px;
                font-family:'Work Sans',sans-serif">Kg/Lit</div>
  </div>

  <div style="padding:28px 28px 24px;border-right:1px solid #e5e7eb;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Dif. Planificado / Ejecutado</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:#111;line-height:1">{_fmt(dif_plan_ejec)}</div>
    <div style="font-size:13px;font-weight:600;color:#9ca3af;margin-top:6px;
                font-family:'Work Sans',sans-serif">Kg/Lit</div>
  </div>

  <div style="padding:28px 28px 24px;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Proyección Total</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:{proy_color};line-height:1">{_fmt(proy_total)}</div>
    <div style="display:inline-flex;align-items:center;gap:4px;margin-top:10px;
                font-size:11px;font-weight:700;padding:3px 10px;border-radius:3px;
                background:{proy_bg};color:{proy_color};font-family:'Work Sans',sans-serif">
      {proy_label}
    </div>
  </div>

</div>
""", unsafe_allow_html=True)

# ── TABLA ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="duhau-section"><div class="duhau-bar"></div><span class="duhau-lbl">Análisis Cruzado</span></div>', unsafe_allow_html=True)

display_cols = [c for c in [
    "EMPRESA", "FAMILIA", "SUBFAMILIA", "PRINCIPIOACTIVO", "FORMULACION",
    "PRODUCTO", "CENTROLOGISTICO",
    "stock_qty", "planificado_qty", "ejecutado_qty", "pendiente_qty", "proyeccion",
] if c in filtered.columns]

col_labels = {
    "PRODUCTO":         "Producto",
    "EMPRESAPADRE":     "Empresa",
    "EMPRESA":          "Unidad de Negocios",
    "FAMILIA":          "Familia",
    "SUBFAMILIA":       "Subfamilia",
    "PRINCIPIOACTIVO":  "Principio Activo",
    "FORMULACION":      "Formulación",
    "CENTROLOGISTICO":  "Centro Distribución",
    "stock_qty":        "Stock Actual",
    "planificado_qty":  "Planificado",
    "ejecutado_qty":    "Ejecutado",
    "pendiente_qty":    "Pendiente Recepción",
    "proyeccion":       "Proyección",
}

table_df = filtered[display_cols].copy().rename(columns=col_labels)
NUM_COLS = ["Stock Actual", "Planificado", "Ejecutado", "Pendiente Recepción", "Proyección"]
num_cols_present = [c for c in NUM_COLS if c in table_df.columns]
text_cols = [c for c in table_df.columns if c not in num_cols_present]
table_df[text_cols] = table_df[text_cols].fillna("")

proy_filter = st.radio(
    "Mostrar",
    options=["Todos", "Solo déficit (negativo)", "Solo superávit (≥ 0)"],
    horizontal=True,
    label_visibility="collapsed",
)
if proy_filter == "Solo déficit (negativo)":
    table_df = table_df[filtered["proyeccion"].lt(0).values]
elif proy_filter == "Solo superávit (≥ 0)":
    table_df = table_df[filtered["proyeccion"].ge(0).values]


def color_proyeccion(val):
    if isinstance(val, (int, float)):
        if val >= 0:
            return "background-color: #dcfce7; color: #2d6a4f; font-weight: 600"
        else:
            return "background-color: #fee2e2; color: #dc2626; font-weight: 600"
    return ""


st.dataframe(
    table_df.style
        .format("{:,.2f}", subset=num_cols_present, na_rep="")
        .map(color_proyeccion, subset=["Proyección"] if "Proyección" in table_df.columns else [])
        .set_properties(**{"font-family": "Work Sans, sans-serif", "font-size": "13px"}),
    width="stretch",
    hide_index=True,
)

total_rows = len(table_df)
total_empresas = filtered["EMPRESA"].nunique() if "EMPRESA" in filtered.columns else 0
st.markdown(f"""
<div style="font-family:'Work Sans',sans-serif;font-size:11px;color:#9ca3af;
            margin-top:8px;text-align:right">
  {total_rows:,} productos · {total_empresas} empresa{"s" if total_empresas != 1 else ""}
</div>
""", unsafe_allow_html=True)

# ── PROYECCIÓN TEMPORAL ───────────────────────────────────────────────────────
st.markdown('<div class="duhau-section"><div class="duhau-bar"></div><span class="duhau-lbl">Proyección de Stock en el Tiempo</span></div>', unsafe_allow_html=True)

incluir_pendiente = st.toggle("Incluir pendiente a recibir en el stock base", value=True)

df_proy = build_proyeccion_temporal(df_monthly, filtered, incluir_pendiente, filters)

if df_proy.empty:
    st.info("Sin datos suficientes para graficar la proyección temporal.")
else:
    fig = px.line(
        df_proy.sort_values("ANO_MES"),
        x="ANO_MES",
        y="proyeccion",
        color="EMPRESA",
        markers=True,
        labels={
            "ANO_MES":    "Período",
            "proyeccion": "Stock Proyectado",
            "EMPRESA":    "Unidad de Negocios",
        },
        color_discrete_sequence=[
            "#1a3a2a", "#c49a1a", "#2d6a4f", "#e8b82a",
            "#4a7c59", "#a07c10", "#6b8a74", "#374151",
            "#dc2626", "#1e4d3a",
        ],
    )
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#dc2626",
        line_width=1.5,
        annotation_text="Déficit",
        annotation_position="bottom right",
        annotation_font_color="#dc2626",
    )
    fig.update_layout(
        plot_bgcolor="#f7f9f4",
        paper_bgcolor="#f7f9f4",
        font_family="Work Sans",
        font_color="#1a3a2a",
        legend_title_text="Unidad de Negocios",
        xaxis=dict(showgrid=True, gridcolor="#e5e7eb", title_font_size=12),
        yaxis=dict(showgrid=True, gridcolor="#e5e7eb", title_font_size=12,
                   tickformat=",.0f"),
        margin=dict(t=20, b=20),
        hovermode="x unified",
    )
    fig.update_traces(line_width=2, marker_size=6)
    st.plotly_chart(fig, width="stretch")

# ── DATOS CRUDOS ──────────────────────────────────────────────────────────────
st.markdown('<div class="duhau-section"><div class="duhau-bar"></div><span class="duhau-lbl">Detalle por Servicio</span></div>', unsafe_allow_html=True)

active_filters = {k: v for k, v in filters.items() if v}
encoded = urllib.parse.quote(json.dumps(active_filters))
query = f"?f={encoded}" if active_filters else ""

st.markdown(
    f'<a href="/Stock{query}" target="_blank" style="margin-right:32px;font-weight:600;font-family:Work Sans,sans-serif;font-size:13px;color:#1a3a2a;text-decoration:none;border:1px solid #1a3a2a;padding:6px 14px;border-radius:4px">📦 Stock</a>'
    f'<a href="/Analisis_Lote{query}" target="_blank" style="margin-right:32px;font-weight:600;font-family:Work Sans,sans-serif;font-size:13px;color:#1a3a2a;text-decoration:none;border:1px solid #1a3a2a;padding:6px 14px;border-radius:4px">📋 Análisis de Lotes</a>'
    f'<a href="/Pendiente{query}" target="_blank" style="font-weight:600;font-family:Work Sans,sans-serif;font-size:13px;color:#1a3a2a;text-decoration:none;border:1px solid #1a3a2a;padding:6px 14px;border-radius:4px">⏳ Pendiente Recibir</a>',
    unsafe_allow_html=True,
)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-top:1px solid #d1d5db;padding:16px 0;margin-top:40px;
            display:flex;justify-content:space-between;align-items:center">
  <div style="font-family:'Work Sans',sans-serif;font-size:11px;color:#9ca3af">
    Fuentes: Finnegans ERP
  </div>
  <span style="font-family:'Work Sans',sans-serif;font-size:10px;font-weight:800;
               letter-spacing:1.5px;text-transform:uppercase;color:#dc2626;
               border:1px solid rgba(220,38,38,.2);padding:3px 10px;border-radius:3px">
    CONFIDENCIAL INTERNO
  </span>
</div>
""", unsafe_allow_html=True)

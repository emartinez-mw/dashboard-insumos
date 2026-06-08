# app.py
from datetime import datetime
import streamlit as st
import plotly.express as px
from api.services import fetch_stock, fetch_presupuestado, fetch_pendiente
from data.transform import merge_services, add_cobertura, prepare_anio_mes
from config import MERGE_KEYS

st.set_page_config(page_title="Dashboard Insumos — Duhau", layout="wide")
st.title("Dashboard de Insumos Agrícolas — Duhau")


@st.cache_data(show_spinner="Cargando datos desde Finnegans...")
def load_data():
    stock = fetch_stock()
    presup = fetch_presupuestado()
    pendiente = fetch_pendiente()
    merged = merge_services(stock, presup, pendiente)
    merged = add_cobertura(merged)
    anio_mes = prepare_anio_mes(stock, presup, pendiente)
    return merged, anio_mes


# Header
col1, col2 = st.columns([6, 1])
with col1:
    st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
with col2:
    if st.button("🔄 Actualizar"):
        st.cache_data.clear()
        st.rerun()

try:
    df, df_anio_mes = load_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# Filtros
st.subheader("Filtros")
filter_cols = st.columns(3)
filter_fields = ["EMPRESA", "RUBRO", "PRODUCTO"]
filter_labels = ["Empresa", "Rubro", "Producto"]
filters = {}

for col, field, label in zip(filter_cols, filter_fields, filter_labels):
    with col:
        if field in df.columns:
            options = sorted(df[field].dropna().unique().tolist())
            filters[field] = st.multiselect(label, options)

filtered = df.copy()
for field, selected in filters.items():
    if selected:
        filtered = filtered[filtered[field].isin(selected)]

# Tabla de análisis cruzado
st.subheader("Análisis Cruzado")

display_cols = [c for c in ["PRODUCTO", "EMPRESA", "RUBRO", "DEPOSITO", "SUCURSAL",
                             "stock_qty", "presupuestado_qty", "pendiente_qty", "cobertura"]
                if c in filtered.columns]

col_labels = {
    "PRODUCTO": "Producto", "EMPRESA": "Empresa", "RUBRO": "Rubro",
    "DEPOSITO": "Depósito", "SUCURSAL": "Sucursal",
    "stock_qty": "Stock Actual", "presupuestado_qty": "Presupuestado",
    "pendiente_qty": "Pendiente Recepción", "cobertura": "Cobertura",
}

table_df = filtered[display_cols].copy()
table_df = table_df.rename(columns=col_labels)


def color_cobertura(val):
    if isinstance(val, (int, float)):
        color = "#d4edda" if val >= 0 else "#f8d7da"
        return f"background-color: {color}"
    return ""


st.dataframe(
    table_df.style.map(color_cobertura, subset=["Cobertura"]),
    use_container_width=True,
    hide_index=True,
)

# Gráfico de proyección por año-mes
st.subheader("Proyección por Año-Mes")

if df_anio_mes.empty or "ANO-MES" not in df_anio_mes.columns:
    st.info("No hay datos de Año-Mes disponibles.")
else:
    fig = px.bar(
        df_anio_mes.sort_values("ANO-MES"),
        x="ANO-MES",
        y="cantidad",
        color="servicio",
        barmode="group",
        labels={"ANO-MES": "Año-Mes", "cantidad": "Cantidad", "servicio": "Servicio"},
        title="Cantidades por Año-Mes",
        color_discrete_map={
            "Presupuestado": "#FF9800",
            "Pendiente": "#4CAF50",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

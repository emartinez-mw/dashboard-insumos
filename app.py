import streamlit as st

from access_control import require_login

st.write("DEBUG top-level secrets keys:", list(st.secrets.keys()))
if "auth" in st.secrets:
    auth_val = st.secrets["auth"]
    st.write("DEBUG type of auth value:", type(auth_val).__name__)
    try:
        st.write("DEBUG auth section keys:", list(auth_val.keys()))
    except Exception as e:
        st.write("DEBUG auth is not dict-like:", repr(e))
st.stop()

require_login()

pg = st.navigation(
    [
        st.Page("_resumen_general.py",          title="Resumen General"),
        st.Page("pages/1_Stock.py",             title="Stock",             url_path="Stock"),
        st.Page("pages/2_Analisis_Lote.py",     title="Análisis de Lotes", url_path="Analisis_Lote"),
        st.Page("pages/3_Pendiente_Recibir.py", title="Pendiente Recibir", url_path="Pendiente"),
    ],
    position="hidden",
)
pg.run()

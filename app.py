import streamlit as st

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

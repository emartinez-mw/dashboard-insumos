# Botón de descarga Excel — grilla "Análisis Cruzado"

**Fecha:** 2026-07-14

## Contexto

La grilla "Análisis Cruzado" en `_resumen_general.py` (línea ~322) no tiene forma de exportar su contenido. Las páginas `1_Stock.py`, `2_Analisis_Lote.py` y `3_Pendiente_Recibir.py` ya tienen un botón "⬇️ Descargar Excel" con el mismo patrón (buffer en memoria + `st.download_button`). Este cambio replica ese patrón en `_resumen_general.py`.

## Alcance

Agregar un botón exclusivo de descarga a Excel para la grilla "Análisis Cruzado", sin modificar el contador de registros existente ("N productos · M empresas") que queda donde está hoy, después de la tabla.

## Diseño

- **Datos exportados:** `table_df`, ya filtrado por el radio "Todos / Solo déficit / Solo superávit" y con las columnas ya renombradas (Producto, Familia, Stock Actual, etc.) — exactamente lo que se ve en pantalla.
- **Ubicación:** fila propia justo antes de `st.dataframe(...)` (después del radio de filtro), con el botón alineado a la derecha vía `st.columns([8, 2])` (columna izquierda vacía).
- **Nombre de archivo:** `analisis_cruzado.xlsx` (fijo, sin fecha).
- **Import:** agregar `import io` al inicio de `_resumen_general.py` (no está importado hoy; sí lo está en las otras 3 páginas).

```python
_, col_btn = st.columns([8, 2])
with col_btn:
    buffer = io.BytesIO()
    table_df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        "⬇️ Descargar Excel",
        data=buffer.getvalue(),
        file_name="analisis_cruzado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

## Fuera de alcance

- No se toca el contador de registros existente.
- No se agregan tests nuevos (no hay tests de UI para las otras páginas con el mismo patrón; se mantiene la convención existente).
- No se modifica el patrón de descarga de las otras 3 páginas.

## Deploy

Push a `main` dispara redeploy automático en Streamlit Cloud (confirmado funcionando en despliegues previos).

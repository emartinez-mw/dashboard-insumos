# Descarga Excel — Análisis Cruzado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un botón "⬇️ Descargar Excel" a la grilla "Análisis Cruzado" en `_resumen_general.py`, replicando el patrón ya usado en `pages/1_Stock.py`, `pages/2_Analisis_Lote.py` y `pages/3_Pendiente_Recibir.py`.

**Architecture:** Cambio de un único archivo (`_resumen_general.py`): un import nuevo (`io`) y un bloque de ~10 líneas antes de `st.dataframe(...)` que serializa `table_df` a un buffer en memoria y lo expone vía `st.download_button`. No hay lógica de negocio nueva ni cambios de datos.

**Tech Stack:** Streamlit (`st.download_button`, `st.columns`), pandas (`DataFrame.to_excel`), `openpyxl` como engine (ya en `requirements.txt`, usado por las otras 3 páginas), `io.BytesIO`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-14-descarga-excel-analisis-cruzado-design.md`
- No modificar el contador de registros existente ("N productos · M empresas"), que queda después de la tabla sin cambios.
- Nombre de archivo fijo: `analisis_cruzado.xlsx`.
- Datos exportados: `table_df` tal cual se muestra en pantalla (ya filtrado por el radio Todos/Déficit/Superávit, columnas ya renombradas).
- No agregar tests automatizados nuevos — las otras 3 páginas con el mismo patrón no los tienen; se mantiene la convención existente del repo.
- No tocar el patrón de descarga de las otras 3 páginas.

---

### Task 1: Agregar botón de descarga Excel a "Análisis Cruzado"

**Files:**
- Modify: `_resumen_general.py:1-8` (imports)
- Modify: `_resumen_general.py:301-322` (bloque del radio de filtro y la tabla)

**Interfaces:**
- Consumes: `table_df` (ya definido en `_resumen_general.py:295`, `pd.DataFrame` con columnas renombradas: Producto, Familia, Subfamilia, Principio Activo, Formulación, Centro Distribución, Stock Actual, Planificado, Ejecutado, Pendiente Recepción, Proyección) y `proy_filter` (`str`, ya aplicado a `table_df` en las líneas 307-310, antes de este bloque).
- Produces: nada consumido por tasks posteriores — no hay más tasks en este plan.

- [ ] **Step 1: Agregar el import de `io` al principio del archivo**

Archivo `_resumen_general.py`, línea 1. Hoy dice:

```python
from datetime import datetime
import base64
import json
import os
import urllib.parse
from pathlib import Path
import pandas as pd
import streamlit as st
```

Cambiar a:

```python
from datetime import datetime
import base64
import io
import json
import os
import urllib.parse
from pathlib import Path
import pandas as pd
import streamlit as st
```

- [ ] **Step 2: Agregar el botón de descarga antes de `st.dataframe(...)`**

En `_resumen_general.py`, ubicar el bloque (alrededor de la línea 301-322):

```python
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
```

Insertar el bloque del botón entre el `if/elif` del filtro y la función `color_proyeccion`, quedando así:

```python
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
```

- [ ] **Step 3: Verificar sintaxis con py_compile**

Run: `cd ~/dashboard-insumos && python -m py_compile _resumen_general.py`
Expected: sin output (compila sin errores)

- [ ] **Step 4: Correr la suite de tests existente para descartar regresiones**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest -q`
Expected: `22 passed` (mismo resultado que antes del cambio — este cambio no toca módulos con tests propios)

- [ ] **Step 5: Verificación manual en browser**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py`

En el browser (`http://localhost:8501`):
1. Ir a la sección "Análisis Cruzado".
2. Confirmar que aparece el botón "⬇️ Descargar Excel" alineado a la derecha, antes de la grilla.
3. Confirmar que el contador "N productos · M empresas" sigue apareciendo después de la grilla, sin cambios.
4. Clickear el botón, abrir el `.xlsx` descargado y confirmar que las columnas y filas coinciden con lo que se ve en pantalla (probar también con el radio en "Solo déficit" y "Solo superávit" para confirmar que el excel refleja el filtro activo).

Expected: el archivo `analisis_cruzado.xlsx` descargado contiene las mismas filas/columnas visibles en la grilla para cada estado del filtro.

- [ ] **Step 6: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: agregar boton de descarga Excel a grilla Analisis Cruzado"
```

- [ ] **Step 7: Push a main para disparar el redeploy automático en Streamlit Cloud**

```bash
git push origin main
```

Expected: push exitoso; Streamlit Cloud redeploya automáticamente (mismo comportamiento confirmado en despliegues previos, ver `project-dashboard-insumos` memoria).

- [ ] **Step 8: Verificar en producción**

Abrir la URL de producción en Streamlit Cloud y repetir la verificación del Step 5 (botón visible, descarga funciona, contador de registros intacto).

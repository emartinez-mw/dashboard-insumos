# Fechas de Corte — Planificado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir cargar hasta 3 fechas de corte (≥ hoy) que recalculen `planificado_qty` (y todo lo derivado: grilla "Análisis Cruzado", KPIs "Dif. Planificado/Ejecutado" y "Proyección Total", líneas de referencia en el gráfico temporal) sin tocar Stock, Pendiente ni Ejecutado.

**Architecture:** La query SQL de `api/db.py` que suma Planificado/Ejecutado recibe un corte de fecha opcional (parámetro `%s`, paramstyle `format` de pg8000) que solo condiciona la suma de `Planificado`. `_resumen_general.py` separa la carga de datos en una parte base (Stock/Pendiente/Monthly, sin corte) y una parte de AnálisisLote parametrizada por corte, cacheadas por separado con `st.cache_data`; un helper `build_filtered()` arma el dataframe final (merge + zona + proyección + filtros) para cualquier fecha de corte dada, reusado tanto por la grilla/KPIs (corte activo del slicer) como por las líneas de referencia del gráfico (las 3 fechas cargadas).

**Tech Stack:** Streamlit (`st.date_input`, `st.segmented_control`), pandas, pg8000 (paramstyle `format`), Plotly (`fig.add_vline`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-14-fechas-corte-planificado-design.md`
- Las 3 fechas son opcionales; sin ninguna cargada, el comportamiento es idéntico al actual ("Sin corte").
- Validación "≥ hoy": `min_value=date.today()` en los 3 `st.date_input` (nativo de Streamlit).
- Orden creciente forzado: `min_value` de Fecha 2 = Fecha 1 (o hoy); `min_value` de Fecha 3 = Fecha 2 (o Fecha 1, o hoy). Al cambiar una fecha, las posteriores se limpian (evita que un valor guardado quede por debajo del nuevo `min_value` y Streamlit tire `StreamlitAPIException`).
- Solo `planificado_qty` cambia con el corte. `stock_qty`, `pendiente_qty`, `ejecutado_qty` y la curva mensual del gráfico no se filtran por fecha.
- No se agregan tests de UI de Streamlit (criterio ya usado en el resto del repo); sí se testea unitariamente la lógica pura (construcción de la query parametrizada).
- Se valida localmente contra datos reales de Finnegans antes de subir a producción.

---

### Task 1: Query parametrizada por fecha de corte en `api/db.py`

**Files:**
- Modify: `api/db.py:8-30` (agregar función de construcción de query) y `api/db.py:119-137` (`fetch_analisis_lote_db`)
- Test: `tests/test_db.py` (nuevo)

**Interfaces:**
- Produces: `_build_analisis_lote_query(fecha_corte: str | None) -> tuple[str, tuple]` — función pura, sin conexión a DB. `fetch_analisis_lote_db(fecha_corte: str | None = None) -> pd.DataFrame` — firma nueva, con default `None` para no romper el llamador actual.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_db.py`:

```python
from api.db import _build_analisis_lote_query


def test_build_query_sin_corte_no_agrega_condicion_de_fecha():
    query, params = _build_analisis_lote_query(None)
    assert params == ()
    assert "fecha::date" not in query
    assert "WHEN estado = 'Planificado' THEN" in query


def test_build_query_con_corte_agrega_condicion_de_fecha():
    query, params = _build_analisis_lote_query("2026-08-15")
    assert params == ("2026-08-15",)
    assert "WHEN estado = 'Planificado' AND fecha::date <= %s THEN" in query


def test_build_query_con_corte_no_afecta_la_suma_de_ejecutado():
    query, _ = _build_analisis_lote_query("2026-08-15")
    assert "WHEN estado = 'Ejecutado'   THEN cantidad::numeric END), 0) AS ejecutado_qty" in query
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_db.py -v`
Expected: FAIL con `ImportError: cannot import name '_build_analisis_lote_query'`

- [ ] **Step 3: Implementar `_build_analisis_lote_query` y actualizar `fetch_analisis_lote_db`**

En `api/db.py`, agregar la función justo después de `_QUERY` (después de la línea 30, antes de `def _conn():`):

```python
def _build_analisis_lote_query(fecha_corte: str | None = None) -> tuple:
    if fecha_corte:
        query = _QUERY.replace(
            "WHEN estado = 'Planificado' THEN",
            "WHEN estado = 'Planificado' AND fecha::date <= %s THEN",
        )
        return query, (fecha_corte,)
    return _QUERY, ()
```

Reemplazar `fetch_analisis_lote_db` (líneas 119-137) por:

```python
def fetch_analisis_lote_db(fecha_corte: str | None = None) -> pd.DataFrame:
    _EMPTY_COLS = [
        "PRODUCTO", "EMPRESA", "EMPRESAPADRE",
        "FAMILIA", "SUBFAMILIA", "PRINCIPIOACTIVO",
        "FORMULACION", "CENTROLOGISTICO",
        "planificado_qty", "ejecutado_qty",
    ]
    query, params = _build_analisis_lote_query(fecha_corte)
    try:
        conn = _conn()
        cur = conn.cursor()
        cur.execute(query, params)
        cols = [desc[0] for desc in cur.description]
        result = pd.DataFrame(cur.fetchall(), columns=cols)
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"[db] Error conectando a PostgreSQL: {e}")
        return pd.DataFrame(columns=_EMPTY_COLS)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_db.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/dashboard-insumos
git add api/db.py tests/test_db.py
git commit -m "feat: query de AnalisisLote acepta fecha de corte opcional para Planificado"
```

---

### Task 2: Pasar `fecha_corte` a través de `api/services.py`

**Files:**
- Modify: `api/services.py:30-32`
- Test: `tests/test_services.py`

**Interfaces:**
- Consumes: `fetch_analisis_lote_db(fecha_corte: str | None = None) -> pd.DataFrame` (Task 1)
- Produces: `fetch_analisis_lote(fecha_corte: str | None = None) -> pd.DataFrame`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_services.py` (después de `test_fetch_analisis_lote_returns_dataframe_from_db`):

```python
def test_fetch_analisis_lote_pasa_fecha_corte_a_la_db():
    with patch("api.db.fetch_analisis_lote_db", return_value=pd.DataFrame()) as mock_db:
        fetch_analisis_lote(fecha_corte="2026-08-15")
    mock_db.assert_called_once_with("2026-08-15")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_services.py::test_fetch_analisis_lote_pasa_fecha_corte_a_la_db -v`
Expected: FAIL con `TypeError: fetch_analisis_lote() got an unexpected keyword argument 'fecha_corte'`

- [ ] **Step 3: Implementar el pasaje del parámetro**

En `api/services.py`, reemplazar (líneas 30-32):

```python
def fetch_analisis_lote() -> pd.DataFrame:
    from api.db import fetch_analisis_lote_db
    return fetch_analisis_lote_db()
```

por:

```python
def fetch_analisis_lote(fecha_corte: str | None = None) -> pd.DataFrame:
    from api.db import fetch_analisis_lote_db
    return fetch_analisis_lote_db(fecha_corte)
```

- [ ] **Step 4: Correr todos los tests de services y verificar que pasan**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_services.py -v`
Expected: todos los tests de `test_services.py` en verde (incluido el nuevo)

- [ ] **Step 5: Commit**

```bash
cd ~/dashboard-insumos
git add api/services.py tests/test_services.py
git commit -m "feat: fetch_analisis_lote acepta fecha_corte opcional"
```

---

### Task 3: Refactor de carga de datos en `_resumen_general.py` (sin cambios de comportamiento)

**Files:**
- Modify: `_resumen_general.py:145-211`

**Interfaces:**
- Consumes: `fetch_analisis_lote(fecha_corte: str | None = None)` (Task 2), `merge_services`, `add_zona`, `add_proyeccion` (ya importados en `_resumen_general.py:23`)
- Produces: `load_base_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` (stock, pendiente, monthly); `load_analisis_lote(fecha_corte: str | None) -> pd.DataFrame`; `build_filtered(analisis_lote_df: pd.DataFrame, filters: dict) -> pd.DataFrame` — usados por Task 4 y Task 5.

Este task es un refactor puro: el comportamiento visible de la app no cambia (todavía no hay UI de fechas de corte). Sirve para separar la carga cacheada de Stock/Pendiente/Monthly (no dependen del corte) de la de AnálisisLote (si depende), sin todavía exponer el selector.

- [ ] **Step 1: Reemplazar el bloque de carga de datos**

En `_resumen_general.py`, reemplazar el bloque (líneas 145-168):

```python
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
```

por:

```python
# ── CARGA DE DATOS ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos desde Finnegans...")
def load_base_data():
    stock     = fetch_stock()
    pendiente = fetch_pendiente()
    monthly   = fetch_analisis_lote_monthly()
    return stock, pendiente, monthly


@st.cache_data(show_spinner="Calculando planificado...")
def load_analisis_lote(fecha_corte: str | None):
    return fetch_analisis_lote(fecha_corte)


def build_filtered(stock, analisis_lote_df, pendiente, filters):
    merged = merge_services(stock, analisis_lote_df, pendiente)
    merged = add_zona(merged)
    merged = add_proyeccion(merged)
    for field, selected in filters.items():
        if selected and field in merged.columns:
            merged = merged[merged[field].isin(selected)]
    return merged


col_ref, _ = st.columns([1, 11])
with col_ref:
    if st.button("↺  Actualizar"):
        st.cache_data.clear()
        st.rerun()

try:
    stock, pendiente, df_monthly = load_base_data()
    df = build_filtered(stock, load_analisis_lote(None), pendiente, {})
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()
```

- [ ] **Step 2: Reemplazar la línea final de la sección de Filtros**

En `_resumen_general.py`, reemplazar (línea 210-211):

```python
filters = {field: st.session_state.get(f"filter_{field}", []) for field, _ in FILTER_CHAIN}
filtered = cascade_df
```

por:

```python
filters = {field: st.session_state.get(f"filter_{field}", []) for field, _ in FILTER_CHAIN}
filtered = build_filtered(stock, load_analisis_lote(None), pendiente, filters)
```

(Todavía sin UI de corte — `load_analisis_lote(None)` reemplaza al `cascade_df` de antes, pero con el mismo resultado: sin corte, filtrado por los mismos `filters`.)

- [ ] **Step 3: Verificar sintaxis**

Run: `cd ~/dashboard-insumos && python -m py_compile _resumen_general.py`
Expected: sin output

- [ ] **Step 4: Correr toda la suite de tests**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest -q`
Expected: todos los tests existentes en verde (este refactor no cambia lógica de negocio, solo la orquestación de carga)

- [ ] **Step 5: Verificación manual — comportamiento idéntico al actual**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py`

En el browser: confirmar que KPIs, grilla "Análisis Cruzado" y gráfico se ven exactamente igual que antes de este refactor (mismos números). Este paso es clave: si algo cambió acá, es un bug del refactor, no de la feature nueva.

- [ ] **Step 6: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "refactor: separar carga base de datos del fetch de AnalisisLote parametrizable por corte"
```

---

### Task 4: UI de Fechas de Corte + slicer, conectado a la grilla y KPIs

**Files:**
- Modify: `_resumen_general.py:1` (import), `_resumen_general.py` (nueva sección entre Filtros y KPI Strip, y línea que arma `filtered` con el corte activo en vez de `None`)

**Interfaces:**
- Consumes: `build_filtered(stock, analisis_lote_df, pendiente, filters)`, `load_analisis_lote(fecha_corte)` (Task 3)
- Produces: `fecha_corte_activa_iso: str | None` — usado por Task 5 para saber cuál corte quedó activo (aunque Task 5 recalcula las 3 fechas de forma independiente, este valor debe seguir existiendo con este nombre para que la grilla/KPIs y el gráfico usen la misma fuente de fechas).

- [ ] **Step 1: Agregar `date` al import de `datetime`**

En `_resumen_general.py`, línea 1, reemplazar:

```python
from datetime import datetime
```

por:

```python
from datetime import date, datetime
```

- [ ] **Step 2: Insertar la sección de Fechas de Corte y actualizar el cálculo de `filtered`**

En `_resumen_general.py`, la línea (del Task 3, Step 2):

```python
filters = {field: st.session_state.get(f"filter_{field}", []) for field, _ in FILTER_CHAIN}
filtered = build_filtered(stock, load_analisis_lote(None), pendiente, filters)
```

Reemplazarla por:

```python
filters = {field: st.session_state.get(f"filter_{field}", []) for field, _ in FILTER_CHAIN}

# ── FECHAS DE CORTE — PLANIFICADO ───────────────────────────────────────────────
st.markdown('<div class="duhau-section"><div class="duhau-bar"></div><span class="duhau-lbl">Fechas de Corte — Planificado</span></div>', unsafe_allow_html=True)

hoy = date.today()


def _clear_downstream_fechas(idx: int) -> None:
    keys = ["corte_fecha1", "corte_fecha2", "corte_fecha3"]
    for k in keys[idx + 1:]:
        st.session_state[k] = None


col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    fecha1 = st.date_input("Fecha de Corte 1", value=None, min_value=hoy,
                           key="corte_fecha1", on_change=_clear_downstream_fechas, args=(0,))
with col_f2:
    fecha2 = st.date_input("Fecha de Corte 2", value=None, min_value=fecha1 or hoy,
                           key="corte_fecha2", on_change=_clear_downstream_fechas, args=(1,))
with col_f3:
    fecha3 = st.date_input("Fecha de Corte 3", value=None, min_value=fecha2 or fecha1 or hoy,
                           key="corte_fecha3")

opciones_corte = ["Sin corte"]
mapa_corte = {"Sin corte": None}
for label, fecha in [("Corte 1", fecha1), ("Corte 2", fecha2), ("Corte 3", fecha3)]:
    if fecha:
        texto = f"{label} ({fecha:%d/%m})"
        opciones_corte.append(texto)
        mapa_corte[texto] = fecha

if st.session_state.get("corte_activo") not in opciones_corte:
    st.session_state["corte_activo"] = "Sin corte"

corte_seleccionado = st.segmented_control("Corte de análisis", opciones_corte, key="corte_activo")
fecha_corte_activa = mapa_corte.get(corte_seleccionado)
fecha_corte_activa_iso = fecha_corte_activa.isoformat() if fecha_corte_activa else None

filtered = build_filtered(stock, load_analisis_lote(fecha_corte_activa_iso), pendiente, filters)
```

- [ ] **Step 3: Verificar sintaxis**

Run: `cd ~/dashboard-insumos && python -m py_compile _resumen_general.py`
Expected: sin output

- [ ] **Step 4: Correr toda la suite de tests**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest -q`
Expected: todos los tests existentes en verde (no se agregan tests nuevos acá — es UI de Streamlit, mismo criterio que el resto del repo)

- [ ] **Step 5: Verificación manual**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py`

En el browser:
1. Confirmar que aparece la sección "Fechas de Corte — Planificado" con 3 inputs de fecha y el slicer "Corte de análisis", entre "Filtros" y "Resumen" (KPIs).
2. Confirmar que no se puede elegir una fecha anterior a hoy en ninguno de los 3 inputs.
3. Cargar Fecha 1, confirmar que Fecha 2 no permite elegir una fecha anterior a Fecha 1. Repetir con Fecha 3 respecto de Fecha 2.
4. Cambiar Fecha 1 a una fecha posterior a la Fecha 2 ya cargada — confirmar que Fecha 2 y Fecha 3 se limpian automáticamente (sin error de Streamlit).
5. Con las 3 fechas cargadas, confirmar que el slicer muestra 4 opciones: "Sin corte", "Corte 1 (dd/mm)", "Corte 2 (dd/mm)", "Corte 3 (dd/mm)".
6. Elegir cada opción del slicer y confirmar que el KPI "Dif. Planificado/Ejecutado", "Proyección Total" y la columna "Planificado" de la grilla "Análisis Cruzado" cambian según el corte (a fecha de corte más cercana, menor planificado acumulado → mayor Proyección Total, o igual comportamiento esperado según los datos reales).
7. Confirmar que Stock Actual y Pendiente Recepción **no** cambian al alternar el corte.
8. Volver a "Sin corte" y confirmar que los valores vuelven a ser iguales a los de antes de este cambio (Task 3, Step 5).

- [ ] **Step 6: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: UI de fechas de corte con slicer, afecta Planificado en grilla y KPIs"
```

---

### Task 5: Líneas de referencia en el gráfico de Proyección Temporal

**Files:**
- Modify: `_resumen_general.py:352-401` (aprox., sección "PROYECCIÓN TEMPORAL")

**Interfaces:**
- Consumes: `fecha1`, `fecha2`, `fecha3` (`date | None`, Task 4), `build_filtered`, `load_analisis_lote` (Task 3), `filters` (dict), `_fmt` (ya definida en `_resumen_general.py:38`)

- [ ] **Step 1: Agregar las líneas de referencia después del gráfico existente**

En `_resumen_general.py`, ubicar el bloque final de la sección de gráfico:

```python
    fig.update_traces(line_width=2, marker_size=6)
    st.plotly_chart(fig, width="stretch")
```

Reemplazarlo por:

```python
    for label, fecha in [("Corte 1", fecha1), ("Corte 2", fecha2), ("Corte 3", fecha3)]:
        if fecha:
            proy_en_fecha = build_filtered(
                stock, load_analisis_lote(fecha.isoformat()), pendiente, filters
            )["proyeccion"].sum()
            fig.add_vline(
                x=fecha.strftime("%Y-%m"),
                line_dash="dot",
                line_color="#1a3a2a",
                annotation_text=f"{label}: {_fmt(proy_en_fecha)}",
                annotation_position="top",
            )

    fig.update_traces(line_width=2, marker_size=6)
    st.plotly_chart(fig, width="stretch")
```

- [ ] **Step 2: Verificar sintaxis**

Run: `cd ~/dashboard-insumos && python -m py_compile _resumen_general.py`
Expected: sin output

- [ ] **Step 3: Correr toda la suite de tests**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest -q`
Expected: todos los tests en verde

- [ ] **Step 4: Verificación manual**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py`

En el browser:
1. Cargar las 3 fechas de corte.
2. Confirmar que en el gráfico "Proyección de Stock en el Tiempo" aparecen 3 líneas verticales punteadas (una por cada fecha), cada una con una anotación de texto "Corte N: <valor>".
3. Confirmar que la curva mensual de fondo (líneas por Unidad de Negocios) **no cambia** — sigue mostrando todo sin filtrar, sin importar qué corte esté activo en el slicer de la sección anterior.
4. Cambiar el corte activo del slicer (Task 4) y confirmar que las 3 líneas de referencia del gráfico **no cambian** (dependen solo de las 3 fechas cargadas, no del corte activo).
5. Borrar una de las 3 fechas y confirmar que su línea de referencia desaparece del gráfico.

- [ ] **Step 5: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: lineas de referencia por fecha de corte en grafico de proyeccion temporal"
```

---

### Task 6: Validación end-to-end local y despliegue a producción

**Files:**
- Ninguno (solo verificación y deploy)

**Interfaces:**
- Consumes: todo lo anterior, ya commiteado en `main`

- [ ] **Step 1: Correr toda la suite de tests una vez más**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest -q`
Expected: todos los tests en verde

- [ ] **Step 2: Validación manual completa en local con datos reales**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py`

Repetir el checklist completo de Task 4 (Step 5) y Task 5 (Step 4) de punta a punta, con Ezequiel confirmando los números contra su conocimiento del negocio (no solo que "no tira error").

- [ ] **Step 3: Push a main**

```bash
cd ~/dashboard-insumos
git push origin main
```

Expected: push exitoso; Streamlit Cloud redeploya automáticamente.

- [ ] **Step 4: Verificar en producción**

Abrir la URL de producción en Streamlit Cloud y repetir una verificación rápida: cargar las 3 fechas, alternar el slicer, confirmar que KPIs/grilla/gráfico se comportan igual que en local.

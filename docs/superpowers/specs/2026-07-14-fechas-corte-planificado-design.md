# Fechas de Corte para el Detalle de Planificado

**Fecha:** 2026-07-14

## Contexto

Hoy `_resumen_general.py` calcula `planificado_qty` con una sola query SQL agregada (`api/db.py::fetch_analisis_lote_db()`), que suma **todo** lo planificado en la campaña 26-27 sin importar la fecha de cada línea. La tabla origen (`duhau_analisisloteejecutadoplanificado`) tiene una columna `fecha` (texto, formato `YYYY-MM-DD HH:MM:SS.f`) por cada línea de detalle; para la campaña 26-27 y `estado='Planificado'` el rango real es `2025-10-01` a `2027-05-30`.

Ezequiel quiere poder cargar hasta 3 fechas de corte (≥ hoy) y ver qué pasa con la Proyección si el planificado se corta en cada una de esas fechas, **sin tocar** Stock, Pendiente ni Ejecutado.

## Alcance

- Afecta: `planificado_qty` (y todo lo que se deriva: columna "Planificado" en la grilla "Análisis Cruzado", KPI "Dif. Planificado/Ejecutado", KPI "Proyección Total", líneas de referencia en el gráfico de Proyección Temporal).
- No afecta: `stock_qty`, `pendiente_qty`, `ejecutado_qty`, ni la curva mensual existente del gráfico (que sigue mostrando todo sin filtrar).
- Un solo archivo con lógica de negocio nueva: `api/db.py` (parámetro de corte en la query). El resto son cambios de UI/orquestación en `_resumen_general.py`.

## Diseño

### 1. Inputs de fecha

3 `st.date_input` opcionales (`value=None`), ubicados en una nueva subsección "Fechas de Corte — Planificado", **después de Filtros y antes del KPI Strip** (el corte debe existir antes de calcular los KPIs).

- Validación "≥ hoy": `min_value=date.today()` en los 3 inputs (nativo de Streamlit, no requiere validación manual).
- Orden creciente forzado vía `min_value` encadenado:
  - Fecha 2: `min_value = fecha1 or date.today()`
  - Fecha 3: `min_value = fecha2 or fecha1 or date.today()`

### 2. Selector de corte activo

`st.segmented_control` de selección única, opciones dinámicas según las fechas cargadas:

```python
opciones = ["Sin corte"]
if fecha1: opciones.append(f"Corte 1 ({fecha1:%d/%m})")
if fecha2: opciones.append(f"Corte 2 ({fecha2:%d/%m})")
if fecha3: opciones.append(f"Corte 3 ({fecha3:%d/%m})")
corte_activo_label = st.segmented_control("Corte de análisis", opciones, default="Sin corte")
```

Se mapea `corte_activo_label` → la fecha real correspondiente (o `None` si "Sin corte").

### 3. Query parametrizada (`api/db.py`)

`fetch_analisis_lote_db(fecha_corte: str | None = None) -> pd.DataFrame`:

```python
def fetch_analisis_lote_db(fecha_corte=None):
    if fecha_corte:
        query = _QUERY.replace(
            "WHEN estado = 'Planificado' THEN",
            "WHEN estado = 'Planificado' AND fecha::date <= %s THEN",
        )
        params = (fecha_corte,)
    else:
        query = _QUERY
        params = ()
    ...
    cur.execute(query, params)
```

`pg8000.dbapi` usa paramstyle `format` (`%s`), confirmado en el venv local. `Ejecutado` no lleva condición de fecha — no cambia con el corte.

`api/services.py::fetch_analisis_lote(fecha_corte=None)` pasa el parámetro directo a `fetch_analisis_lote_db`.

### 4. Orquestación en `_resumen_general.py`

- `load_data()` (cacheado, sin args) se separa: Stock, Pendiente y Monthly quedan en una carga base sin corte (como hoy). El fetch de AnálisisLote pasa a una función aparte, cacheada por valor de fecha:

```python
@st.cache_data(show_spinner="Calculando planificado...")
def load_analisis_lote(fecha_corte: str | None):
    return fetch_analisis_lote(fecha_corte)
```

  Como máximo 4 variantes en cache (sin corte + 3 fechas) — cambiar de corte no vuelve a pegarle a Stock/Pendiente/Monthly.

- Los filtros (`FILTER_CHAIN`, cascada) se siguen armando sobre el `df` base (sin corte) — el universo de productos/empresas no cambia con el corte, solo las cantidades. Esto ya está cubierto por el merge/outer-join existente.

- Después de definir `filters` (dict campo→selección) y elegir el corte activo, se recalcula `filtered` con un helper:

```python
def build_filtered(analisis_lote_df, filters):
    merged = add_proyeccion(add_zona(merge_services(stock, analisis_lote_df, pendiente)))
    for field, selected in filters.items():
        if selected and field in merged.columns:
            merged = merged[merged[field].isin(selected)]
    return merged

filtered = build_filtered(load_analisis_lote(corte_activo_fecha), filters)
```

  `filtered` reemplaza al `cascade_df` actual y alimenta el KPI Strip y la grilla "Análisis Cruzado" sin más cambios en esa parte del código.

### 5. Líneas de referencia en el gráfico

El gráfico de Proyección Temporal (`df_proy`, curva mensual) **no cambia** — sigue mostrando todo sin filtrar. Por cada fecha cargada (las 3, sin importar cuál esté activa en el slicer), se agrega una línea vertical + anotación con el valor exacto de Proyección Total a esa fecha:

```python
for label, fecha in [("Corte 1", fecha1), ("Corte 2", fecha2), ("Corte 3", fecha3)]:
    if fecha:
        proy_en_fecha = build_filtered(load_analisis_lote(fecha.isoformat()), filters)["proyeccion"].sum()
        fig.add_vline(
            x=fecha.strftime("%Y-%m"), line_dash="dot", line_color="#1a3a2a",
            annotation_text=f"{label}: {_fmt(proy_en_fecha)}",
            annotation_position="top",
        )
```

Reutiliza el mismo cache de `load_analisis_lote` — si el corte ya está activo en el slicer, no hay query nueva.

## Fuera de alcance

- No se filtra `ejecutado_qty`, `stock_qty` ni `pendiente_qty` por fecha.
- No se agregan tests automatizados nuevos para la UI de fechas (mismo criterio que el resto del dashboard: sin tests de UI de Streamlit); si se agrega lógica pura testeable (ej. la función que arma el `WHERE` parametrizado), sí se cubre con un test unitario.
- No se persiste el corte entre sesiones (vive en `st.session_state`/inputs de la sesión actual, como el resto de los filtros).

## Validación

Se programa y valida localmente (`streamlit run _resumen_general.py` con datos reales de Finnegans) antes de subir a producción — mismo flujo que el cambio anterior (spec → plan → implementación → validación local → commit → push a `main` → verificación en Streamlit Cloud).

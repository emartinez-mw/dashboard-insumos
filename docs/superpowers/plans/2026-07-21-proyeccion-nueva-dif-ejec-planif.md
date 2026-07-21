# Columnas Proyección Nueva y Dif. Ejec/Planif Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar dos columnas calculadas fila a fila ("Dif. Ejec/Planif" y "Proyección Nueva") a la grilla "Análisis Cruzado" y al KPI strip del dashboard de insumos, reordenando la grilla y quitando la columna "Formulación".

**Architecture:** Dos funciones puras nuevas en `data/transform.py` (mismo patrón que `add_proyeccion`), invocadas en los mismos 2 puntos donde ya se invoca `add_proyeccion` en `_resumen_general.py`, más ajustes de presentación (orden de columnas, labels, color, KPI strip) en ese mismo archivo.

**Tech Stack:** Python, pandas, Streamlit, pytest.

## Global Constraints

- Spec de referencia: `docs/superpowers/specs/2026-07-21-proyeccion-nueva-dif-ejec-planif-design.md`.
- `Dif. Ejec/Planif = max(ejecutado_qty - planificado_qty, 0)` — nunca negativo.
- `Proyección Nueva = stock_qty + pendiente_qty - max(planificado_qty - ejecutado_qty, 0)` — no suma excedente de ejecución (a diferencia de `Proyección`).
- Ambas columnas se recalculan cuando el toggle "Ver Relación Principio Activo" está activo, igual que `Proyección`.
- Grilla: se quita `Formulación`, se renombra `Pendiente Recepción` → `Pend. Recepción`.
- `Proyección Nueva` usa el mismo color verde/rojo que `Proyección` en la grilla. `Dif. Ejec/Planif` es una columna numérica simple, sin color.
- El filtro "Solo déficit/superávit" y la descarga de Excel no cambian de comportamiento (siguen atados a `display_cols` / columna `proyeccion` tal cual hoy).
- Entorno del proyecto: `cd ~/dashboard-insumos && source .venv/bin/activate` antes de correr tests o la app.

---

### Task 1: Funciones `add_dif_ejec_planif` y `add_proyeccion_nueva`

**Files:**
- Modify: `data/transform.py:151-154` (después de `add_proyeccion`)
- Test: `tests/test_transform.py:1-7` (import) y agregar tests al final del archivo

**Interfaces:**
- Produces: `add_dif_ejec_planif(df: pd.DataFrame) -> pd.DataFrame` — agrega columna `dif_ejec_planif`. Requiere que `df` tenga `ejecutado_qty` y `planificado_qty`.
- Produces: `add_proyeccion_nueva(df: pd.DataFrame) -> pd.DataFrame` — agrega columna `proyeccion_nueva`. Requiere que `df` tenga `stock_qty`, `pendiente_qty`, `planificado_qty`, `ejecutado_qty`.

- [ ] **Step 1: Actualizar el import y escribir los tests que fallan**

En `tests/test_transform.py`, reemplazar el import (líneas 3-6):

```python
from data.transform import (
    merge_services, add_proyeccion, add_factor_principio_activo,
    apply_factor_principio_activo,
)
```

por:

```python
from data.transform import (
    merge_services, add_proyeccion, add_factor_principio_activo,
    apply_factor_principio_activo, add_dif_ejec_planif, add_proyeccion_nueva,
)
```

Agregar al final del archivo:

```python
def test_add_dif_ejec_planif_ejecutado_mayor():
    df = pd.DataFrame([{"ejecutado_qty": 120.0, "planificado_qty": 100.0}])
    result = add_dif_ejec_planif(df)
    assert result["dif_ejec_planif"].iloc[0] == 20.0


def test_add_dif_ejec_planif_ejecutado_menor():
    df = pd.DataFrame([{"ejecutado_qty": 50.0, "planificado_qty": 150.0}])
    result = add_dif_ejec_planif(df)
    assert result["dif_ejec_planif"].iloc[0] == 0.0


def test_add_dif_ejec_planif_iguales():
    df = pd.DataFrame([{"ejecutado_qty": 80.0, "planificado_qty": 80.0}])
    result = add_dif_ejec_planif(df)
    assert result["dif_ejec_planif"].iloc[0] == 0.0


def test_add_dif_ejec_planif_ambos_cero():
    df = pd.DataFrame([{"ejecutado_qty": 0.0, "planificado_qty": 0.0}])
    result = add_dif_ejec_planif(df)
    assert result["dif_ejec_planif"].iloc[0] == 0.0


def test_add_proyeccion_nueva_planificado_mayor():
    # Igual que test_add_proyeccion_formula: planificado > ejecutado, no hay clip
    # = 100 + 30 - (150 - 50) = 30, idéntico a add_proyeccion en este caso
    df = pd.DataFrame([{
        "stock_qty": 100.0, "pendiente_qty": 30.0,
        "planificado_qty": 150.0, "ejecutado_qty": 50.0,
    }])
    result = add_proyeccion_nueva(df)
    assert result["proyeccion_nueva"].iloc[0] == 30.0


def test_add_proyeccion_nueva_no_suma_excedente_ejecucion():
    # ejecutado > planificado: add_proyeccion sumaria el excedente (45), proyeccion_nueva no (15)
    df = pd.DataFrame([{
        "stock_qty": 10.0, "pendiente_qty": 5.0,
        "planificado_qty": 50.0, "ejecutado_qty": 80.0,
    }])
    resultado_viejo = add_proyeccion(df)
    resultado_nuevo = add_proyeccion_nueva(df)
    assert resultado_viejo["proyeccion"].iloc[0] == 45.0
    assert resultado_nuevo["proyeccion_nueva"].iloc[0] == 15.0


def test_add_proyeccion_nueva_iguales():
    df = pd.DataFrame([{
        "stock_qty": 20.0, "pendiente_qty": 0.0,
        "planificado_qty": 40.0, "ejecutado_qty": 40.0,
    }])
    result = add_proyeccion_nueva(df)
    assert result["proyeccion_nueva"].iloc[0] == 20.0
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && python -m pytest tests/test_transform.py -v 2>&1 | tail -20`
Expected: `ImportError: cannot import name 'add_dif_ejec_planif' from 'data.transform'`

- [ ] **Step 3: Implementar las funciones**

En `data/transform.py`, agregar después de `add_proyeccion` (después de la línea 154):

```python
def add_dif_ejec_planif(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dif_ejec_planif"] = (df["ejecutado_qty"] - df["planificado_qty"]).clip(lower=0)
    return df


def add_proyeccion_nueva(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["proyeccion_nueva"] = (
        df["stock_qty"] + df["pendiente_qty"]
        - (df["planificado_qty"] - df["ejecutado_qty"]).clip(lower=0)
    )
    return df
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && python -m pytest tests/test_transform.py -v 2>&1 | tail -15`
Expected: todos los tests de `test_transform.py` en PASSED, incluidos los 8 nuevos.

- [ ] **Step 5: Commit**

```bash
cd ~/dashboard-insumos
git add data/transform.py tests/test_transform.py
git commit -m "feat: agregar add_dif_ejec_planif y add_proyeccion_nueva"
```

---

### Task 2: Cablear las funciones nuevas en `_resumen_general.py`

**Files:**
- Modify: `_resumen_general.py:27-30` (import)
- Modify: `_resumen_general.py:171-177` (`_apply_factor_if_active`)
- Modify: `_resumen_general.py:180-187` (`build_filtered`)

**Interfaces:**
- Consumes: `add_dif_ejec_planif(df)`, `add_proyeccion_nueva(df)` de Task 1.
- Produces: `filtered` (el DataFrame que consumen KPI strip y grilla) trae ahora las columnas `dif_ejec_planif` y `proyeccion_nueva` siempre pobladas, recalculadas cuando el toggle de factor está activo.

- [ ] **Step 1: Actualizar el import**

Reemplazar (líneas 27-30):

```python
from data.transform import (
    merge_services, add_proyeccion, add_zona, build_proyeccion_temporal,
    add_factor_principio_activo, apply_factor_principio_activo,
)
```

por:

```python
from data.transform import (
    merge_services, add_proyeccion, add_zona, build_proyeccion_temporal,
    add_factor_principio_activo, apply_factor_principio_activo,
    add_dif_ejec_planif, add_proyeccion_nueva,
)
```

- [ ] **Step 2: Actualizar `_apply_factor_if_active`**

Reemplazar (líneas 171-177):

```python
def _apply_factor_if_active(df, id_map, factor_map, active, qty_cols, recompute_proyeccion=False):
    df = add_factor_principio_activo(df, id_map, factor_map)
    if active:
        df = apply_factor_principio_activo(df, qty_cols)
        if recompute_proyeccion:
            df = add_proyeccion(df)
    return df
```

por:

```python
def _apply_factor_if_active(df, id_map, factor_map, active, qty_cols, recompute_proyeccion=False):
    df = add_factor_principio_activo(df, id_map, factor_map)
    if active:
        df = apply_factor_principio_activo(df, qty_cols)
        if recompute_proyeccion:
            df = add_proyeccion(df)
            df = add_dif_ejec_planif(df)
            df = add_proyeccion_nueva(df)
    return df
```

- [ ] **Step 3: Actualizar `build_filtered`**

Reemplazar (líneas 180-187):

```python
def build_filtered(stock, analisis_lote_df, pendiente, filters):
    merged = merge_services(stock, analisis_lote_df, pendiente)
    merged = add_zona(merged)
    merged = add_proyeccion(merged)
    for field, selected in filters.items():
        if selected and field in merged.columns:
            merged = merged[merged[field].isin(selected)]
    return merged
```

por:

```python
def build_filtered(stock, analisis_lote_df, pendiente, filters):
    merged = merge_services(stock, analisis_lote_df, pendiente)
    merged = add_zona(merged)
    merged = add_proyeccion(merged)
    merged = add_dif_ejec_planif(merged)
    merged = add_proyeccion_nueva(merged)
    for field, selected in filters.items():
        if selected and field in merged.columns:
            merged = merged[merged[field].isin(selected)]
    return merged
```

- [ ] **Step 4: Verificar sintaxis y que la suite completa sigue pasando**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && python -m py_compile _resumen_general.py && python -m pytest tests/ -q 2>&1 | tail -5`
Expected: `py_compile` no imprime nada (éxito), y `44 passed` (36 anteriores + 8 de Task 1). Ningún test de `_resumen_general.py` existe, así que esta suite no cubre este archivo directamente — la validación funcional queda para la Task 5.

- [ ] **Step 5: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: recalcular dif_ejec_planif y proyeccion_nueva en build_filtered y el toggle de factor"
```

---

### Task 3: Reordenar la grilla "Análisis Cruzado", quitar Formulación y agregar color a Proyección Nueva

**Files:**
- Modify: `_resumen_general.py:354-377` (`display_cols`, `col_labels`, `NUM_COLS`)
- Modify: `_resumen_general.py:414-421` (subset de color en `st.dataframe`)

**Interfaces:**
- Consumes: columnas `dif_ejec_planif`, `proyeccion_nueva` en `filtered` (de Task 2).
- Produces: `table_df` con las columnas y el orden final; `NUM_COLS` y el subset de color usados más abajo en el mismo archivo para formato y estilo.

- [ ] **Step 1: Reordenar `display_cols`, actualizar `col_labels` y `NUM_COLS`**

Reemplazar (líneas 354-377):

```python
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
```

por:

```python
display_cols = [c for c in [
    "EMPRESA", "FAMILIA", "SUBFAMILIA", "PRINCIPIOACTIVO",
    "PRODUCTO", "CENTROLOGISTICO",
    "stock_qty", "planificado_qty", "ejecutado_qty", "dif_ejec_planif",
    "pendiente_qty", "proyeccion", "proyeccion_nueva",
] if c in filtered.columns]

col_labels = {
    "PRODUCTO":         "Producto",
    "EMPRESAPADRE":     "Empresa",
    "EMPRESA":          "Unidad de Negocios",
    "FAMILIA":          "Familia",
    "SUBFAMILIA":       "Subfamilia",
    "PRINCIPIOACTIVO":  "Principio Activo",
    "CENTROLOGISTICO":  "Centro Distribución",
    "stock_qty":        "Stock Actual",
    "planificado_qty":  "Planificado",
    "ejecutado_qty":    "Ejecutado",
    "dif_ejec_planif":  "Dif. Ejec/Planif",
    "pendiente_qty":    "Pend. Recepción",
    "proyeccion":       "Proyección",
    "proyeccion_nueva": "Proyección Nueva",
}

table_df = filtered[display_cols].copy().rename(columns=col_labels)
NUM_COLS = [
    "Stock Actual", "Planificado", "Ejecutado", "Dif. Ejec/Planif",
    "Pend. Recepción", "Proyección", "Proyección Nueva",
]
```

- [ ] **Step 2: Aplicar el color de Proyección también a Proyección Nueva**

Reemplazar (líneas 414-421):

```python
st.dataframe(
    table_df.style
        .format("{:,.2f}", subset=num_cols_present, na_rep="")
        .map(color_proyeccion, subset=["Proyección"] if "Proyección" in table_df.columns else [])
        .set_properties(**{"font-family": "Work Sans, sans-serif", "font-size": "13px"}),
    width="stretch",
    hide_index=True,
)
```

por:

```python
proyeccion_color_cols = [c for c in ["Proyección", "Proyección Nueva"] if c in table_df.columns]

st.dataframe(
    table_df.style
        .format("{:,.2f}", subset=num_cols_present, na_rep="")
        .map(color_proyeccion, subset=proyeccion_color_cols)
        .set_properties(**{"font-family": "Work Sans, sans-serif", "font-size": "13px"}),
    width="stretch",
    hide_index=True,
)
```

- [ ] **Step 3: Verificar sintaxis, suite de tests y presencia de los cambios**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && python -m py_compile _resumen_general.py && python -m pytest tests/ -q 2>&1 | tail -5 && grep -n "Formulación\|Dif. Ejec/Planif\|Proyección Nueva\|Pend. Recepción" _resumen_general.py`
Expected: `py_compile` sin salida, `44 passed`, y el `grep` muestra `"Dif. Ejec/Planif"`, `"Proyección Nueva"` y `"Pend. Recepción"` en `col_labels`/`NUM_COLS`, sin ninguna ocurrencia de `"Formulación"` (el label se quitó del dict; el campo `FORMULACION` puede seguir existiendo en otras partes del pipeline de datos, pero ya no en este archivo).

- [ ] **Step 4: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: reordenar grilla Analisis Cruzado, quitar Formulacion y colorear Proyeccion Nueva"
```

---

### Task 4: Tercera fila del KPI strip con Dif. Ejec/Planif y Proyección Nueva

**Files:**
- Modify: `_resumen_general.py:298-349` (totales, badge, `_kpi_card` y `kpi_cards`)

**Interfaces:**
- Consumes: columnas `dif_ejec_planif`, `proyeccion_nueva` en `filtered` (de Task 2), función existente `_kpi_card(label, value_html, unit_html, border_right, border_bottom)`.
- Produces: nueva función `_kpi_placeholder()` usada solo en este bloque para la celda vacía de la fila 3.

- [ ] **Step 1: Agregar los totales nuevos y el color/badge de Proyección Nueva**

Reemplazar (líneas 298-308):

```python
stock_total       = filtered["stock_qty"].sum()
planificado_total = filtered["planificado_qty"].sum()
ejecutado_total   = filtered["ejecutado_qty"].sum()
dif_plan_ejec      = planificado_total - ejecutado_total
pendiente_total   = filtered["pendiente_qty"].sum()
proy_total        = filtered["proyeccion"].sum() if "proyeccion" in filtered.columns else 0.0

proy_color = "#1a6b3a" if proy_total >= 0 else "#dc2626"
proy_bg    = "#dcfce7" if proy_total >= 0 else "#fee2e2"
proy_label = "▲ Positiva" if proy_total >= 0 else "▼ Negativa"
```

por:

```python
stock_total       = filtered["stock_qty"].sum()
planificado_total = filtered["planificado_qty"].sum()
ejecutado_total   = filtered["ejecutado_qty"].sum()
dif_plan_ejec      = planificado_total - ejecutado_total
pendiente_total   = filtered["pendiente_qty"].sum()
proy_total        = filtered["proyeccion"].sum() if "proyeccion" in filtered.columns else 0.0
dif_ejec_planif_total  = filtered["dif_ejec_planif"].sum() if "dif_ejec_planif" in filtered.columns else 0.0
proyeccion_nueva_total = filtered["proyeccion_nueva"].sum() if "proyeccion_nueva" in filtered.columns else 0.0

proy_color = "#1a6b3a" if proy_total >= 0 else "#dc2626"
proy_bg    = "#dcfce7" if proy_total >= 0 else "#fee2e2"
proy_label = "▲ Positiva" if proy_total >= 0 else "▼ Negativa"

proy_nueva_color = "#1a6b3a" if proyeccion_nueva_total >= 0 else "#dc2626"
proy_nueva_bg    = "#dcfce7" if proyeccion_nueva_total >= 0 else "#fee2e2"
proy_nueva_label = "▲ Positiva" if proyeccion_nueva_total >= 0 else "▼ Negativa"
```

- [ ] **Step 2: Agregar el badge y el placeholder de celda vacía**

Ubicar el bloque `_proy_badge` (después de la definición de `_unit`, antes de `kpi_cards`):

```python
_proy_badge = f"""<div style="display:inline-flex;align-items:center;gap:3px;margin-top:8px;
                font-size:9px;font-weight:700;padding:2px 8px;border-radius:2px;
                background:{proy_bg};color:{proy_color};font-family:'Work Sans',sans-serif">
      {proy_label}
    </div>"""
```

Agregar justo después:

```python
_proy_nueva_badge = f"""<div style="display:inline-flex;align-items:center;gap:3px;margin-top:8px;
                font-size:9px;font-weight:700;padding:2px 8px;border-radius:2px;
                background:{proy_nueva_bg};color:{proy_nueva_color};font-family:'Work Sans',sans-serif">
      {proy_nueva_label}
    </div>"""


def _kpi_placeholder():
    return '<div style="padding:22px 22px 19px;background:#fff"></div>'
```

- [ ] **Step 3: Actualizar `kpi_cards` con la tercera fila**

Reemplazar (líneas 335-342):

```python
kpi_cards = [
    _kpi_card("Stock Actual", _fmt(stock_total), _unit("kg"), border_right=True, border_bottom=True),
    _kpi_card("Planificado", _fmt(planificado_total), _unit("Kg/Lit"), border_right=True, border_bottom=True),
    _kpi_card("Ejecutado", _fmt(ejecutado_total), _unit("Kg/Lit"), border_right=False, border_bottom=True),
    _kpi_card("Dif. Planificado / Ejecutado", _fmt(dif_plan_ejec), _unit("Kg/Lit"), border_right=True, border_bottom=False),
    _kpi_card("Pendiente Recepción", _fmt(pendiente_total), _unit("Kg/Lit"), border_right=True, border_bottom=False),
    _kpi_card("Proyección Total", f'<span style="color:{proy_color}">{_fmt(proy_total)}</span>', _proy_badge, border_right=False, border_bottom=False),
]
```

por:

```python
kpi_cards = [
    _kpi_card("Stock Actual", _fmt(stock_total), _unit("kg"), border_right=True, border_bottom=True),
    _kpi_card("Planificado", _fmt(planificado_total), _unit("Kg/Lit"), border_right=True, border_bottom=True),
    _kpi_card("Ejecutado", _fmt(ejecutado_total), _unit("Kg/Lit"), border_right=False, border_bottom=True),
    _kpi_card("Dif. Planificado / Ejecutado", _fmt(dif_plan_ejec), _unit("Kg/Lit"), border_right=True, border_bottom=True),
    _kpi_card("Pendiente Recepción", _fmt(pendiente_total), _unit("Kg/Lit"), border_right=True, border_bottom=True),
    _kpi_card("Proyección Total", f'<span style="color:{proy_color}">{_fmt(proy_total)}</span>', _proy_badge, border_right=False, border_bottom=True),
    _kpi_card("Dif. Ejec/Planif", _fmt(dif_ejec_planif_total), _unit("Kg/Lit"), border_right=True, border_bottom=False),
    _kpi_card("Proyección Nueva", f'<span style="color:{proy_nueva_color}">{_fmt(proyeccion_nueva_total)}</span>', _proy_nueva_badge, border_right=True, border_bottom=False),
    _kpi_placeholder(),
]
```

- [ ] **Step 4: Verificar sintaxis y suite de tests**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && python -m py_compile _resumen_general.py && python -m pytest tests/ -q 2>&1 | tail -5`
Expected: `py_compile` sin salida, `44 passed`.

- [ ] **Step 5: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: agregar tercera fila al KPI strip con Dif. Ejec/Planif y Proyeccion Nueva"
```

---

### Task 5: Validación manual local

**Files:** ninguno (solo verificación, sin cambios de código)

- [ ] **Step 1: Levantar la app localmente**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py`

- [ ] **Step 2: Verificar la grilla "Análisis Cruzado"**

Confirmar en el navegador:
- El orden de columnas es: Unidad de Negocios, Familia, Subfamilia, Principio Activo, Producto, Centro Distribución, Stock Actual, Planificado, Ejecutado, Dif. Ejec/Planif, Pend. Recepción, Proyección, Proyección Nueva.
- No aparece la columna "Formulación".
- "Proyección" y "Proyección Nueva" tienen fondo verde/rojo según signo; "Dif. Ejec/Planif" no tiene color.
- La descarga de Excel incluye las columnas nuevas.

- [ ] **Step 3: Verificar el KPI strip "Resumen"**

Confirmar que aparece una tercera fila con "Dif. Ejec/Planif" y "Proyección Nueva" (con badge verde/rojo), con un espacio vacío a la derecha, y que las filas 1 y 2 no cambiaron de contenido.

- [ ] **Step 4: Verificar el toggle "Ver Relación Principio Activo"**

Activar el toggle y confirmar que "Dif. Ejec/Planif" y "Proyección Nueva" (columna y KPI) cambian de valor de forma consistente con "Proyección"; desactivarlo y confirmar que vuelven a los valores originales.

- [ ] **Step 5: Reportar el resultado**

Si todo se ve correcto, avisar que la feature quedó validada localmente y lista para pushear a `main` (redeploy automático en Streamlit Cloud). Si algo no coincide, anotar el detalle antes de continuar.

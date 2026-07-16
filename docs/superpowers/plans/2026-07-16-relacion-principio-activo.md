# Factor Relación Principio Activo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Traer el factor `relacionprincipioactivo` (tabla `duhau_dw_productos_duhau` del mismo Data Warehouse) conectado por `ProductoID`, con un toggle "Ver Relación Principio Activo" que, al activarse, recalcula `stock_qty`, `planificado_qty`, `ejecutado_qty`, `pendiente_qty` y `proyeccion` (KPI strip, grilla "Análisis Cruzado" y curva del gráfico de Proyección Temporal) multiplicándolos por ese factor.

**Architecture:** Dos queries nuevas y livianas en `api/db.py` (sin tocar las 3 queries existentes) traen un mapa `PRODUCTO → PRODUCTOID` (desde `duhau_analisisloteejecutadoplanificado`) y un mapa `PRODUCTOID → factor` (desde `duhau_dw_productos_duhau`). `data/transform.py` combina ambos mapas por `ProductoID` y los pega al dataset existente por `PRODUCTO`, aplicando la regla nulo/cero→1 (`add_factor_principio_activo`), y una función separada (`apply_factor_principio_activo`) multiplica las columnas de cantidad indicadas por el factor — se llama una vez sobre `filtered` (KPI + grilla) y otra vez sobre `df_monthly` (antes de `build_proyeccion_temporal`, que no necesita cambios). El toggle vive antes de la sección "Resumen" en `_resumen_general.py` porque el KPI strip se renderiza primero en el script.

**Tech Stack:** pandas (`pd.to_numeric(errors="coerce")` para manejar el string literal `"NULL"` que usa el DW en vez de NULL real), Streamlit (`st.toggle`, `st.cache_data`), pg8000 (mismo patrón de conexión que las queries existentes).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-16-relacion-principio-activo-design.md`
- Join verificado: `laborproductoid` (AnalisisLote) = `productoid` (Productos), 1 a 1 sin fan-out — confirmado con `SELECT laborproducto, count(DISTINCT laborproductoid) ... HAVING count(...) > 1` → 0 filas sobre el universo de 212 productos que usa el dashboard.
- Regla de negocio: `relacionprincipioactivo` nulo (incluido el string literal `"NULL"`) o `0` → factor `1.0` (no altera la cantidad).
- Comportamiento default (toggle apagado): idéntico al actual, sin cambios de ningún tipo.
- No se agrega ninguna columna nueva visible en la grilla — solo se recalculan las columnas existentes.
- No se toca `_QUERY`, `_QUERY_MONTHLY` ni `_QUERY_RAW` en `api/db.py`.
- Se valida localmente contra datos reales de Finnegans antes de subir a producción (mismo flujo que los cambios anteriores del repo).

---

### Task 1: Fetch de mapa `PRODUCTO → PRODUCTOID`

**Files:**
- Modify: `api/db.py` (agregar al final del archivo, después de `fetch_analisis_lote_db`)
- Modify: `api/services.py` (agregar al final del archivo, después de `fetch_pendiente`)
- Test: `tests/test_services.py`

**Interfaces:**
- Produces: `fetch_producto_id_map_db() -> pd.DataFrame` (columnas `PRODUCTO`, `PRODUCTOID`); `fetch_producto_id_map() -> pd.DataFrame` — usada por Task 5.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_services.py`, actualizando el import de la primera línea:

```python
from api.services import fetch_stock, fetch_analisis_lote, fetch_pendiente, fetch_producto_id_map
```

Y al final del archivo:

```python
def test_fetch_producto_id_map_returns_dataframe_from_db():
    sample = pd.DataFrame([{"PRODUCTO": "HERB A", "PRODUCTOID": "123"}])
    with patch("api.db.fetch_producto_id_map_db", return_value=sample):
        df = fetch_producto_id_map()
    assert "PRODUCTOID" in df.columns
    assert df["PRODUCTOID"].iloc[0] == "123"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_services.py::test_fetch_producto_id_map_returns_dataframe_from_db -v`
Expected: FAIL con `ImportError: cannot import name 'fetch_producto_id_map'`

- [ ] **Step 3: Implementar `fetch_producto_id_map_db` en `api/db.py`**

Agregar al final de `api/db.py`:

```python
_QUERY_PRODUCTO_ID_MAP = f"""
SELECT DISTINCT
    laborproducto   AS "PRODUCTO",
    laborproductoid AS "PRODUCTOID"
FROM {_TABLE}
WHERE tipo     = '02 - Insumo'
  AND campania  = '26-27 Campaña'
  AND estado   != 'Ordenado'
"""


def fetch_producto_id_map_db() -> pd.DataFrame:
    _EMPTY = ["PRODUCTO", "PRODUCTOID"]
    try:
        conn = _conn()
        cur = conn.cursor()
        cur.execute(_QUERY_PRODUCTO_ID_MAP)
        cols = [desc[0] for desc in cur.description]
        result = pd.DataFrame(cur.fetchall(), columns=cols)
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"[db] Error obteniendo mapa de ProductoID: {e}")
        return pd.DataFrame(columns=_EMPTY)
```

- [ ] **Step 4: Implementar `fetch_producto_id_map` en `api/services.py`**

Agregar al final de `api/services.py`:

```python
def fetch_producto_id_map() -> pd.DataFrame:
    from api.db import fetch_producto_id_map_db
    return fetch_producto_id_map_db()
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_services.py -v`
Expected: todos los tests de `test_services.py` en verde (incluido el nuevo)

- [ ] **Step 6: Commit**

```bash
cd ~/dashboard-insumos
git add api/db.py api/services.py tests/test_services.py
git commit -m "feat: fetch de mapa PRODUCTO a ProductoID desde AnalisisLote"
```

---

### Task 2: Fetch de mapa `PRODUCTOID → factor relacionprincipioactivo`

**Files:**
- Modify: `api/db.py` (agregar después de `fetch_producto_id_map_db`, Task 1)
- Modify: `api/services.py` (agregar después de `fetch_producto_id_map`, Task 1)
- Test: `tests/test_services.py`

**Interfaces:**
- Consumes: nada de tasks anteriores (independiente de Task 1)
- Produces: `fetch_relacion_principio_activo_db() -> pd.DataFrame` (columnas `PRODUCTOID`, `FACTOR_PA_RAW`); `fetch_relacion_principio_activo() -> pd.DataFrame` — usada por Task 5.

- [ ] **Step 1: Escribir el test que falla**

Actualizar el import en `tests/test_services.py`:

```python
from api.services import (
    fetch_stock, fetch_analisis_lote, fetch_pendiente,
    fetch_producto_id_map, fetch_relacion_principio_activo,
)
```

Y agregar al final del archivo:

```python
def test_fetch_relacion_principio_activo_returns_dataframe_from_db():
    sample = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0.61"}])
    with patch("api.db.fetch_relacion_principio_activo_db", return_value=sample):
        df = fetch_relacion_principio_activo()
    assert "FACTOR_PA_RAW" in df.columns
    assert df["FACTOR_PA_RAW"].iloc[0] == "0.61"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_services.py::test_fetch_relacion_principio_activo_returns_dataframe_from_db -v`
Expected: FAIL con `ImportError: cannot import name 'fetch_relacion_principio_activo'`

- [ ] **Step 3: Implementar `fetch_relacion_principio_activo_db` en `api/db.py`**

Agregar al final de `api/db.py`:

```python
_QUERY_RELACION_PRINCIPIO_ACTIVO = """
SELECT
    productoid               AS "PRODUCTOID",
    relacionprincipioactivo  AS "FACTOR_PA_RAW"
FROM duhau_dw_productos_duhau
"""


def fetch_relacion_principio_activo_db() -> pd.DataFrame:
    _EMPTY = ["PRODUCTOID", "FACTOR_PA_RAW"]
    try:
        conn = _conn()
        cur = conn.cursor()
        cur.execute(_QUERY_RELACION_PRINCIPIO_ACTIVO)
        cols = [desc[0] for desc in cur.description]
        result = pd.DataFrame(cur.fetchall(), columns=cols)
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"[db] Error obteniendo relación principio activo: {e}")
        return pd.DataFrame(columns=_EMPTY)
```

- [ ] **Step 4: Implementar `fetch_relacion_principio_activo` en `api/services.py`**

Agregar al final de `api/services.py`:

```python
def fetch_relacion_principio_activo() -> pd.DataFrame:
    from api.db import fetch_relacion_principio_activo_db
    return fetch_relacion_principio_activo_db()
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_services.py -v`
Expected: todos los tests de `test_services.py` en verde (incluido el nuevo)

- [ ] **Step 6: Commit**

```bash
cd ~/dashboard-insumos
git add api/db.py api/services.py tests/test_services.py
git commit -m "feat: fetch del factor relacionprincipioactivo desde duhau_dw_productos_duhau"
```

---

### Task 3: `add_factor_principio_activo` en `data/transform.py`

**Files:**
- Modify: `data/transform.py` (agregar al final del archivo, después de `add_proyeccion`)
- Test: `tests/test_transform.py`

**Interfaces:**
- Consumes: nada de tasks anteriores (función pura, se testea con DataFrames armados a mano)
- Produces: `add_factor_principio_activo(df: pd.DataFrame, id_map: pd.DataFrame, factor_map: pd.DataFrame) -> pd.DataFrame` — agrega columna `factor_pa` a `df`. Usada por Task 5.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_transform.py`, actualizando el import de la primera línea:

```python
from data.transform import (
    merge_services, add_proyeccion, add_factor_principio_activo, apply_factor_principio_activo,
)
```

Y al final del archivo:

```python
def test_add_factor_principio_activo_usa_valor_real():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0.61"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 0.61


def test_add_factor_principio_activo_null_string_default_a_uno():
    # El DW guarda los nulos como el string literal "NULL", no como NULL real
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "NULL"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 1.0


def test_add_factor_principio_activo_cero_default_a_uno():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 1.0


def test_add_factor_principio_activo_producto_sin_match_default_a_uno():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA DESCONOCIDO", "EMPRESA": "AED"}])
    id_map = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "PRODUCTOID": "123"}])
    factor_map = pd.DataFrame([{"PRODUCTOID": "123", "FACTOR_PA_RAW": "0.61"}])

    result = add_factor_principio_activo(df, id_map, factor_map)

    assert result["factor_pa"].iloc[0] == 1.0


def test_add_factor_principio_activo_mapas_vacios_default_a_uno():
    df = pd.DataFrame([{"PRODUCTO": "HERBICIDA A", "EMPRESA": "AED"}])
    result = add_factor_principio_activo(df, pd.DataFrame(), pd.DataFrame())
    assert result["factor_pa"].iloc[0] == 1.0
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_transform.py -k factor_principio_activo -v`
Expected: FAIL con `ImportError: cannot import name 'add_factor_principio_activo'`

- [ ] **Step 3: Implementar `add_factor_principio_activo`**

Agregar al final de `data/transform.py`:

```python
def add_factor_principio_activo(df: pd.DataFrame, id_map: pd.DataFrame,
                                 factor_map: pd.DataFrame) -> pd.DataFrame:
    """Agrega columna factor_pa a df uniendo PRODUCTO -> PRODUCTOID -> factor. NULL o 0 -> 1."""
    df = df.copy()
    if id_map.empty or factor_map.empty:
        df["factor_pa"] = 1.0
        return df
    ref = id_map.merge(factor_map, on="PRODUCTOID", how="left")[["PRODUCTO", "FACTOR_PA_RAW"]]
    df = df.merge(ref, on="PRODUCTO", how="left")
    factor = pd.to_numeric(df["FACTOR_PA_RAW"], errors="coerce")
    df["factor_pa"] = factor.fillna(1.0).replace(0, 1.0)
    return df.drop(columns=["FACTOR_PA_RAW"])
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_transform.py -k factor_principio_activo -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/dashboard-insumos
git add data/transform.py tests/test_transform.py
git commit -m "feat: add_factor_principio_activo con regla nulo/cero a uno"
```

---

### Task 4: `apply_factor_principio_activo` en `data/transform.py`

**Files:**
- Modify: `data/transform.py` (agregar después de `add_factor_principio_activo`, Task 3)
- Test: `tests/test_transform.py`

**Interfaces:**
- Consumes: `factor_pa` (columna producida por `add_factor_principio_activo`, Task 3)
- Produces: `apply_factor_principio_activo(df: pd.DataFrame, qty_cols: list) -> pd.DataFrame` — usada por Task 5, dos veces (una con las columnas de `filtered`, otra con las de `df_monthly`).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_transform.py` (el import ya se actualizó en Task 3):

```python
def test_apply_factor_principio_activo_multiplica_columnas_indicadas():
    df = pd.DataFrame([{
        "stock_qty": 100.0, "planificado_qty": 150.0,
        "ejecutado_qty": 50.0, "pendiente_qty": 30.0,
        "factor_pa": 0.5,
    }])
    result = apply_factor_principio_activo(
        df, ["stock_qty", "planificado_qty", "ejecutado_qty", "pendiente_qty"]
    )
    assert result["stock_qty"].iloc[0] == 50.0
    assert result["planificado_qty"].iloc[0] == 75.0
    assert result["ejecutado_qty"].iloc[0] == 25.0
    assert result["pendiente_qty"].iloc[0] == 15.0


def test_apply_factor_principio_activo_no_toca_columnas_no_indicadas():
    df = pd.DataFrame([{
        "planificado_mes": 100.0, "ejecutado_mes": 40.0,
        "ANO_MES": "2026-08", "factor_pa": 2.0,
    }])
    result = apply_factor_principio_activo(df, ["planificado_mes", "ejecutado_mes"])
    assert result["planificado_mes"].iloc[0] == 200.0
    assert result["ejecutado_mes"].iloc[0] == 80.0
    assert result["ANO_MES"].iloc[0] == "2026-08"
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_transform.py -k apply_factor_principio_activo -v`
Expected: FAIL con `ImportError: cannot import name 'apply_factor_principio_activo'`

- [ ] **Step 3: Implementar `apply_factor_principio_activo`**

Agregar al final de `data/transform.py`:

```python
def apply_factor_principio_activo(df: pd.DataFrame, qty_cols: list) -> pd.DataFrame:
    """Multiplica cada columna de qty_cols por factor_pa. Requiere que df ya tenga factor_pa."""
    df = df.copy()
    for col in qty_cols:
        if col in df.columns:
            df[col] = df[col] * df["factor_pa"]
    return df
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_transform.py -k apply_factor_principio_activo -v`
Expected: `2 passed`

- [ ] **Step 5: Correr toda la suite de tests**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest -q`
Expected: todos los tests en verde

- [ ] **Step 6: Commit**

```bash
cd ~/dashboard-insumos
git add data/transform.py tests/test_transform.py
git commit -m "feat: apply_factor_principio_activo multiplica cantidades por el factor"
```

---

### Task 5: Toggle y recálculo en `_resumen_general.py`

**Files:**
- Modify: `_resumen_general.py:23-24` (imports)
- Modify: `_resumen_general.py:155-158` (agregar loader cacheado, después de `load_analisis_lote`)
- Modify: `_resumen_general.py:263-265` (insertar toggle y recálculo entre `filtered = build_filtered(...)` y `# ── KPI STRIP`)

**Interfaces:**
- Consumes: `fetch_producto_id_map`, `fetch_relacion_principio_activo` (Task 1, 2); `add_factor_principio_activo`, `apply_factor_principio_activo` (Task 3, 4)
- Produces: `filtered` y `df_monthly` recalculados en memoria — no se agregan nuevas funciones reusables, es orquestación final.

- [ ] **Step 1: Actualizar los imports**

En `_resumen_general.py`, reemplazar (líneas 23-24):

```python
from api.services import fetch_stock, fetch_analisis_lote, fetch_analisis_lote_monthly, fetch_pendiente
from data.transform import merge_services, add_proyeccion, add_zona, build_proyeccion_temporal
```

por:

```python
from api.services import (
    fetch_stock, fetch_analisis_lote, fetch_analisis_lote_monthly, fetch_pendiente,
    fetch_producto_id_map, fetch_relacion_principio_activo,
)
from data.transform import (
    merge_services, add_proyeccion, add_zona, build_proyeccion_temporal,
    add_factor_principio_activo, apply_factor_principio_activo,
)
```

- [ ] **Step 2: Agregar el loader cacheado del factor**

En `_resumen_general.py`, después de (líneas 155-157):

```python
@st.cache_data(show_spinner="Calculando planificado...")
def load_analisis_lote(fecha_corte: Optional[str]):
    return fetch_analisis_lote(fecha_corte)
```

agregar:

```python
@st.cache_data(show_spinner="Cargando factor de principio activo...")
def load_factor_principio_activo():
    return fetch_producto_id_map(), fetch_relacion_principio_activo()
```

- [ ] **Step 3: Insertar el toggle y el recálculo condicional**

En `_resumen_general.py`, reemplazar (líneas 263-265):

```python
filtered = build_filtered(stock, load_analisis_lote(fecha_corte_activa_iso), pendiente, filters)

# ── KPI STRIP ─────────────────────────────────────────────────────────────────
```

por:

```python
filtered = build_filtered(stock, load_analisis_lote(fecha_corte_activa_iso), pendiente, filters)

# ── FACTOR RELACIÓN PRINCIPIO ACTIVO ────────────────────────────────────────────
id_map, factor_map = load_factor_principio_activo()
filtered = add_factor_principio_activo(filtered, id_map, factor_map)
df_monthly = add_factor_principio_activo(df_monthly, id_map, factor_map)

ver_factor_pa = st.toggle("Ver Relación Principio Activo", value=False)

if ver_factor_pa:
    filtered = apply_factor_principio_activo(
        filtered, ["stock_qty", "planificado_qty", "ejecutado_qty", "pendiente_qty"]
    )
    filtered = add_proyeccion(filtered)
    df_monthly = apply_factor_principio_activo(df_monthly, ["planificado_mes", "ejecutado_mes"])

# ── KPI STRIP ─────────────────────────────────────────────────────────────────
```

- [ ] **Step 4: Verificar sintaxis**

Run: `cd ~/dashboard-insumos && python -m py_compile _resumen_general.py`
Expected: sin output

- [ ] **Step 5: Correr toda la suite de tests**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest -q`
Expected: todos los tests en verde (este task no agrega tests nuevos — es orquestación de UI, mismo criterio que el resto del repo)

- [ ] **Step 6: Verificación manual**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py`

En el browser:
1. Confirmar que aparece el toggle "Ver Relación Principio Activo" justo antes de la sección "Resumen" (KPIs), apagado por default.
2. Con el toggle apagado, confirmar que KPI strip, grilla y gráfico se ven exactamente igual que antes de este cambio (mismos números).
3. Filtrar por Producto = "Glifosato Panzer Gold" (factor real `0.61` cargado en Finnegans). Activar el toggle y confirmar que Stock Actual, Planificado, Ejecutado, Pendiente Recepción y Proyección Total se multiplican por `0.61` respecto de los valores con el toggle apagado.
4. Filtrar por un producto sin factor cargado (la mayoría) y confirmar que activar el toggle **no cambia** sus valores (factor `1`).
5. Con el toggle activado y sin filtro de producto, confirmar que el gráfico "Proyección de Stock en el Tiempo" también cambia (la curva ya no es igual a la del toggle apagado).
6. Alternar el toggle varias veces y confirmar que siempre vuelve a los valores originales al apagarlo (no hay corrupción de estado entre reruns).

- [ ] **Step 7: Commit**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: toggle Ver Relacion Principio Activo recalcula KPI, grilla y grafico"
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

Repetir el checklist completo de Task 5 (Step 6) de punta a punta, con Ezequiel confirmando los números contra su conocimiento del negocio (no solo que "no tira error"). Además, pedirle que cargue un par de factores más en Finnegans para otros productos "Glifosato" (de los que hoy tienen `NULL`) y confirmar que aparecen reflejados al activar el toggle sin necesidad de reiniciar la app (el cache de `load_factor_principio_activo` se invalida con el botón "↺ Actualizar" existente).

- [ ] **Step 3: Push a main**

```bash
cd ~/dashboard-insumos
git push origin main
```

Expected: push exitoso; Streamlit Cloud redeploya automáticamente.

- [ ] **Step 4: Verificar en producción**

Abrir la URL de producción en Streamlit Cloud y repetir una verificación rápida: activar el toggle sobre "Glifosato Panzer Gold", confirmar que los valores se recalculan igual que en local.

# Factor Relación Principio Activo

**Fecha:** 2026-07-16

## Contexto

El Data Warehouse de Finnegans tiene una tabla adicional, `duhau_dw_productos_duhau`, con el detalle maestro de productos (5626 filas). De ahí solo necesitamos una columna: `relacionprincipioactivo`, un factor numérico decimal (ej. `0.61`, `0.71`) que convierte cantidad de producto a cantidad equivalente de principio activo. Se conecta con el resto del dataset por `ProductoID` (`laborproductoid` en `duhau_analisisloteejecutadoplanificado` = `productoid` en `duhau_dw_productos_duhau` — verificado 1 a 1 con muestras reales).

Detalle de datos encontrado al explorar (relevante para el diseño):
- Todas las columnas de ambas tablas son `text` en Postgres. Los nulos reales de `relacionprincipioactivo` están guardados como el string literal `"NULL"`, no como NULL de SQL.
- Sobre el universo de productos que usa hoy el dashboard (212 productos distintos, tipo "02 - Insumo", campaña 26-27), el 100% tiene `relacionprincipioactivo` en ese estado "NULL" salvo los que Ezequiel fue cargando manualmente en Finnegans (ej. 3 de 12 productos "Glifosato" ya tienen valor real: Panzer Gold `0.61`, Round Up TOP `0.71`, Sulfosato Touchdown `0.62`).
- Regla de negocio confirmada: si el valor es nulo (incluido el string `"NULL"`) o `0`, se toma como `1` (no altera la cantidad).

## Alcance

- Afecta, solo cuando el toggle está activo: `stock_qty`, `planificado_qty`, `ejecutado_qty`, `pendiente_qty`, `proyeccion` en el KPI strip y en la grilla "Análisis Cruzado", y `planificado_mes`/`ejecutado_mes` (y por lo tanto la curva acumulada) en el gráfico de Proyección Temporal.
- No afecta las queries SQL existentes (`_QUERY`, `_QUERY_MONTHLY`, `_QUERY_RAW` en `api/db.py`) — se agregan dos queries nuevas y livianas, sin modificar las que ya están en producción.
- No se agrega ninguna columna nueva visible en la grilla (el pedido es recalcular las columnas existentes, no mostrar el factor).
- Comportamiento default (toggle apagado): idéntico al actual, sin cambios.

## Diseño

### 1. Queries nuevas (`api/db.py`)

Dos funciones nuevas, mismo patrón try/except y fallback a DataFrame vacío que las funciones existentes (`fetch_analisis_lote_db`, etc.):

```python
_QUERY_PRODUCTO_ID_MAP = """
SELECT DISTINCT
    laborproducto   AS "PRODUCTO",
    laborproductoid AS "PRODUCTOID"
FROM duhau_analisisloteejecutadoplanificado
WHERE tipo = '02 - Insumo'
  AND campania = '26-27 Campaña'
  AND estado != 'Ordenado'
"""

def fetch_producto_id_map_db() -> pd.DataFrame:
    _EMPTY = ["PRODUCTO", "PRODUCTOID"]
    ...  # mismo try/except que fetch_analisis_lote_db


_QUERY_RELACION_PRINCIPIO_ACTIVO = """
SELECT
    productoid            AS "PRODUCTOID",
    relacionprincipioactivo AS "FACTOR_PA_RAW"
FROM duhau_dw_productos_duhau
"""

def fetch_relacion_principio_activo_db() -> pd.DataFrame:
    _EMPTY = ["PRODUCTOID", "FACTOR_PA_RAW"]
    ...  # mismo try/except
```

### 2. Wrappers (`api/services.py`)

```python
def fetch_producto_id_map() -> pd.DataFrame:
    from api.db import fetch_producto_id_map_db
    return fetch_producto_id_map_db()

def fetch_relacion_principio_activo() -> pd.DataFrame:
    from api.db import fetch_relacion_principio_activo_db
    return fetch_relacion_principio_activo_db()
```

### 3. Transformación (`data/transform.py`)

```python
def add_factor_principio_activo(df: pd.DataFrame, id_map: pd.DataFrame,
                                 factor_map: pd.DataFrame) -> pd.DataFrame:
    """Agrega columna factor_pa a df (join PRODUCTO -> PRODUCTOID -> factor). NULL/0 -> 1."""
    df = df.copy()
    ref = id_map.merge(factor_map, on="PRODUCTOID", how="left")[["PRODUCTO", "FACTOR_PA_RAW"]]
    df = df.merge(ref, on="PRODUCTO", how="left")
    factor = pd.to_numeric(df["FACTOR_PA_RAW"], errors="coerce")  # "NULL" (string) y NaN -> NaN
    df["factor_pa"] = factor.fillna(1.0).replace(0, 1.0)
    return df.drop(columns=["FACTOR_PA_RAW"])


def apply_factor_principio_activo(df: pd.DataFrame, qty_cols: list[str]) -> pd.DataFrame:
    """Multiplica las columnas indicadas por factor_pa. Requiere que df ya tenga factor_pa."""
    df = df.copy()
    for col in qty_cols:
        if col in df.columns:
            df[col] = df[col] * df["factor_pa"]
    return df
```

`pd.to_numeric(..., errors="coerce")` resuelve el caso del string literal `"NULL"` sin necesidad de un chequeo de string aparte: al no poder parsearse como número, cae en NaN igual que un NULL real, y de ahí sigue la misma regla `fillna(1.0).replace(0, 1.0)`.

### 4. Orquestación (`_resumen_general.py`)

- Carga cacheada de los dos mapas nuevos, mismo patrón que `load_base_data()`:

```python
@st.cache_data(show_spinner="Cargando factor de principio activo...")
def load_factor_principio_activo():
    return fetch_producto_id_map(), fetch_relacion_principio_activo()
```

- El toggle se ubica **después de los filtros y antes de la sección "Resumen"** (no dentro de la grilla, como se planteó al principio) — necesario porque el KPI strip se renderiza antes que la grilla en el script, y el mismo toggle tiene que gobernar ambos:

```python
ver_factor_pa = st.toggle("Ver Relación Principio Activo", value=False)
```

- Justo después de calcular `filtered` (con `add_proyeccion` ya aplicado) y `df_monthly`:

```python
id_map, factor_map = load_factor_principio_activo()
filtered = add_factor_principio_activo(filtered, id_map, factor_map)
df_monthly = add_factor_principio_activo(df_monthly, id_map, factor_map)

if ver_factor_pa:
    filtered = apply_factor_principio_activo(
        filtered, ["stock_qty", "planificado_qty", "ejecutado_qty", "pendiente_qty"]
    )
    filtered = add_proyeccion(filtered)  # recalcula proyeccion con las cantidades ya ajustadas
    df_monthly = apply_factor_principio_activo(df_monthly, ["planificado_mes", "ejecutado_mes"])
```

- `build_proyeccion_temporal` no cambia — recibe `df_monthly` ya ajustado (o crudo, si el toggle está apagado) y sigue agrupando por Empresa+Mes exactamente igual que hoy.
- KPI strip y grilla leen de `filtered` sin cambios adicionales — ya vienen recalculados si el toggle está activo.

## Fuera de alcance

- No se muestra el factor (`factor_pa`) como columna nueva en la grilla.
- No se persiste el estado del toggle entre sesiones (vive en la sesión actual, como el resto de los controles).
- No se valida ni corrige el dato de origen en Finnegans (la carga de `relacionprincipioactivo` por producto es responsabilidad de Ezequiel/AED en el ERP) — el dashboard solo lee y aplica el default 1 cuando falta.

## Testing

- `tests/test_transform.py`: casos nuevos para `add_factor_principio_activo` (valor real pasa igual, `"NULL"` string → 1, `0` → 1, producto sin match en `id_map` → 1) y para `apply_factor_principio_activo` (multiplica solo las columnas indicadas, dejando el resto intacto).
- `tests/test_db.py` / `tests/test_services.py`: tests de fallback a DataFrame vacío en error de conexión para las dos funciones nuevas de fetch, mismo patrón que las existentes.

## Validación

Se implementa y corre localmente (`streamlit run _resumen_general.py` con datos reales de Finnegans) verificando ambos estados del toggle antes de subir a producción — mismo flujo que los cambios anteriores (spec → plan → implementación → validación local → commit → push a `main` → verificación en Streamlit Cloud).

# Columnas Proyección Nueva y Dif. Ejec/Planif

**Fecha:** 2026-07-21

## Contexto

La grilla "Análisis Cruzado" y el KPI strip ya tienen una columna "Proyección" (`stock_qty + pendiente_qty - (planificado_qty - ejecutado_qty)`), que cuando `ejecutado_qty > planificado_qty` "premia" el excedente de ejecución sumándolo a la proyección. Se pide una versión más conservadora que ignore ese excedente, más una columna nueva que sí lo muestre por separado.

## Alcance

- Dos columnas nuevas, calculadas fila a fila (por PRODUCTO + EMPRESA), en la grilla "Análisis Cruzado":
  - **Dif. Ejec/Planif**: excedente de ejecución sobre lo planificado, nunca negativo.
  - **Proyección Nueva**: versión de "Proyección" que no suma ese excedente.
- Se agregan también como tarjetas nuevas en una tercera fila del KPI strip "Resumen".
- Se reordena la grilla y se quita la columna "Formulación" (sigue existiendo en los datos internos, solo deja de mostrarse).
- Se renombra el header "Pendiente Recepción" → "Pend. Recepción" (grilla y tarjeta KPI).
- Ambas columnas nuevas respetan el toggle "Ver Relación Principio Activo" igual que "Proyección" (se recalculan sobre las cantidades ya ajustadas por el factor cuando está activo).

## Diseño

### 1. Fórmulas y funciones nuevas (`data/transform.py`)

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

Mismo patrón que `add_proyeccion` (función pura, testeable de forma aislada). Las tres reglas de "Proyección Simple" que se plantearon originalmente (planificado > ejecutado / planificado < ejecutado / iguales o ambos cero) se resuelven todas con un único `.clip(lower=0)` sobre `planificado_qty - ejecutado_qty` — no queda ningún caso sin cubrir.

### 2. Dónde se calculan (`_resumen_general.py`)

Se llaman en los mismos 2 puntos donde hoy se llama `add_proyeccion`:

- `build_filtered` (línea ~183), justo después de `add_proyeccion(merged)`.
- Dentro de `_apply_factor_if_active`, en el bloque `if recompute_proyeccion:` (línea ~175-176), justo después de recalcular `add_proyeccion` — así el toggle de factor las recalcula igual que a "Proyección".

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

`build_filtered` queda igual, agregando las dos llamadas después de `add_proyeccion(merged)`.

### 3. Grilla "Análisis Cruzado" — orden y labels

`display_cols` pasa a:

```
EMPRESA, FAMILIA, SUBFAMILIA, PRINCIPIOACTIVO, PRODUCTO, CENTROLOGISTICO,
stock_qty, planificado_qty, ejecutado_qty, dif_ejec_planif, pendiente_qty, proyeccion, proyeccion_nueva
```

(se quita `FORMULACION` de la lista; el resto de columnas no cambia).

`col_labels` — cambios:
- `"pendiente_qty": "Pend. Recepción"` (antes "Pendiente Recepción")
- `"dif_ejec_planif": "Dif. Ejec/Planif"` (nueva)
- `"proyeccion_nueva": "Proyección Nueva"` (nueva)

`NUM_COLS` agrega `"Dif. Ejec/Planif"` y `"Proyección Nueva"`, y actualiza `"Pendiente Recepción"` → `"Pend. Recepción"`.

**Color de fondo:** `color_proyeccion` (verde si ≥ 0, rojo si negativo) se aplica a **ambas** columnas "Proyección" y "Proyección Nueva" (`subset=["Proyección", "Proyección Nueva"]`). "Dif. Ejec/Planif" queda como columna numérica simple, sin color (nunca es negativa por el `.clip(lower=0)`).

**Filtro "Solo déficit/superávit":** sin cambios — sigue filtrando solo por la columna `proyeccion` original, no por `proyeccion_nueva`.

**Excel:** las columnas nuevas se incluyen automáticamente en la descarga, al venir de `display_cols`.

### 4. KPI Strip "Resumen" — tercera fila

Filas 1 y 2 quedan **igual que hoy** en contenido y orden (Stock Actual, Planificado, Ejecutado / Dif. Planificado-Ejecutado, Pend. Recepción, Proyección Total) — se mantienen ambos indicadores de diferencia (el agregado existente y el nuevo), tal como se confirmó.

Fila 3 (nueva), en un grid de 3 columnas:

| Dif. Ejec/Planif | Proyección Nueva | *(vacío)* |
|---|---|---|

```python
dif_ejec_planif_total = filtered["dif_ejec_planif"].sum() if "dif_ejec_planif" in filtered.columns else 0.0
proyeccion_nueva_total = filtered["proyeccion_nueva"].sum() if "proyeccion_nueva" in filtered.columns else 0.0
```

- "Dif. Ejec/Planif" → tarjeta simple, sin color (mismo estilo que "Pend. Recepción").
- "Proyección Nueva" → mismo tratamiento visual que "Proyección Total" (badge y color verde/rojo según signo).
- La celda vacía de la fila 3 es un placeholder sin contenido, mismo fondo, sin borde derecho.
- Las tarjetas de la fila 2 pasan a tener `border_bottom=True` (ya no es la última fila); las de la fila 3 usan `border_bottom=False`.

## Fuera de alcance

- No se toca el filtro "Solo déficit/superávit" para que también considere "Proyección Nueva".
- No se persiste ningún estado nuevo entre sesiones.
- No se modifican las queries SQL ni los datos de origen.

## Testing

- `tests/test_transform.py`: casos nuevos para `add_dif_ejec_planif` (ejecutado > planificado, ejecutado < planificado, iguales, ambos cero) y `add_proyeccion_nueva` (mismos casos, más verificación de que no suma el excedente de ejecución a diferencia de `add_proyeccion`).
- Tests existentes que dependen de `display_cols` / cantidad de columnas visibles / conteo de tests totales (36/36) se actualizan para reflejar las columnas nuevas y la quita de Formulación.

## Validación

Se implementa y corre localmente (`streamlit run _resumen_general.py`) verificando: grilla con el nuevo orden de columnas y colores, KPI strip con la tercera fila, y ambos estados del toggle "Ver Relación Principio Activo" — antes de subir a producción.

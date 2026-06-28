# Design: Nuevos Indicadores en Resumen

**Fecha:** 2026-06-28  
**Archivo afectado:** `_resumen_general.py` (sección KPI strip, líneas ~212–267)

## Cambio

Reemplazar las cards "Productos — Superávit" y "Productos — Déficit" por dos nuevas.

## KPI Strip final (4 columnas)

| # | Label | Valor | Unidad | Color |
|---|-------|-------|--------|-------|
| 1 | Stock Actual | `filtered["stock_qty"].sum()` | kg | neutro |
| 2 | Pendiente Recepción | `filtered["pendiente_qty"].sum()` | Kg/Lit | neutro |
| 3 | Dif. Planificado / Ejecutado | `filtered["planificado_qty"].sum() - filtered["ejecutado_qty"].sum()` | Kg/Lit | neutro |
| 4 | Proyección Total | `filtered["proyeccion"].sum()` | Kg/Lit | verde si ≥ 0, rojo si < 0 |

## Variables a agregar/quitar en la sección KPI

**Quitar:**
- `proy_ok` (conteo de filas con proyeccion >= 0)
- `proy_def` (conteo de filas con proyeccion < 0)

**Agregar:**
- `dif_plan_ejec = filtered["planificado_qty"].sum() - filtered["ejecutado_qty"].sum()`
- `proy_total = filtered["proyeccion"].sum() if "proyeccion" in filtered.columns else 0`

## Card 4 — lógica de color

```python
proy_color = "#1a6b3a" if proy_total >= 0 else "#dc2626"
proy_bg    = "#dcfce7"  if proy_total >= 0 else "#fee2e2"
proy_label = "▲ Positiva" if proy_total >= 0 else "▼ Negativa"
```

## Scope

- Un solo archivo: `_resumen_general.py`
- No se tocan: `data/transform.py`, `pages/`, `api/`, `config.py`

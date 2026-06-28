# KPI Resumen — Nuevos Indicadores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar los indicadores "Productos — Superávit" y "Productos — Déficit" por "Dif. Planificado / Ejecutado" y "Proyección Total" en el KPI strip del resumen.

**Architecture:** Cambio localizado en `_resumen_general.py`. Se eliminan dos variables (`proy_ok`, `proy_def`) y se agregan dos nuevas (`dif_plan_ejec`, `proy_total`). El HTML del grid de 4 columnas se reescribe sólo en las posiciones 3 y 4.

**Tech Stack:** Streamlit, pandas, HTML inline vía `st.markdown(unsafe_allow_html=True)`

## Global Constraints

- No modificar `data/transform.py`, `api/`, `config.py`, ni ninguna página en `pages/`
- Mantener el grid de exactamente 4 columnas con el mismo estilo visual (fuentes Work Sans / Libre Baskerville, colores `#111`, `#9ca3af`)
- Unidades a mostrar en card 3 y 4: `Kg/Lit`

---

### Task 1: Reemplazar KPI cards en `_resumen_general.py`

**Files:**
- Modify: `_resumen_general.py:213–267`

**Interfaces:**
- Consumes: `filtered` DataFrame (ya calculado antes del KPI strip), con columnas `planificado_qty`, `ejecutado_qty`, `proyeccion`
- Produce: nada (renderizado directo por Streamlit)

- [ ] **Step 1: Reemplazar variables de KPI**

En `_resumen_general.py`, encontrá el bloque (líneas ~213–216):

```python
stock_total    = filtered["stock_qty"].sum()
pendiente_total = filtered["pendiente_qty"].sum()
proy_ok  = int((filtered["proyeccion"] >= 0).sum()) if "proyeccion" in filtered.columns else 0
proy_def = int((filtered["proyeccion"] < 0).sum())  if "proyeccion" in filtered.columns else 0
```

Reemplazarlo por:

```python
stock_total     = filtered["stock_qty"].sum()
pendiente_total = filtered["pendiente_qty"].sum()
dif_plan_ejec   = filtered["planificado_qty"].sum() - filtered["ejecutado_qty"].sum()
proy_total      = filtered["proyeccion"].sum() if "proyeccion" in filtered.columns else 0.0

proy_color = "#1a6b3a" if proy_total >= 0 else "#dc2626"
proy_bg    = "#dcfce7" if proy_total >= 0 else "#fee2e2"
proy_label = "▲ Positiva" if proy_total >= 0 else "▼ Negativa"
```

- [ ] **Step 2: Reemplazar las cards 3 y 4 en el HTML**

En `_resumen_general.py`, encontrá el bloque HTML de las cards 3 y 4 (líneas ~242–264):

```html
  <div style="padding:28px 28px 24px;border-right:1px solid #e5e7eb;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Productos — Superávit</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:#1a6b3a;line-height:1">{proy_ok}</div>
    <div style="display:inline-flex;align-items:center;gap:4px;margin-top:10px;
                font-size:11px;font-weight:700;padding:3px 10px;border-radius:3px;
                background:#dcfce7;color:#1a6b3a;font-family:'Work Sans',sans-serif">
      ▲ Proyección positiva
    </div>
  </div>

  <div style="padding:28px 28px 24px;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Productos — Déficit</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:#dc2626;line-height:1">{proy_def}</div>
    <div style="display:inline-flex;align-items:center;gap:4px;margin-top:10px;
                font-size:11px;font-weight:700;padding:3px 10px;border-radius:3px;
                background:#fee2e2;color:#b91c1c;font-family:'Work Sans',sans-serif">
      ▼ Proyección negativa
    </div>
  </div>
```

Reemplazarlo por:

```html
  <div style="padding:28px 28px 24px;border-right:1px solid #e5e7eb;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Dif. Planificado / Ejecutado</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:#111;line-height:1">{_fmt(dif_plan_ejec)}</div>
    <div style="font-size:13px;font-weight:600;color:#9ca3af;margin-top:6px;
                font-family:'Work Sans',sans-serif">Kg/Lit</div>
  </div>

  <div style="padding:28px 28px 24px;background:#fff">
    <div style="font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
                color:#9ca3af;margin-bottom:12px;font-family:'Work Sans',sans-serif">Proyección Total</div>
    <div style="font-family:'Libre Baskerville',serif;font-size:40px;font-weight:700;
                color:{proy_color};line-height:1">{_fmt(proy_total)}</div>
    <div style="display:inline-flex;align-items:center;gap:4px;margin-top:10px;
                font-size:11px;font-weight:700;padding:3px 10px;border-radius:3px;
                background:{proy_bg};color:{proy_color};font-family:'Work Sans',sans-serif">
      {proy_label}
    </div>
  </div>
```

- [ ] **Step 3: Verificar que el app arranca sin errores**

```bash
cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run _resumen_general.py
```

Esperado: arranca sin `NameError` ni `KeyError`. Verificar visualmente:
- Card 3 muestra "Dif. Planificado / Ejecutado" con un número formateado en negro
- Card 4 muestra "Proyección Total" en verde (si positiva) o rojo (si negativa) con badge ▲/▼

- [ ] **Step 4: Commitear**

```bash
cd ~/dashboard-insumos
git add _resumen_general.py
git commit -m "feat: reemplazar KPI superávit/déficit por dif plan/ejec y proyección total"
```

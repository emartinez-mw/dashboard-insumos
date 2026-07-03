# Autenticación Google restringida a dominio @admin.com.ar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restringir el acceso a la app de Streamlit únicamente a cuentas de Google del dominio `admin.com.ar`, con cierre de sesión automático tras 2hs de inactividad.

**Architecture:** Un módulo nuevo `access_control.py` con dos funciones puras testeables (`is_allowed_domain`, `is_session_expired`) y una función de orquestación (`require_login`) que usa el soporte nativo de auth de Streamlit (`st.login`/`st.user`/`st.logout`). `app.py`, único entrypoint de la app (usa `st.navigation`), llama a `require_login()` antes de armar la navegación — un solo punto de gateo cubre las 4 páginas.

**Tech Stack:** Streamlit 1.50.0 (ya instalado), `Authlib` (dependencia nueva, requerida por Streamlit para `st.login`), pytest (tests existentes del proyecto).

## Global Constraints

- Dominio autorizado: `admin.com.ar` — comparación exacta tras el `@`, no `endswith` (evita bypass tipo `evil-admin.com.ar`).
- Timeout de inactividad: 7200 segundos (2hs), implementado vía `st.session_state` (sliding, se resetea con cada interacción).
- Limitación aceptada: si la conexión WebSocket del navegador se corta y reconecta, se pierde el timer de inactividad (session_state se reinicia); la cookie de auth de Streamlit sigue válida hasta 30 días. Ver spec para detalle.
- No se piden ni pegan credenciales reales (Client ID/Secret de Google, cookie_secret real) en la conversación con Claude — esos valores los completa Ezequiel directamente en `.streamlit/secrets.toml` local (gitignored) y en el secrets manager de Streamlit Cloud.
- No se modifican: `_resumen_general.py`, `pages/`, `api/`, `data/transform.py`, `config.py`.
- Spec de referencia: `docs/superpowers/specs/2026-07-03-google-oauth-domain-auth-design.md`.

---

### Task 1: `is_allowed_domain` — función pura de validación de dominio

**Files:**
- Create: `access_control.py`
- Create: `tests/test_access_control.py`

**Interfaces:**
- Produces: `is_allowed_domain(email: str, allowed_domain: str = "admin.com.ar") -> bool`

- [ ] **Step 1: Write the failing tests**

Crear `tests/test_access_control.py`:

```python
from access_control import is_allowed_domain


def test_is_allowed_domain_matches_exact_domain():
    assert is_allowed_domain("user@admin.com.ar") is True


def test_is_allowed_domain_rejects_other_domain():
    assert is_allowed_domain("user@otrodominio.com") is False


def test_is_allowed_domain_rejects_lookalike_domain():
    assert is_allowed_domain("user@evil-admin.com.ar") is False


def test_is_allowed_domain_case_insensitive():
    assert is_allowed_domain("USER@ADMIN.COM.AR") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/dashboard-insumos && source .venv/bin/activate && pytest tests/test_access_control.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'access_control'`

- [ ] **Step 3: Write minimal implementation**

Crear `access_control.py`:

```python
ALLOWED_DOMAIN = "admin.com.ar"


def is_allowed_domain(email: str, allowed_domain: str = ALLOWED_DOMAIN) -> bool:
    """Compara el dominio exacto tras el @, no endswith (evita bypass tipo evil-admin.com.ar)."""
    return email.split("@")[-1].lower() == allowed_domain.lower()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_access_control.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add access_control.py tests/test_access_control.py
git commit -m "feat: agregar validación de dominio de email para auth"
```

---

### Task 2: `is_session_expired` — función pura de timeout por inactividad

**Files:**
- Modify: `access_control.py`
- Modify: `tests/test_access_control.py`

**Interfaces:**
- Consumes: nada de Task 1 (función independiente en el mismo módulo)
- Produces: `is_session_expired(last_activity: float, now: float, timeout_seconds: int = 7200) -> bool`

- [ ] **Step 1: Write the failing tests**

Agregar al final de `tests/test_access_control.py`:

```python
from access_control import is_session_expired


def test_is_session_expired_false_just_before_limit():
    assert is_session_expired(last_activity=0, now=7199, timeout_seconds=7200) is False


def test_is_session_expired_true_just_after_limit():
    assert is_session_expired(last_activity=0, now=7201, timeout_seconds=7200) is True


def test_is_session_expired_false_exactly_at_limit():
    assert is_session_expired(last_activity=0, now=7200, timeout_seconds=7200) is False
```

(El `from access_control import is_session_expired` va junto al import existente de `is_allowed_domain` al tope del archivo — dejar un solo bloque de imports.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_access_control.py -v`
Expected: FAIL con `ImportError: cannot import name 'is_session_expired'`

- [ ] **Step 3: Write minimal implementation**

Agregar a `access_control.py`, debajo de `is_allowed_domain`:

```python
INACTIVITY_TIMEOUT_SECONDS = 7200


def is_session_expired(last_activity: float, now: float, timeout_seconds: int = INACTIVITY_TIMEOUT_SECONDS) -> bool:
    return (now - last_activity) > timeout_seconds
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_access_control.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add access_control.py tests/test_access_control.py
git commit -m "feat: agregar chequeo de expiración de sesión por inactividad"
```

---

### Task 3: `require_login` — orquestación con Streamlit

**Files:**
- Modify: `access_control.py`

**Interfaces:**
- Consumes: `is_allowed_domain(email: str) -> bool` (Task 1), `is_session_expired(last_activity: float, now: float) -> bool` (Task 2)
- Produces: `require_login() -> None`

**Nota:** esta función no tiene test automatizado — usa `st.user`/`st.session_state`/`st.login`/`st.logout`, que requieren un runtime de Streamlit activo (no disponible en pytest plano). La lógica de decisión ya está cubierta por los tests de Task 1 y 2; `require_login` solo orquesta. La verificación de esta función es manual y se hace en Task 6.

- [ ] **Step 1: Agregar `require_login` a `access_control.py`**

Agregar al tope del archivo el import de `time` y `streamlit`, y al final la función:

```python
import time

import streamlit as st

ALLOWED_DOMAIN = "admin.com.ar"
INACTIVITY_TIMEOUT_SECONDS = 7200


def is_allowed_domain(email: str, allowed_domain: str = ALLOWED_DOMAIN) -> bool:
    """Compara el dominio exacto tras el @, no endswith (evita bypass tipo evil-admin.com.ar)."""
    return email.split("@")[-1].lower() == allowed_domain.lower()


def is_session_expired(last_activity: float, now: float, timeout_seconds: int = INACTIVITY_TIMEOUT_SECONDS) -> bool:
    return (now - last_activity) > timeout_seconds


def require_login() -> None:
    if not st.user.is_logged_in:
        st.header("Dashboard de Insumos — Duhau")
        st.subheader("Iniciá sesión con tu cuenta de Google")
        st.button("Iniciar sesión con Google", on_click=st.login)
        st.stop()

    if not is_allowed_domain(st.user.email):
        st.error("Tu cuenta no pertenece al dominio autorizado (@admin.com.ar).")
        st.button("Cerrar sesión", on_click=st.logout, key="logout_wrong_domain")
        st.stop()

    now = time.time()
    last_activity = st.session_state.get("last_activity")
    if last_activity is not None and is_session_expired(last_activity, now):
        st.warning("Sesión expirada por inactividad. Volvé a iniciar sesión.")
        st.logout()
        st.stop()

    st.session_state["last_activity"] = now

    with st.sidebar:
        st.caption(f"Sesión: {st.user.name}")
        st.button("Cerrar sesión", on_click=st.logout, key="logout_sidebar")
```

El archivo completo de `access_control.py` queda con: imports (`time`, `streamlit as st`), las dos constantes, las dos funciones puras (sin cambios de Tasks 1-2) y `require_login` al final.

- [ ] **Step 2: Correr la suite completa para confirmar que nada se rompió**

Run: `pytest -q`
Expected: 22 passed (15 tests previos + 7 nuevos de `test_access_control.py`)

(`import streamlit as st` a nivel de módulo no rompe los tests — no se ejecuta ningún `st.*` hasta que se llama a `require_login()`, que ningún test invoca.)

- [ ] **Step 3: Commit**

```bash
git add access_control.py
git commit -m "feat: agregar orquestación de login/logout con Google OAuth"
```

---

### Task 4: Gatear `app.py` con `require_login()`

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: `require_login() -> None` (Task 3)

- [ ] **Step 1: Modificar `app.py`**

Contenido completo del archivo:

```python
import streamlit as st

from access_control import require_login

require_login()

pg = st.navigation(
    [
        st.Page("_resumen_general.py",          title="Resumen General"),
        st.Page("pages/1_Stock.py",             title="Stock",             url_path="Stock"),
        st.Page("pages/2_Analisis_Lote.py",     title="Análisis de Lotes", url_path="Analisis_Lote"),
        st.Page("pages/3_Pendiente_Recibir.py", title="Pendiente Recibir", url_path="Pendiente"),
    ],
    position="hidden",
)
pg.run()
```

- [ ] **Step 2: Correr la suite completa**

Run: `pytest -q`
Expected: 22 passed (este cambio no agrega tests — `app.py` no tiene tests unitarios en el proyecto, se verifica manualmente en Task 6)

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: gatear acceso a la app con require_login"
```

---

### Task 5: Dependencia `Authlib` y template de secrets

**Files:**
- Modify: `requirements.txt`
- Modify: `.streamlit/secrets.toml.example`

**Interfaces:** ninguna (config estático, no código)

- [ ] **Step 1: Agregar `Authlib` a `requirements.txt`**

Contenido completo del archivo:

```
streamlit
pandas
requests
plotly
python-dotenv
pg8000
openpyxl
Authlib
```

- [ ] **Step 2: Instalar la dependencia localmente**

Run: `source .venv/bin/activate && pip install Authlib`
Expected: `Successfully installed authlib-...`

- [ ] **Step 3: Agregar sección `[auth]` a `.streamlit/secrets.toml.example`**

Contenido completo del archivo:

```toml
# Copiá este archivo como secrets.toml y completá los valores reales
# En Streamlit Cloud pegás este contenido en App Settings → Secrets

DB_HOST     = "duhau.dw.finneg.com"
DB_NAME     = "finnegansbi"
DB_USER     = "duhauuser"
DB_PASSWORD = "tu_password_aqui"
DB_PORT     = "5432"

CLIENT_ID     = "tu_client_id_aqui"
CLIENT_SECRET = "tu_client_secret_aqui"

# Auth Google (dominio admin.com.ar) — client_id/client_secret son los del
# OAuth Client de Google Cloud Console, DISTINTOS de CLIENT_ID/CLIENT_SECRET de arriba.
[auth]
# Local:           "http://localhost:8501/oauth2callback"
# Streamlit Cloud:  "https://emartinez-mw-dashboard-insumos.streamlit.app/oauth2callback"
redirect_uri        = "http://localhost:8501/oauth2callback"
cookie_secret       = "generar_con: python -c \"import secrets; print(secrets.token_hex(32))\""
client_id           = "tu_client_id_de_google_aqui"
client_secret       = "tu_client_secret_de_google_aqui"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

**Nota:** el patch existente en `_resumen_general.py` (`for _k, _v in st.secrets.items(): if isinstance(_v, str) ...`) no toca la sección `[auth]` porque su valor es una tabla TOML (no un string) — no hace falta tocar ese archivo.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .streamlit/secrets.toml.example
git commit -m "chore: agregar Authlib y template de secrets para auth Google"
```

---

### Task 6 (Manual — Ezequiel, no subagent): Configurar secrets reales y verificar end-to-end

Esta tarea no la ejecuta un subagent: requiere las credenciales reales de Google Cloud Console y una sesión de navegador real.

- [ ] **Paso 1 — Generar `cookie_secret`:**
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
  Guardá el valor generado (no lo compartas en el chat).

- [ ] **Paso 2 — Crear `.streamlit/secrets.toml` local** (copiá `.streamlit/secrets.toml.example`, ya gitignored) con:
  - `DB_*` y `CLIENT_ID`/`CLIENT_SECRET` reales que ya venías usando.
  - `[auth].client_id` / `[auth].client_secret` = los del OAuth Client de Google Cloud Console.
  - `[auth].cookie_secret` = el valor generado en el Paso 1.
  - `[auth].redirect_uri` = `"http://localhost:8501/oauth2callback"`.

- [ ] **Paso 3 — Probar localmente:**
  ```bash
  cd ~/dashboard-insumos && source .venv/bin/activate && streamlit run app.py
  ```
  Verificar:
  - Sin login: aparece la pantalla "Iniciá sesión con tu cuenta de Google".
  - Con una cuenta `@admin.com.ar`: entra normal, aparece "Sesión: <nombre>" y "Cerrar sesión" en el sidebar.
  - Con una cuenta de otro dominio (si tenés alguna a mano para probar): aparece el error de dominio no autorizado y el botón de cerrar sesión, no deja pasar a la app.
  - Botón "Cerrar sesión" del sidebar: vuelve a la pantalla de login.

- [ ] **Paso 4 — Verificar el timeout de inactividad (atajo, sin esperar 2hs real):**
  En `access_control.py`, cambiar temporalmente `INACTIVITY_TIMEOUT_SECONDS = 7200` a `INACTIVITY_TIMEOUT_SECONDS = 10`, correr la app, loguearte, esperar >10s sin interactuar, click en cualquier lado de la UI → debe forzar logout con el mensaje de sesión expirada. Revertir el valor a `7200` antes de commitear (no commitear el valor de prueba).

- [ ] **Paso 5 — Configurar secrets en Streamlit Cloud:**
  En el dashboard de la app (Settings → Secrets), pegar el mismo contenido que el `secrets.toml` local pero con:
  `[auth].redirect_uri = "https://emartinez-mw-dashboard-insumos.streamlit.app/oauth2callback"`

- [ ] **Paso 6 — Pushear y verificar en producción:**
  ```bash
  git push origin main
  ```
  Esperar el redeploy automático de Streamlit Cloud y repetir las verificaciones del Paso 3 contra la URL pública.

---

## Self-Review

**Spec coverage:** gate único en `app.py` (Task 4) ✓, `is_allowed_domain` con comparación exacta (Task 1) ✓, `require_login` con las 3 ramas: no-logueado / dominio inválido / OK (Task 3) ✓, timeout de inactividad vía `session_state` (Task 2 y 3) ✓, sidebar con nombre + logout (Task 3) ✓, `Authlib` + `[auth]` en secrets.toml.example (Task 5) ✓, tests de las funciones puras con los 7 casos del spec (Tasks 1-2) ✓, limitación de inactividad documentada (Global Constraints) ✓, no se pega ningún secreto real en la conversación (Task 6) ✓.

**Placeholders:** ninguno — todos los steps tienen código completo o comandos exactos. Los placeholders visibles (`tu_client_id_aqui`, etc.) son intencionales: están en el `.example` que el usuario completa manualmente.

**Consistencia de tipos:** `is_allowed_domain(email: str, allowed_domain: str = "admin.com.ar") -> bool` y `is_session_expired(last_activity: float, now: float, timeout_seconds: int = 7200) -> bool` se usan igual en tests, en `require_login` y en la spec. `require_login() -> None` sin argumentos, consistente entre Task 3 y Task 4.

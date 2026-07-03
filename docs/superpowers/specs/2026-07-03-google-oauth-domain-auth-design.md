# Design: Autenticación Google restringida a dominio @admin.com.ar

**Fecha:** 2026-07-03
**Archivos afectados:** `app.py`, `access_control.py` (nuevo), `requirements.txt`, `.streamlit/secrets.toml.example`, `tests/test_access_control.py` (nuevo)

## Objetivo

Restringir el acceso a la app únicamente a cuentas de Google del dominio `admin.com.ar`, usando el soporte nativo de autenticación de Streamlit (`st.login`/`st.user`/`st.logout`, disponible desde Streamlit 1.42+, confirmado instalado 1.50.0). Agregar cierre de sesión automático tras 2hs de inactividad.

## Por qué auth nativa de Streamlit (no librería externa, no OAuth manual)

Streamlit ya resuelve manejo de tokens OIDC, firma de cookies de identidad y refresh — construirlo a mano (OAuth manual) o sumar una librería de terceros (`streamlit-authenticator`, etc.) duplicaría algo que el framework ya provee. Requiere únicamente:
- Agregar `Authlib` a `requirements.txt` (dependencia explícita que pide Streamlit para que `st.login` funcione).
- Sección `[auth]` en `secrets.toml` (local y Streamlit Cloud) con `client_id`, `client_secret`, `redirect_uri`, `cookie_secret`, `server_metadata_url`.

**Limitación confirmada de la auth nativa:** la cookie de identidad de Streamlit expira a los 30 días fijos, no configurable, y no tiene mecanismo de inactividad. El timeout de 2hs por inactividad se construye aparte (ver abajo).

## Punto de gateo único

`app.py` es el único entrypoint (usa `st.navigation` con las 4 páginas registradas ahí — no son rutas independientes). El gate se llama una sola vez, antes de armar la navegación:

```python
from access_control import require_login

require_login()

pg = st.navigation([...])
pg.run()
```

## `access_control.py` (nuevo módulo)

### Funciones puras (testeables sin runtime de Streamlit)

```python
def is_allowed_domain(email: str, allowed_domain: str = "admin.com.ar") -> bool:
    """Compara el dominio exacto tras el @, no endswith (evita bypass tipo evil-admin.com.ar)."""
    return email.split("@")[-1].lower() == allowed_domain.lower()

def is_session_expired(last_activity: float, now: float, timeout_seconds: int = 7200) -> bool:
    return (now - last_activity) > timeout_seconds
```

### Orquestación (usa `st.*`, delgada — delega lógica a las funciones puras)

```python
import time
import streamlit as st

def require_login():
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

## Secrets

`.streamlit/secrets.toml.example` — agregar sección:

```toml
[auth]
redirect_uri         = "http://localhost:8501/oauth2callback"
cookie_secret         = "generar_con_python_-c_import_secrets;secrets.token_hex(32)"
client_id             = "tu_client_id_aqui"
client_secret         = "tu_client_secret_aqui"
server_metadata_url   = "https://accounts.google.com/.well-known/openid-configuration"
```

Los valores reales se completan directamente en:
- `.streamlit/secrets.toml` local (ya gitignored, no se commitea)
- Secrets manager de Streamlit Cloud (dashboard de la app), con `redirect_uri = "https://emartinez-mw-dashboard-insumos.streamlit.app/oauth2callback"`

No se piden ni pegan credenciales reales en la conversación con Claude.

## Tests — `tests/test_access_control.py`

Solo se testean las funciones puras (no requieren runtime de Streamlit):

- `is_allowed_domain`:
  - `"user@admin.com.ar"` → `True`
  - `"user@otrodominio.com"` → `False`
  - `"user@evil-admin.com.ar"` → `False` (no debe matchear por substring)
  - `"USER@ADMIN.COM.AR"` → `True` (case-insensitive)
- `is_session_expired`:
  - `now - last_activity` justo antes del límite (7199s) → `False`
  - justo después (7201s) → `True`
  - exactamente en el límite (7200s) → `False` (no estrictamente mayor)

## Limitación conocida (aceptada)

El timeout de inactividad usa `st.session_state`, atado a la conexión WebSocket del navegador. Si la conexión se corta y reconecta (notebook suspendida, red inestable, tab en background mucho tiempo), se pierde el timer — el usuario sigue con la cookie de auth válida (hasta 30 días) y el chequeo de inactividad no se dispara hasta la próxima sesión continua de 2hs+. Aceptable para este dashboard interno de uso acotado; no se implementa el mecanismo robusto basado en cookie de navegador (`streamlit-cookies-controller`) porque agrega una dependencia sin necesidad clara en este caso.

## Scope

- Archivos nuevos: `access_control.py`, `tests/test_access_control.py`
- Archivos modificados: `app.py` (agrega `require_login()` antes de `st.navigation`), `requirements.txt` (agrega `Authlib`), `.streamlit/secrets.toml.example` (agrega sección `[auth]`)
- No se tocan: `_resumen_general.py`, `pages/`, `api/`, `data/transform.py`, `config.py`

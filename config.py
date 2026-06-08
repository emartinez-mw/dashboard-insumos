import os
from dotenv import load_dotenv

load_dotenv()

# Auth
AUTH_URL = "https://api.teamplace.finneg.com/api/oauth/token"
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("CLIENT_ID y CLIENT_SECRET deben estar configurados en .env")

# Endpoints
STOCK_URL = "https://api.finneg.com/api/reports/StockEmpresaDepositoDuhau"
PRESUPUESTADO_URL = "https://api.finneg.com/api/reports/AnalisisInsumosPresupuestadoDuhau"
PENDIENTE_URL = "https://api.finneg.com/api/reports/OrdenesDeCompraPendientesDuhau"

# Parámetros fijos por servicio (sin ACCESS_TOKEN ni fechas dinámicas)
STOCK_FIXED_PARAMS = {
    "PARAMWEBREPORT_tipoStock": 0,
    "PARAMWEBREPORT_TipoPrecio": 0,
    "PARAMWEBREPORT_MonedaID": "PES",
    "PARAMWEB_Rubro": "INSAGR",
}

PRESUPUESTADO_FIXED_PARAMS = {
    "PARAMWEBREPORT_fechaDesde": "2025-01-01",
    "PARAMWEBREPORT_CampanaID": "26-27 Campaña",
    "PARAMWEBREPORT_VerMonedaEn": 0,
}

PENDIENTE_FIXED_PARAMS = {
    "PARAMWEBREPORT_FechaDesde": "2025-01-01",
    "PARAMWEB_PendienteRecepcion": 1,
    "PARAMWEB_Rubro": "INSAGR",
}

# Mapeo de columnas de la API → nombres internos
# Actualizado con columnas reales verificadas contra los 3 endpoints (2026-06-08)
#
# Notas:
#   - Stock (StockEmpresaDepositoDuhau): EMPRESA ✅, PRODUCTO ✅, CANTIDAD1 (kg), DEPOSITO, RUBRO
#   - Presupuestado: producto en LABORPRODUCTO (se normaliza a PRODUCTO antes del merge)
#                    cantidad en CANTIDAD ✅, tiene ANO-MES, EMPRESA, DEPOSITO, RUBRO
#   - Pendiente: PRODUCTO ✅, EMPRESA ✅, SUCURSAL, PENDIENTERECEPCION (qty real pendiente),
#                ANO-MES, RUBRO
#   - Los 3 endpoints devuelven una lista JSON directa (no {"data": [...]})
COLUMN_MAP = {
    # Campos de merge — presentes en los 3 tras normalización
    "producto":          "PRODUCTO",          # Stock y Pendiente; Presupuestado usa LABORPRODUCTO (normalizar)
    "empresa":           "EMPRESA",           # los 3 servicios
    "rubro":             "RUBRO",             # los 3 servicios
    # Cantidades
    "stock_qty":         "CANTIDAD1",         # Stock: CANTIDAD1 = kg (CANTIDAD2 = toneladas)
    "presupuestado_qty": "CANTIDAD",          # Presupuestado: campo CANTIDAD
    "pendiente_qty":     "PENDIENTERECEPCION",# Pendiente: cantidad aún no recibida en depósito
    # Contexto adicional
    "deposito":          "DEPOSITO",          # Stock y Presupuestado (Pendiente no lo tiene)
    "sucursal":          "SUCURSAL",          # Solo Pendiente
    "anio_mes":          "ANO-MES",           # Presupuestado y Pendiente (Stock no lo tiene)
    "subfamilia":        "SUBFAMILIA",
    "familia":           "FAMILIA",
    "marca":             "MARCA",
}

# Campos para el merge de los 3 servicios
# Presupuestado requiere normalizar LABORPRODUCTO → PRODUCTO antes del merge
MERGE_KEYS = ["PRODUCTO", "EMPRESA", "RUBRO"]

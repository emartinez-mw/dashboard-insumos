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
STOCK_URL = "https://api.finneg.com/api/reports/StockDepositoDuhau"
PRESUPUESTADO_URL = "https://api.finneg.com/api/reports/AnalisisInsumosPresupuestadoDuhau"
PENDIENTE_URL = "https://api.finneg.com/api/reports/OrdenesDeCompraPendientesDuhau"

# Parámetros fijos por servicio (sin ACCESS_TOKEN ni fechas dinámicas)
STOCK_FIXED_PARAMS = {
    "PARAMWEBREPORT_tipoStock": 0,
    "PARAMWEBREPORT_soloStockNoCero": "true",
    "PARAMWEBREPORT_TipoPrecio": 0,
    "PARAMWEBREPORT_AgruparPor": 0,
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
# Actualizado en Task 5 con nombres reales verificados contra la API (2026-06-08)
#
# Notas importantes:
#   - StockDeposito: no tiene columna EMPRESA ni SUCURSAL; usa DEPOSITO como ubicación.
#     El campo PRINCIPIOACTIVO no tiene espacio (diferente a Presupuestado).
#   - Presupuestado: el producto está en LABORPRODUCTO (no PRODUCTO).
#     PRINCIPIO ACTIVO tiene un espacio en el nombre. Tiene EMPRESA pero no SUCURSAL.
#   - Pendiente: tiene PRODUCTO, EMPRESA, SUCURSAL. PRINCIPIO ACTIVO no existe en este endpoint.
#   - Los 3 endpoints devuelven una lista JSON directa (no {"data": [...]}).
COLUMN_MAP = {
    "producto":              "PRODUCTO",           # Stock: PRODUCTO | Presupuestado: LABORPRODUCTO | Pendiente: PRODUCTO
    "empresa":               "EMPRESA",            # Stock: ausente (usa DEPOSITO) | Presupuestado: EMPRESA | Pendiente: EMPRESA
    "rubro":                 "RUBRO",              # los 3 servicios
    "principio_activo_stock":"PRINCIPIOACTIVO",    # StockDeposito (sin espacio)
    "principio_activo_pres": "PRINCIPIO ACTIVO",  # Presupuestado (con espacio)
    "sucursal":              "SUCURSAL",           # solo en Pendiente; Stock y Presupuestado no tienen
    "deposito":              "DEPOSITO",           # Stock y Presupuestado; equivale a ubicación
    "stock_qty":             "CANTIDAD1",          # StockDeposito usa CANTIDAD1 (CANTIDAD2 = toneladas)
    "presupuestado_qty":     "CANTIDAD",           # Presupuestado
    "pendiente_qty":         "CANTIDAD",           # Pendiente (PENDIENTERECEPCION = pendiente exacto)
    "pendiente_recepcion":   "PENDIENTERECEPCION", # Pendiente: cantidad aún no recibida
    "anio_mes":              "ANO-MES",            # Presupuestado y Pendiente tienen ANO-MES; Stock no
    "subfamilia":            "SUBFAMILIA",         # los 3 servicios
    "familia":               "FAMILIA",            # los 3 servicios
    "marca":                 "MARCA",              # los 3 servicios
}

# Campos comunes para el merge
# ADVERTENCIA: no hay un conjunto de claves que exista en los 3 endpoints con el mismo nombre.
# Stock no tiene EMPRESA/SUCURSAL; Presupuestado no tiene SUCURSAL; Pendiente no tiene PRINCIPIOACTIVO.
# El merge debe hacerse por pares (Stock+Presupuestado por PRODUCTO+RUBRO+DEPOSITO,
# Presupuestado+Pendiente por PRODUCTO+EMPRESA+RUBRO) o normalizando antes.
MERGE_KEYS = ["PRODUCTO", "RUBRO", "EMPRESA"]

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
# ACTUALIZAR en Task 5 con los nombres reales de la API
COLUMN_MAP = {
    "producto":         "producto",        # columna producto en los 3 servicios
    "empresa":          "empresa",         # columna empresa en los 3 servicios
    "rubro":            "rubro",           # columna rubro
    "principio_activo": "principio_activo",# columna principio activo
    "sucursal":         "sucursal",        # columna sucursal
    "stock_qty":        "cantidad",        # columna cantidad en StockDeposito
    "presupuestado_qty":"cantidad",        # columna cantidad en Presupuestado
    "pendiente_qty":    "cantidad",        # columna cantidad en Pendiente
    "anio_mes":         "anio_mes",        # columna año-mes (si existe en la API)
}

# Campos comunes para el merge
MERGE_KEYS = ["producto", "empresa", "rubro", "principio_activo", "sucursal"]

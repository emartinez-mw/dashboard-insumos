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
ANALISIS_LOTE_URL = "https://api.finneg.com/api/reports/AnalisisLoteDuhau"
PENDIENTE_URL = "https://api.finneg.com/api/reports/OrdenesDeCompraPendientesDuhau"

# Stock v2: no recibe parámetros (solo ACCESS_TOKEN)
STOCK_FIXED_PARAMS = {}

ANALISIS_LOTE_FIXED_PARAMS = {
    "CampanaID": "26-27 Campaña",
    "incluirlabores": 3,
    "Ejecutado": "true",
    "Planificado": "true",
    "VerMonedaEn": 0,
    "fechaDesde": "2026-01-01",
    "fechaHasta": "2030-12-31",
}

PENDIENTE_FIXED_PARAMS = {
    "PARAMWEBREPORT_FechaDesde": "2025-01-01",
    "PARAMWEB_PendienteRecepcion": 1,
    "PARAMWEB_Rubro": "INSAGR",
}

COLUMN_MAP = {
    "producto":         "PRODUCTO",
    "empresa":          "EMPRESA",
    "empresapadre":     "EMPRESAPADRE",
    "familia":          "FAMILIA",
    "subfamilia":       "SUBFAMILIA",
    "principioactivo":  "PRINCIPIOACTIVO",
    "formulacion":      "FORMULACION",
    "centrologistico":  "CENTROLOGISTICO",
    "stock_qty":        "CANTIDAD1",
    "pendiente_qty":    "PENDIENTERECEPCION",
}

# Menor denominador común entre los 3 servicios (Pendiente no tiene EMPRESAPADRE)
MERGE_KEYS = ["PRODUCTO", "EMPRESA"]

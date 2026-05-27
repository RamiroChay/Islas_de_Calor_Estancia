from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pymongo import MongoClient
from datetime import datetime
import os
import secrets

import threading
import time
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dags.weather_pipeline import run_pipeline
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

# ALLOWED_ORIGINS en .env como CSV: "https://islas.tudominio.com,https://www.islas.tudominio.com"
# Vacío o no definido = abierto (útil en desarrollo).
_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
_allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client[os.getenv("MONGO_DB")]

raw_collection = db["SensoresRaw"]
features_collection = db["mediciones_analitica"]
grid_collection = db["mapa_calor_actual"]
resumen_collection = db['resumen_ambiental']

# ---------------------------
# Autenticación HTTP Basic
#   Credenciales se leen de .env (API_USER y API_PASS).
#   Si no están definidas, la API arranca pero rechaza toda petición a /api/*.
# ---------------------------
_API_USER = os.getenv("API_USER", "").strip()
_API_PASS = os.getenv("API_PASS", "").strip()

_security = HTTPBasic(realm="Islas de Calor · API")


def require_auth(creds: HTTPBasicCredentials = Depends(_security)) -> str:
    if not _API_USER or not _API_PASS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_USER / API_PASS no configurados en el servidor.",
        )
    user_ok = secrets.compare_digest(creds.username, _API_USER)
    pass_ok = secrets.compare_digest(creds.password, _API_PASS)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": 'Basic realm="Islas de Calor · API"'},
        )
    return creds.username

# ---------------------------
# Background scheduler
# ---------------------------
def scheduler():
    while True:
        try:
            print("Ejecutando pipeline...")
            run_pipeline()
            print("Pipeline completado")
        except Exception as e:
            print(f"Error en pipeline: {e}")

        time.sleep(300)  # 5 minutos


# ---------------------------
# Startup event
# ---------------------------
@app.on_event("startup")
def start_scheduler():
    thread = threading.Thread(target=scheduler, daemon=True)
    thread.start()


# ---------------------------
# Healthcheck (Azure App Service lo usa para warm-up)
# ---------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ---------------------------
# POST sensores
# ---------------------------
@app.post("/api/sensores")
async def recibir_datos(data: dict, _user: str = Depends(require_auth)):

    documento = {
        "device_id": data.get("device_id"),
        "temperatura": data.get("temperatura"),
        "humedad": data.get("humedad"),
        "salinidad": data.get("salinidad"),
        "radiacion": data.get("radiacion"),
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "estado": data.get("estado"),
        "timestamp": datetime.utcnow()
    }

    raw_collection.insert_one(documento)

    return {"status": "ok"}


# ---------------------------
# GET sensores (features)
# ---------------------------
@app.get("/api/sensores")
def get_sensores(_user: str = Depends(require_auth)):
    return list(features_collection.find({}, {
        "_id": 0,
        "device_id": 1,
        "timestamp": 1,
        "lat": 1,
        "lon": 1,
        "temperatura": 1,
        "humedad": 1,
        "salinidad": 1,
        "radiacion": 1,
        "uhi": 1,
        "zona_termica": 1,
        "tipo_superficie": 1,
        "indice_vegetacion": 1,
        "indice_energia": 1,
        "deficit_humedad": 1
    }))

# ---------------------------
# GET grid (heatmap)
# ---------------------------
@app.get("/api/grid")
def get_grid(_user: str = Depends(require_auth)):
    return list(grid_collection.find({}, {
        "_id": 0,
        "lat": 1,
        "lon": 1,
        "uhi": 1
    }))

# ---------------------------
# GET resumen
# ---------------------------
@app.get("/api/resumen")
def get_resumen(_user: str = Depends(require_auth)):
    return db["resumen_ambiental"].find_one({}, {"_id": 0})


# ---------------------------
# Frontend estático (debe ir AL FINAL para que las rutas /api/* tengan prioridad)
# Sirve web/index.html en "/" y web/app.html en "/app.html".
# ---------------------------
_WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
if os.path.isdir(_WEB_DIR):
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
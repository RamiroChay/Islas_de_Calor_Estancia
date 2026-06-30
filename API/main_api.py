"""API REST de la plataforma de islas de calor (FastAPI).

Expone:
- Ingesta de lecturas de sensores (``POST /api/sensores``).
- Lectura pública del dashboard (``GET /api/sensores|grid|resumen``), protegida
  con Basic Auth de sólo lectura (``API_USER`` / ``API_PASS``).
- Zona admin (``/api/admin/*``: pipeline, explorador de BD, truncate),
  protegida con credenciales de administrador (``API_ADMIN_USER`` / ``API_ADMIN_PASS``).
- Sirve el frontend estático de ``web/`` (con cabeceras anti-caché).

Además, un scheduler en segundo plano ejecuta el pipeline ETL cada 5 minutos.
"""

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

# Credenciales de ADMINISTRADOR (zona admin: pipeline, explorador BD, truncate).
# Independientes de las públicas: protegen todos los endpoints /api/admin/*.
_API_ADMIN_USER = os.getenv("API_ADMIN_USER", "").strip()
_API_ADMIN_PASS = os.getenv("API_ADMIN_PASS", "").strip()

_security = HTTPBasic(realm="Islas de Calor · API")


def require_auth(creds: HTTPBasicCredentials = Depends(_security)) -> str:
    """Valida las credenciales PÚBLICAS (sólo lectura) del dashboard.

    Si ``API_USER`` / ``API_PASS`` no están configuradas, la API arranca pero
    rechaza toda petición protegida con 503.
    """
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


def require_admin(creds: HTTPBasicCredentials = Depends(_security)) -> str:
    """Valida credenciales de ADMINISTRADOR (API_ADMIN_USER / API_ADMIN_PASS).
    Protege todos los endpoints /api/admin/*. Las credenciales públicas
    (require_auth) NO dan acceso aquí."""
    if not _API_ADMIN_USER or not _API_ADMIN_PASS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_ADMIN_USER / API_ADMIN_PASS no configurados en el servidor.",
        )
    user_ok = secrets.compare_digest(creds.username, _API_ADMIN_USER)
    pass_ok = secrets.compare_digest(creds.password, _API_ADMIN_PASS)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de administrador inválidas.",
            headers={"WWW-Authenticate": 'Basic realm="Islas de Calor · Admin"'},
        )
    return creds.username

# ---------------------------
# Background scheduler
# ---------------------------
def scheduler():
    """Bucle en segundo plano: corre el pipeline ETL cada 5 minutos.

    Captura las excepciones para que un fallo de una corrida no tumbe el hilo
    (que es daemon) ni la API.
    """
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
# GET /api/admin/me
# Verifica credenciales de administrador. El frontend lo usa como "login":
# 200 => credenciales válidas (es admin); 401 => inválidas.
# ---------------------------
@app.get("/api/admin/me")
def admin_me(user: str = Depends(require_admin)):
    return {"user": user, "role": "admin"}


# ---------------------------
# POST /api/admin/run-pipeline
# Dispara el pipeline ETL on-demand (síncrono). Requiere admin.
# Devuelve los conteos resultantes de cada colección.
# ---------------------------
@app.post("/api/admin/run-pipeline")
def run_pipeline_now(_user: str = Depends(require_admin)):
    try:
        run_pipeline(full=True)   # botón manual = rebuild completo (todo SensoresRaw)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al ejecutar el pipeline: {e}",
        )

    counts = {}
    for name in ["SensoresRaw", "mediciones_analitica", "mapa_calor_actual", "resumen_ambiental"]:
        try:
            counts[name] = db[name].estimated_document_count()
        except Exception:
            counts[name] = None

    return {
        "status": "ok",
        "counts": counts,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


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
# GET /api/admin/db/collections
# Lista las colecciones de la base con conteo aproximado.
# ---------------------------
@app.get("/api/admin/db/collections")
def list_collections(_user: str = Depends(require_admin)):
    out = []
    for name in db.list_collection_names():
        try:
            count = db[name].estimated_document_count()
        except Exception:
            count = None
        out.append({"name": name, "count": count})
    out.sort(key=lambda x: x["name"])
    return out


# ---------------------------
# GET /api/admin/db/{collection}?limit=50&skip=0
# Devuelve documentos de una colección (paginado).
# ---------------------------
def _serialize_doc(doc):
    """Convierte tipos BSON no-JSON (ObjectId, datetime) a strings."""
    out = {}
    for k, v in doc.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat() + ("Z" if not v.tzinfo else "")
        elif isinstance(v, dict):
            out[k] = _serialize_doc(v)
        elif isinstance(v, list):
            out[k] = [_serialize_doc(x) if isinstance(x, dict) else (str(x) if not isinstance(x, (str, int, float, bool, type(None))) else x) for x in v]
        elif isinstance(v, (str, int, float, bool, type(None))):
            out[k] = v
        else:
            out[k] = str(v)  # ObjectId, etc.
    return out


@app.get("/api/admin/db/{collection}")
def get_collection_docs(
    collection: str,
    limit: int = 50,
    skip: int = 0,
    _user: str = Depends(require_admin),
):
    if collection not in db.list_collection_names():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Colección '{collection}' no existe.",
        )

    limit = max(1, min(int(limit), 500))
    skip = max(0, int(skip))

    total = db[collection].estimated_document_count()
    cursor = db[collection].find({}).skip(skip).limit(limit)
    docs = [_serialize_doc(d) for d in cursor]

    return {
        "collection": collection,
        "total": total,
        "skip": skip,
        "limit": limit,
        "returned": len(docs),
        "docs": docs,
    }


# ---------------------------
# POST /api/admin/db/{collection}/truncate
# Borra los documentos de UNA sola colección. Requiere auth +
# payload {"confirm": "<nombre_exacto_de_la_coleccion>"}.
# ---------------------------
@app.post("/api/admin/db/{collection}/truncate")
def truncate_collection(collection: str, body: dict, _user: str = Depends(require_admin)):
    if collection not in db.list_collection_names():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Colección '{collection}' no existe.",
        )

    if (body or {}).get("confirm") != collection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Debes enviar {{"confirm": "{collection}"}} (el nombre exacto) para vaciar la tabla.',
        )

    res = db[collection].delete_many({})
    return {
        "status": "ok",
        "collection": collection,
        "deleted": res.deleted_count,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------
# POST /api/admin/truncate
# Borra TODAS las colecciones. Requiere auth + payload con la frase exacta.
# Devuelve los conteos de documentos eliminados por colección.
# ---------------------------
_TRUNCATABLE_COLLECTIONS = [
    "SensoresRaw",
    "mediciones_analitica",
    "mapa_calor_actual",
    "resumen_ambiental",
]
_CONFIRM_PHRASE = "BORRAR TODO"


@app.post("/api/admin/truncate")
def truncate_all(body: dict, _user: str = Depends(require_admin)):
    if (body or {}).get("confirm") != _CONFIRM_PHRASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Debes enviar {{"confirm": "{_CONFIRM_PHRASE}"}} para ejecutar.',
        )

    deleted = {}
    for name in _TRUNCATABLE_COLLECTIONS:
        res = db[name].delete_many({})
        deleted[name] = res.deleted_count

    return {
        "status": "ok",
        "deleted": deleted,
        "total": sum(deleted.values()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------
# Frontend estático (debe ir AL FINAL para que las rutas /api/* tengan prioridad)
# Sirve web/index.html en "/" y web/app.html en "/app.html".
#
# NoCacheStaticFiles: añade cabeceras anti-caché para que el navegador SIEMPRE
# pida la versión más reciente del HTML/CSS/JS. Evita el clásico "edité pero el
# navegador sigue mostrando lo viejo". (En producción podrías cachear los assets
# versionados, pero en este proyecto el frontend cambia seguido.)
# ---------------------------
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


_WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
if os.path.isdir(_WEB_DIR):
    app.mount("/", NoCacheStaticFiles(directory=_WEB_DIR, html=True), name="web")
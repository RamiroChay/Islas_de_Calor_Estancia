from fastapi import FastAPI
from pymongo import MongoClient
from datetime import datetime
import os
import threading
import time

from dags.weather_pipeline import run_pipeline
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
# ROOT
# ---------------------------
@app.get("/")
def root():
    return {"status": "API running"}


# ---------------------------
# POST sensores
# ---------------------------
@app.post("/api/sensores")
async def recibir_datos(data: dict):

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
def get_sensores():
    return list(features_collection.find({}, {
        "_id": 0,
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
def get_grid():
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
def get_resumen():
    return db["resumen_ambiental"].find_one({}, {"_id": 0})
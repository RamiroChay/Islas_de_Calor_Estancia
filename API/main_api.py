from fastapi import FastAPI
from pymongo import MongoClient
from datetime import datetime
import os
import threading
import time

from dags import run_pipeline

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["islas_calor"]

raw_collection = db["sensores_raw"]
features_collection = db["sensores_features"]
grid_collection = db["map_grid"]

# ---------------------------
# 🧠 Background scheduler
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
        "uhi": 1,
        "zona_termica": 1
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
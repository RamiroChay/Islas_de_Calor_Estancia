import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def get_db():
    client = MongoClient(os.getenv("MONGO_URI"))
    return client[os.getenv("MONGO_DB")]


# ---------------------------
# FEATURES
# ---------------------------
def load_features(df):
    if df.empty:
        return

    db = get_db()
    collection = db["mediciones_analitica"]

    # timestamp del pipeline
    timestamp = datetime.utcnow()

    data = df.to_dict(orient='records')

    for d in data:
        d["pipeline_timestamp"] = timestamp

    # eliminar datos antiguos (mantener solo último batch)
    collection.delete_many({"pipeline_timestamp": {"$ne": timestamp}})

    collection.insert_many(data)


# ---------------------------
# GRID (MAPA)
# ---------------------------
def load_grid(grid_data):
    if not grid_data:
        return

    db = get_db()
    collection = db["mapa_calor_actual"]

    timestamp = datetime.utcnow()

    for d in grid_data:
        d["pipeline_timestamp"] = timestamp

    # mantener solo último mapa
    collection.delete_many({"pipeline_timestamp": {"$ne": timestamp}})

    collection.insert_many(grid_data)

def load_resumen(resumen):
    if not resumen:
        return

    db = get_db()
    collection = db["resumen_ambiental"]

    # mantener solo el último
    collection.delete_many({})

    collection.insert_one(resumen)
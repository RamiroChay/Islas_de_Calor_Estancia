import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def get_raw_data():

    client = MongoClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGO_DB")]
    collection = db["SensoresRaw"]

    # ---------------------------
    # Últimos 5 minutos
    # ---------------------------
    limite = datetime.utcnow() - timedelta(minutes=5)

    data = list(collection.find({
        "timestamp": {"$gte": limite}
    }))

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # eliminar _id de Mongo
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])

    return df
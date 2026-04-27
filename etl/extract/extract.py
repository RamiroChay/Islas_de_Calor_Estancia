import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def get_raw_data():
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGO_DB")]
    collection = db["sensores_raw"]
    
    # Traemos todo lo que han mandado los sensores
    data = list(collection.find())
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    # MongoDB devuelve un campo _id que no necesitamos para el análisis
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df
from fastapi import APIRouter
from database import engine
import pandas as pd

router = APIRouter()

@router.get("/features")
def get_features():
    query = "SELECT * FROM climate_features ORDER BY month"
    df = pd.read_sql(query, engine)
    return df.to_dict(orient="records")
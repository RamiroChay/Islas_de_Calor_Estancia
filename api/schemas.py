# models.py

from pydantic import BaseModel

class Feature(BaseModel):
    month: str
    temp_mean: float
    temp_max: float
    temp_min: float
    temp_std: float
    hotspot_ratio: float
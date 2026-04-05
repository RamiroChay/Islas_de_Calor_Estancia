import pandas as pd
from sqlalchemy import create_engine

# 🔌 conexión
engine = create_engine("postgresql://postgres:TU_PASSWORD@localhost:5432/heatmap_db")

# 📥 leer CSV
df = pd.read_csv("data/final/features.csv")

# 🔥 convertir fecha
df["month"] = pd.to_datetime(df["month"])

# 🚀 subir datos
df.to_sql(
    "climate_features",
    engine,
    if_exists="append",  # IMPORTANTE
    index=False
)

print("✅ Datos insertados en PostgreSQL")
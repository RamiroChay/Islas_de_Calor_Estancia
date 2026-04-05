from sqlalchemy import create_engine

DATABASE_URL = "postgresql://postgres:TU_PASSWORD@localhost:5432/heatmap_db"

engine = create_engine(DATABASE_URL)
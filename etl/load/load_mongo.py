"""Etapa LOAD del pipeline.

Persiste los resultados en MongoDB (Cosmos DB). Cada colección guarda sólo el
ÚLTIMO batch: antes de insertar se borran los documentos previos, de modo que
``mediciones_analitica``, ``mapa_calor_actual`` y ``resumen_ambiental`` siempre
reflejan la corrida más reciente.
"""

from datetime import datetime

import pandas as pd

from etl.db import get_db


def load_features(df: pd.DataFrame) -> None:
    """Guarda las features por sensor en ``mediciones_analitica``.

    Reemplaza el batch anterior (borra todo lo que no tenga el timestamp nuevo).
    """
    if df.empty:
        return

    collection = get_db()["mediciones_analitica"]
    timestamp = datetime.utcnow()  # marca de la corrida del pipeline

    data = df.to_dict(orient="records")
    for d in data:
        d["pipeline_timestamp"] = timestamp

    # Mantener sólo el último batch
    collection.delete_many({"pipeline_timestamp": {"$ne": timestamp}})
    collection.insert_many(data)


def load_grid(grid_data: list) -> None:
    """Guarda la malla interpolada (mapa de calor) en ``mapa_calor_actual``.

    Reemplaza el mapa anterior (borra todo lo que no tenga el timestamp nuevo).
    """
    if not grid_data:
        return

    collection = get_db()["mapa_calor_actual"]
    timestamp = datetime.utcnow()

    for d in grid_data:
        d["pipeline_timestamp"] = timestamp

    # Mantener sólo el último mapa
    collection.delete_many({"pipeline_timestamp": {"$ne": timestamp}})
    collection.insert_many(grid_data)


def load_resumen(resumen: dict) -> None:
    """Guarda el resumen ambiental global (un solo documento) en
    ``resumen_ambiental``, reemplazando el anterior."""
    if not resumen:
        return

    collection = get_db()["resumen_ambiental"]

    # Mantener sólo el último
    collection.delete_many({})
    collection.insert_one(resumen)

"""Resumen ambiental global de la corrida del pipeline.

Calcula los KPIs que consume el dashboard (temperatura promedio/máx/mín, UHI
promedio/máx, zona térmica dominante, número de sensores).
"""

from datetime import datetime

import pandas as pd


def calcular_resumen(df: pd.DataFrame, features_df: pd.DataFrame) -> dict:
    """Construye el documento de resumen global.

    Args:
        df: Lecturas crudas (una fila por medición). Aporta las temperaturas y
            humedades sobre TODAS las lecturas.
        features_df: Features por sensor (una fila por sensor). Aporta el UHI y
            la zona térmica.

    Returns:
        Diccionario con los KPIs y el ``pipeline_timestamp``.
    """
    return {
        "temp_promedio": float(df["temperatura"].mean()),
        "temp_max": float(df["temperatura"].max()),
        "temp_min": float(df["temperatura"].min()),

        "humedad_promedio": float(df["humedad"].mean()),

        "uhi_promedio": float(features_df["uhi"].mean()),
        "uhi_max": float(features_df["uhi"].max()),

        "zona_dominante": features_df["zona_termica"].mode()[0],

        "num_sensores": int(len(features_df)),

        "pipeline_timestamp": datetime.utcnow(),
    }

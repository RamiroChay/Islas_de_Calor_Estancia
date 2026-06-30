"""Etapa EXTRACT del pipeline.

Lee las lecturas crudas de los sensores desde la colección ``SensoresRaw`` y
las devuelve como ``DataFrame`` de pandas.
"""

from datetime import datetime, timedelta

import pandas as pd

from etl.db import get_db


def get_raw_data(full: bool = False) -> pd.DataFrame:
    """Obtiene las lecturas crudas de ``SensoresRaw``.

    Args:
        full: Si es ``True`` procesa TODAS las lecturas (rebuild completo).
            Si es ``False`` (tiempo real) sólo trae las de los últimos 5 minutos.

    Returns:
        ``DataFrame`` con las lecturas (sin la columna ``_id`` de Mongo).
        ``DataFrame`` vacío si no hay datos.
    """
    collection = get_db()["SensoresRaw"]

    if full:
        # Rebuild completo: procesa TODAS las lecturas (sin filtro de tiempo)
        data = list(collection.find({}))
    else:
        # Tiempo real: sólo los últimos 5 minutos
        limite = datetime.utcnow() - timedelta(minutes=5)
        data = list(collection.find({"timestamp": {"$gte": limite}}))

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # eliminar _id de Mongo (no aporta al análisis)
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])

    return df

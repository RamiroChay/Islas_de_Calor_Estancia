"""Acceso compartido a MongoDB (Cosmos DB) para el ETL.

Centraliza la conexión en un único ``MongoClient`` cacheado. Antes, cada
etapa (``extract``, ``load``) abría su propia conexión en cada llamada, lo que
creaba varios pools por corrida del pipeline. Aquí se reutiliza uno solo.

Variables de entorno (de ``.env``):
    MONGO_URI  cadena de conexión.
    MONGO_DB   nombre de la base de datos.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """Devuelve un ``MongoClient`` único (cacheado) creado desde ``MONGO_URI``.

    El cliente mantiene su propio pool de conexiones; reutilizarlo evita abrir
    una conexión nueva en cada operación del pipeline.
    """
    return MongoClient(os.getenv("MONGO_URI"))


def get_db() -> Database:
    """Devuelve la base de datos indicada por ``MONGO_DB``."""
    return get_client()[os.getenv("MONGO_DB")]

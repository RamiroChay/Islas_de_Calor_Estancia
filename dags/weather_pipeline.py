"""Orquestador del pipeline ETL de islas de calor.

Encadena las etapas: EXTRACT (lecturas crudas) -> TRANSFORM (features por
sensor + resumen) -> interpolación IDW del mapa de calor -> LOAD (persistir en
Mongo). Lo invocan el scheduler de la API (cada 5 min), el botón de admin
(rebuild completo) y el bloque ``__main__`` para correrlo a mano.
"""

from etl.extract.extract import get_raw_data
from etl.transform.features import transform_data
from etl.transform.grid import idw_interpolation
from etl.transform.resumen import calcular_resumen
from etl.load.load_mongo import load_features, load_grid, load_resumen

# Mínimo de sensores para que la interpolación espacial tenga sentido.
MIN_SENSORES_GRID = 3


def run_pipeline(full: bool = False) -> None:
    """Ejecuta el pipeline completo.

    Args:
        full: ``True`` reprocesa TODAS las lecturas (rebuild completo);
            ``False`` sólo la ventana de los últimos 5 minutos.

    Las excepciones se propagan a quien llama (el scheduler y el endpoint de
    admin las manejan) para que un fallo no quede oculto.
    """
    print(f"Iniciando pipeline... ({'rebuild completo' if full else 'ventana 5 min'})")

    # 1. EXTRACT
    df = get_raw_data(full=full)
    if df.empty:
        print("No hay datos en sensores_raw")
        return
    print(f"Datos extraídos: {len(df)} registros")

    # 2. TRANSFORM · features por sensor
    features_df = transform_data(df)
    if features_df.empty:
        print("Transformación vacía")
        return
    print("Transformación completada")

    # 3. LOAD features
    load_features(features_df)
    print("Features guardadas")

    # 4. Con muy pocos sensores la interpolación no aporta: terminamos aquí.
    if len(features_df) < MIN_SENSORES_GRID:
        print("Muy pocos puntos para interpolación")
        return

    # 5. GRID · interpolación IDW del mapa de calor
    grid_data = idw_interpolation(features_df, variable="uhi")
    if not grid_data:
        print("Grid vacío")
        return
    print(f"Grid generado: {len(grid_data)} puntos")

    # 6. Resumen global + LOAD
    resumen = calcular_resumen(df, features_df)
    load_resumen(resumen)
    print("Resumen global guardado")

    load_grid(grid_data)
    print("Grid guardado")

    print("Pipeline completado")


if __name__ == "__main__":
    run_pipeline()

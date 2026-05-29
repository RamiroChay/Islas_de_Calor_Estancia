from etl.extract.extract import get_raw_data
from etl.transform.features import transform_data
from etl.transform.grid import idw_interpolation
from etl.load.load_mongo import load_features, load_grid, load_resumen
from etl.transform.resumen import calcular_resumen

from dotenv import load_dotenv
import os

load_dotenv()

def run_pipeline(full=False):
    try:
        print(f"Iniciando pipeline... ({'rebuild completo' if full else 'ventana 5 min'})")

        # ---------------------------
        # 1. EXTRACT
        # ---------------------------
        df = get_raw_data(full=full)

        if df.empty:
            print("No hay datos en sensores_raw")
            return

        print(f"Datos extraídos: {len(df)} registros")

        # ---------------------------
        # 2. TRANSFORM
        # ---------------------------
        features_df = transform_data(df)

        if features_df.empty:
            print("Transformación vacía")
            return

        print("Transformación completada")

        # ---------------------------
        # 3. LOAD FEATURES
        # ---------------------------
        load_features(features_df)
        print("Features guardadas")

        # ---------------------------
        # 4. GRID (INTERPOLACIÓN)
        # ---------------------------
        if len(features_df) < 3:
            print("Muy pocos puntos para interpolación")
            return

        grid_data = idw_interpolation(features_df, variable='uhi')

        if not grid_data:
            print("Grid vacío")
            return

        print(f"Grid generado: {len(grid_data)} puntos")

        resumen = calcular_resumen(df, features_df)
        load_resumen(resumen)

        print("Resumen global guardado")

        # ---------------------------
        # 5. LOAD GRID
        # ---------------------------
        load_grid(grid_data)
        print("Grid guardado")

        print("Pipeline completado")

    except Exception as e:
        print(f"Error en pipeline: {e}")

if __name__ == "__main__":
    run_pipeline()
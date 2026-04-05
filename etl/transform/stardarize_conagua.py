import pandas as pd
import os
import rasterio
from pyproj import Transformer, CRS
from pathlib import Path

input_folder = "data/processed"
output_folder = "data/standardized"
raw_folder = Path("data/raw")
os.makedirs(output_folder, exist_ok=True)

# --- PASO 1: Obtener todos los archivos que contienen 'ndvi' y terminan en '.tif' ---
tif_files = list(raw_folder.glob("*ndvi*.tif"))
print(f"Archivos NDVI encontrados: {[f.name for f in tif_files]}")

# --- PASO 2: Procesar cada archivo CSV de estaciones ---
for file in os.listdir(input_folder):
    if file.endswith(".csv"):
        df = pd.read_csv(os.path.join(input_folder, file))
        
        # Limpieza básica
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["temp_max", "temp_min", "precipitation", "latitud", "longitud"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = df.dropna(subset=["latitud", "longitud", "date"])
        df = df[df["date"].dt.year >= 2020]
        if df.empty: continue

        # Extraer componentes de fecha
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        
        # Coordenadas de la estación (asumimos una sola ubicación por archivo CSV)
        lon_sample, lat_sample = df["longitud"].iloc[0], df["latitud"].iloc[0]
        ndvi_encontrado = False

        # --- PASO 3: Probar con cada TIF hasta encontrar uno donde caiga la estación ---
        for tif_path in tif_files:
            with rasterio.open(tif_path) as src:
                crs_raster = CRS.from_wkt(src.crs.to_wkt())
                transformer = Transformer.from_crs("EPSG:4326", crs_raster, always_xy=True)
                x, y = transformer.transform(lon_sample, lat_sample)
                bounds = src.bounds

                # ¿Está la estación dentro de este cuadro (Tile)?
                if (bounds.left <= x <= bounds.right) and (bounds.bottom <= y <= bounds.top):
                    valor_gen = src.sample([(x, y)])
                    ndvi_val = list(valor_gen)[0][0]
                    
                    if -1 <= ndvi_val <= 1:
                        df["ndvi"] = ndvi_val
                        ndvi_encontrado = True
                        break  # Ya encontramos el valor, salimos del bucle de TIFs
        
        if ndvi_encontrado:
            # 5. Cálculo final y orden
            df["temp_avg"] = df[["temp_max", "temp_min"]].mean(axis=1).round(2)
            
            cols_final = [
                "station", "date", "year", "month", "day", 
                "temp_max", "temp_min", "temp_avg", "precipitation",
                "latitud", "longitud", "ndvi"
            ]
            
            df = df[cols_final].sort_values("date")
            output_path = os.path.join(output_folder, file)
            df.to_csv(output_path, index=False)
            print(f"✅ {file} procesada correctamente con NDVI.")
        else:
            print(f"❌ {file} no coincide con NINGÚN archivo NDVI disponible.")
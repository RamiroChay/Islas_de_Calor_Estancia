import pandas as pd
import numpy as np
import os
from geopy.distance import geodesic

# 📥 INPUT: El archivo que contiene todas las estaciones ya con NDVI
input_path = "data/final/conagua_all.csv" 
output_path = "data/final/features_ml.csv"

# 📍 PUNTOS DE REFERENCIA (Mérida, Yucatán)
CENTRO_MERIDA = (20.967, -89.623)
PUERTO_PROGRESO = (21.285, -89.663) # Referencia para la costa

def calcular_distancia(row, punto_ref):
    return geodesic((row['latitud'], row['longitud']), punto_ref).km

def generar_features():
    if not os.path.exists(input_path):
        print(f"❌ No existe el archivo {input_path}. Corre merge.py primero.")
        return

    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['station', 'date'])

    print("🚀 Calculando features geográficas...")
    # 1. Distancias estáticas
    # Nota: Como la lat/lon de una estación no cambia, podrías optimizar esto 
    # calculándolo solo una vez por estación, pero para este volumen de datos está bien así:
    df['dist_centro'] = df.apply(lambda r: calcular_distancia(r, CENTRO_MERIDA), axis=1)
    df['dist_costa'] = df.apply(lambda r: calcular_distancia(r, PUERTO_PROGRESO), axis=1)

    print("📅 Calculando features temporales...")
    # 2. Variables Cíclicas (Mes)
    df['month_sin'] = np.sin(2 * np.pi * df['date'].dt.month / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['date'].dt.month / 12)

    # 3. Lags (Inercia térmica: ¿qué pasó ayer?)
    # Agrupamos por estación para que el "ayer" sea de la misma ubicación
    df['temp_avg_lag1'] = df.groupby('station')['temp_avg'].shift(1)
    df['precip_lag1'] = df.groupby('station')['precipitation'].shift(1)

    # 4. UHI Intensity (Anomalía de Isla de Calor)
    # Calculamos el promedio diario de todas las estaciones como "línea base"
    daily_avg = df.groupby('date')['temp_avg'].transform('mean')
    df['uhi_intensity'] = df['temp_avg'] - daily_avg

    # Limpieza final: quitar los primeros registros de cada estación que quedaron con NaN en el Lag
    df = df.dropna(subset=['temp_avg_lag1'])

    # 💾 Guardar
    df.to_csv(output_path, index=False)
    print(f"✅ Dataset de Features listo para ML: {output_path}")

if __name__ == "__main__":
    generar_features()
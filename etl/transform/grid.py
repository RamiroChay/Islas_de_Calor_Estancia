import pandas as pd
import numpy as np
import os
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from geopy.distance import geodesic

# 📥 CONFIGURACIÓN DE RUTAS
input_path = "data/final/conagua_all.csv"
output_folder = "data/final/heatmap"
os.makedirs(output_folder, exist_ok=True)

# 📍 REFERENCIA: Centro de Mérida
CENTRO_MERIDA = (20.967, -89.623)

# 📏 AJUSTES DE PRECISIÓN (Modifica esto para cerrar o abrir la mancha)
RADIO_INFLUENCIA = 0.08  # Controla qué tan lejos llega el calor de cada estación
RESOLUCION = 250j        # Calidad del grid (250x250 puntos)

# 🔥 CARGA Y LIMPIEZA
df = pd.read_csv(input_path)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["latitud", "longitud", "temp_avg", "date"])
df["month"] = df["date"].dt.to_period("M")

# Límites del área de Mérida (Bounding Box)
LAT_MIN, LAT_MAX = 20.82, 21.18
LON_MIN, LON_MAX = -89.78, -89.48

months = sorted(df["month"].unique())

for month in months:
    df_month = df[df["month"] == month].copy()
    
    # Promedio por estación
    df_stations = df_month.groupby(["latitud", "longitud", "station"])["temp_avg"].mean().reset_index()
    
    if len(df_stations) < 3:
        continue

    # --- CÁLCULO DE ISLA DE CALOR (UHI) ---
    df_stations['dist_centro'] = df_stations.apply(
        lambda r: geodesic((r['latitud'], r['longitud']), CENTRO_MERIDA).km, axis=1
    )
    # Referencia Rural: Estación más alejada
    temp_rural_base = df_stations.sort_values('dist_centro', ascending=False)['temp_avg'].iloc[0]
    df_stations['uhi_val'] = df_stations['temp_avg'] - temp_rural_base

    # 🕸️ GENERACIÓN DEL GRID
    grid_x, grid_y = np.mgrid[LON_MIN:LON_MAX:RESOLUCION, LAT_MIN:LAT_MAX:RESOLUCION]
    puntos_grid = np.c_[grid_x.ravel(), grid_y.ravel()]
    puntos_estaciones = np.c_[df_stations["longitud"], df_stations["latitud"]]

    # 🌡️ INTERPOLACIÓN
    # 1. Lineal (Suave)
    grid_uhi = griddata(puntos_estaciones, df_stations["uhi_val"].values, (grid_x, grid_y), method='linear')
    # 2. Nearest (Para rellenar huecos internos)
    grid_uhi_near = griddata(puntos_estaciones, df_stations["uhi_val"].values, (grid_x, grid_y), method='nearest')
    grid_uhi = np.where(np.isnan(grid_uhi), grid_uhi_near, grid_uhi)

    # 🛡️ MÁSCARA DE DISTANCIA (Elimina el cuadrado rojo infinito)
    # Calculamos qué tan lejos está cada punto del grid de la estación más cercana
    tree = cKDTree(puntos_estaciones)
    distancias, _ = tree.query(puntos_grid)
    distancias = distancias.reshape(grid_x.shape)

    # Función Gaussiana para desvanecer el calor:
    # 1.0 (en la estación) -> 0.0 (lejos de la estación)
    atenuacion = np.exp(-(distancias**2) / (2 * (RADIO_INFLUENCIA**2)))
    grid_uhi = grid_uhi * atenuacion

    # 📝 ESTRUCTURAR RESULTADOS
    df_grid = pd.DataFrame({
        "longitud": grid_x.ravel(),
        "latitud": grid_y.ravel(),
        "uhi_intensity": grid_uhi.ravel().round(2),
        "temp_est": (grid_uhi.ravel() + temp_rural_base).round(2),
        "is_station": 0
    })

    # Inyectar las estaciones reales (Puntos blancos)
    df_real = df_stations.copy()
    df_real['uhi_intensity'] = df_stations['uhi_val']
    df_real['temp_est'] = df_stations['temp_avg']
    df_real['is_station'] = 1

    # Unir todo
    df_final = pd.concat([df_grid, df_real[['latitud', 'longitud', 'uhi_intensity', 'temp_est', 'is_station', 'station']]], ignore_index=True)
    df_final["month"] = str(month)

    # 💾 GUARDAR
    output_path = os.path.join(output_folder, f"heatmap_{str(month)}.csv")
    df_final.to_csv(output_path, index=False)
    print(f"✅ Mapa optimizado para {month}. Base Rural: {temp_rural_base:.1f}°C")
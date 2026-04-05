import pandas as pd
# Carga tu archivo final
df = pd.read_csv("data/final/conagua_all.csv")
df['date'] = pd.to_datetime(df['date'])

# Mira un mes específico (ej. Junio 2024 que fue el más caliente)
mes_test = "2024-06"
df_test = df[df['date'].dt.to_period('M') == mes_test]

# Agrupa por estación para ver el promedio real de ese mes
estaciones_reales = df_test.groupby(['station', 'latitud', 'longitud'])['temp_avg'].mean().reset_index()

# Ordena de más caliente a más frío
print(f"--- Datos Reales de Estaciones ({mes_test}) ---")
print(estaciones_reales.sort_values('temp_avg', ascending=False))
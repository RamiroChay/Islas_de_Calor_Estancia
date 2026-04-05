import pandas as pd
import os

def union_total():
    folder = "data/standardized"
    output_path = "data/final/conagua_all.csv"
    os.makedirs("data/final", exist_ok=True)
    
    archivos = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".csv")]
    
    if not archivos:
        print("❌ No hay archivos en 'standardized'.")
        return

    # Unir todos los CSV
    df_total = pd.concat([pd.read_csv(f) for f in archivos], ignore_index=True)
    
    # Asegurar formato de fecha
    df_total['date'] = pd.to_datetime(df_total['date'])
    
    df_total.to_csv(output_path, index=False)
    print(f"✅ Master Dataset creado: {len(df_total)} filas en {output_path}")

if __name__ == "__main__":
    union_total()
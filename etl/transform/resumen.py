from datetime import datetime

def calcular_resumen(df, features_df):
    resumen = {
        "temp_promedio": float(df["temperatura"].mean()),
        "temp_max": float(df["temperatura"].max()),
        "temp_min": float(df["temperatura"].min()),

        "humedad_promedio": float(df["humedad"].mean()),

        "uhi_promedio": float(features_df["uhi"].mean()),
        "uhi_max": float(features_df["uhi"].max()),

        "zona_dominante": features_df["zona_termica"].mode()[0],

        "num_sensores": int(len(df)),

        "pipeline_timestamp": datetime.utcnow()
    }

    return resumen
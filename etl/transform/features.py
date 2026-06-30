"""Etapa TRANSFORM del pipeline · cálculo de features por sensor.

A partir de las lecturas crudas produce una fila por sensor con:
índice de isla de calor (UHI), normalizaciones, déficit de humedad, índices de
vegetación y energía, clasificación térmica y tipo de superficie.
"""

import pandas as pd
import numpy as np


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega las lecturas crudas a un punto por sensor y deriva sus features.

    Args:
        df: Lecturas crudas (una fila por medición).

    Returns:
        ``DataFrame`` con una fila por ``device_id`` y sus columnas derivadas
        (``uhi``, ``zona_termica``, índices, etc.). Vacío si la entrada lo está.
    """
    if df.empty:
        return df

    # ---------------------------
    # 1. Limpieza
    # ---------------------------
    df = df.dropna().copy()

    # ---------------------------
    # 2. Agrupación espacial · 1 sensor = 1 punto
    #
    # La posición se toma como la (lat, lon) MÁS FRECUENTE de cada device
    # (su posición dominante), NO el promedio: un device cuyo GPS salta entre
    # dos lugares crearía, al promediar, un "sensor fantasma" en medio de la
    # nada y el IDW pintaría un corredor de calor falso entre ambos puntos.
    # ---------------------------
    pos = (
        df.groupby(["device_id", "lat", "lon"]).size()
          .reset_index(name="_n")
          .sort_values("_n", ascending=False)
          .drop_duplicates("device_id")[["device_id", "lat", "lon"]]
    )

    # Métricas: promedio de TODAS las lecturas del device.
    metrics = df.groupby("device_id").agg({
        "temperatura": "mean",
        "humedad": "mean",
        "radiacion": "mean",
        "salinidad": "mean",
        "timestamp": "max",
    }).reset_index()

    df = metrics.merge(pos, on="device_id")

    # ---------------------------
    # 3. Variables base
    # ---------------------------
    T = df['temperatura']
    H = df['humedad']
    R = df['radiacion']

    # ---------------------------
    # 4. Referencias físicas
    # ---------------------------
    T_ref = T.min()        # zona más fría (proxy rural)
    H_ref = H.max()        # zona más húmeda (proxy vegetación)

    # ---------------------------
    # 5. UHI (Isla de calor) = T del sensor - T de la zona más fría
    # ---------------------------
    df['uhi'] = T - T_ref

    # ---------------------------
    # 6. Normalización (el +1e-6 evita división por cero si no hay rango)
    # ---------------------------
    df['temp_norm'] = (T - T.min()) / (T.max() - T.min() + 1e-6)
    df['humedad_norm'] = H / 100.0
    df['radiacion_norm'] = R / (R.max() + 1e-6)

    # ---------------------------
    # 7. Déficit de humedad
    # ---------------------------
    df['deficit_humedad'] = H_ref - H

    # ---------------------------
    # 8. Índice de vegetación (proxy físico)
    # ---------------------------
    df['indice_vegetacion'] = (
        -0.6 * df['temp_norm'] +
         0.4 * df['humedad_norm']
    )

    # ---------------------------
    # 9. Índice de energía (radiación dominante)
    # ---------------------------
    df['indice_energia'] = df['radiacion_norm'] * (1 - df['humedad_norm'])

    # ---------------------------
    # 10. Clasificación térmica por umbrales de UHI (°C)
    # ---------------------------
    def clasificar_uhi(uhi):
        if uhi < 2:
            return "baja"
        elif uhi < 4:
            return "media"
        else:
            return "alta"

    df['zona_termica'] = df['uhi'].apply(clasificar_uhi)

    # ---------------------------
    # 11. Tipo de superficie (proxy por salinidad)
    # ---------------------------
    mediana_salinidad = df['salinidad'].median()
    df['tipo_superficie'] = df['salinidad'].apply(
        lambda x: 'urbano' if x > mediana_salinidad else 'natural'
    )

    print(f"Sensores únicos: {len(df)}")

    return df
import pandas as pd
import numpy as np

def transform_data(df):
    if df.empty:
        return df

    # ---------------------------
    # 1. Limpieza
    # ---------------------------
    df = df.dropna()
    df = df.copy()

    # ---------------------------
    # 2. Variables base
    # ---------------------------
    T = df['temperatura']
    H = df['humedad']
    R = df['radiacion']
    S = df['salinidad']

    # ---------------------------
    # 3. Referencias físicas
    # ---------------------------
    T_ref = T.min()        # zona más fría (proxy rural)
    H_ref = H.max()        # zona más húmeda (proxy vegetación)

    # ---------------------------
    # 4. UHI (Isla de calor)
    # ---------------------------
    df['uhi'] = T - T_ref

    # ---------------------------
    # 5. Normalización
    # ---------------------------
    df['temp_norm'] = (T - T.min()) / (T.max() - T.min() + 1e-6)
    df['humedad_norm'] = H / 100.0
    df['radiacion_norm'] = R / (R.max() + 1e-6)

    # ---------------------------
    # 6. Déficit de humedad
    # ---------------------------
    df['deficit_humedad'] = H_ref - H

    # ---------------------------
    # 7. Índice de vegetación (proxy físico)
    # ---------------------------
    df['indice_vegetacion'] = (
        -0.6 * df['temp_norm'] +
         0.4 * df['humedad_norm']
    )

    # ---------------------------
    # 8. Índice de energía (radiación dominante)
    # ---------------------------
    df['indice_energia'] = df['radiacion_norm'] * (1 - df['humedad_norm'])

    # ---------------------------
    # 9. Clasificación térmica
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
    # 10. Tipo de superficie (proxy)
    # ---------------------------
    df['tipo_superficie'] = df['salinidad'].apply(
        lambda x: 'urbano' if x > df['salinidad'].median() else 'natural'
    )

    return df
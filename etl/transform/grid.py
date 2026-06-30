import numpy as np


def idw_interpolation(df, variable='uhi', grid_size=50, power=2,
                      cutoff_deg=0.02, pad_deg=0.01):
    """Interpolación IDW sobre una malla regular.

    Parámetros nuevos para evitar artefactos:
    - cutoff_deg: si una celda está más lejos que esto (en grados ~ 0.02° ≈
      2.2 km) del sensor MÁS CERCANO, no se pinta. Así no se inventa calor en
      zonas sin mediciones (los "corredores" entre sensores separados).
    - pad_deg: margen alrededor del bounding box para que la malla nunca sea de
      área cero cuando todos los sensores están en el mismo punto.
    """
    if df.empty:
        return []

    lats = df['lat'].values
    lons = df['lon'].values
    values = df[variable].values

    lat_grid = np.linspace(lats.min() - pad_deg, lats.max() + pad_deg, grid_size)
    lon_grid = np.linspace(lons.min() - pad_deg, lons.max() + pad_deg, grid_size)

    grid = []

    for lat in lat_grid:
        for lon in lon_grid:

            distances = np.sqrt((lats - lat) ** 2 + (lons - lon) ** 2)

            # Lejos de cualquier sensor real => sin dato (no inventamos calor)
            if distances.min() > cutoff_deg:
                continue

            # evitar división por cero
            distances[distances == 0] = 1e-10

            weights = 1 / (distances ** power)

            interpolated_value = np.sum(weights * values) / np.sum(weights)

            grid.append({
                "lat": float(lat),
                "lon": float(lon),
                variable: float(interpolated_value)
            })

    return grid

import numpy as np

def idw_interpolation(df, variable='uhi', grid_size=50, power=2):
    if df.empty:
        return []

    lats = df['lat'].values
    lons = df['lon'].values
    values = df[variable].values

    lat_grid = np.linspace(lats.min(), lats.max(), grid_size)
    lon_grid = np.linspace(lons.min(), lons.max(), grid_size)

    grid = []

    for lat in lat_grid:
        for lon in lon_grid:

            distances = np.sqrt((lats - lat)**2 + (lons - lon)**2)

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
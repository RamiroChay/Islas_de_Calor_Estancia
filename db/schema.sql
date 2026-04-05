-- Crear tabla de features
CREATE TABLE IF NOT EXISTS climate_features (
    id SERIAL PRIMARY KEY,
    month DATE UNIQUE,
    temp_mean FLOAT,
    temp_max FLOAT,
    temp_min FLOAT,
    temp_std FLOAT,
    hotspot_ratio FLOAT
);

-- Crear tabla de predicciones
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    month DATE,
    predicted_temp FLOAT,
    model_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
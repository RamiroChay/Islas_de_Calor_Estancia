# Arquitectura de Datos y Flujo ETL

## Flujo General

El sistema sigue una arquitectura ETL (Extract, Transform, Load) para procesar datos ambientales provenientes de sensores distribuidos geográficamente.

```text
Sensores
   │
   ▼
POST /api/sensores
   │
   ▼
SensoresRaw
   │
   ▼
ETL Scheduler (cada 5 minutos)
   │
   ├── Extract
   ├── Transform
   └── Load
   │
   ▼
mediciones_analitica
   │
   ├── resumen_ambiental
   └── mapa_calor_actual
   │
   ▼
Frontend / API GET
```

---

## Colección: SensoresRaw

Esta colección almacena los datos originales enviados por los sensores.

Cada documento representa una lectura individual.

Ejemplo:

```json
{
  "device_id": "sensor-01",
  "temperatura": 34.2,
  "humedad": 55.0,
  "salinidad": 0.45,
  "radiacion": 700,
  "lat": 20.97,
  "lon": -89.62,
  "timestamp": "2026-06-01T12:00:00Z"
}
```

Características:

* Conserva la información sin procesar.
* Puede contener múltiples lecturas del mismo sensor.
* Sirve como fuente principal para el proceso ETL.

---

## Colección: mediciones_analitica

Contiene los datos transformados y enriquecidos por el pipeline.

Durante la transformación se calculan variables adicionales:

* UHI (Urban Heat Island)
* Índice de vegetación
* Índice de energía
* Déficit de humedad
* Clasificación térmica
* Tipo de superficie

Ejemplo:

```json
{
  "device_id": "sensor-01",
  "temperatura": 34.2,
  "uhi": 4.5,
  "zona_termica": "alta",
  "indice_vegetacion": 0.32
}
```

Características:

* Contiene un registro por sensor.
* Las múltiples lecturas de un mismo sensor se agregan mediante promedio.
* Se utiliza para análisis y visualización.

---

## Colección: resumen_ambiental

Almacena indicadores globales del sistema.

Incluye:

* Temperatura promedio
* Temperatura máxima
* Temperatura mínima
* Humedad promedio
* UHI promedio
* UHI máximo
* Zona térmica dominante
* Número de sensores

Esta colección mantiene únicamente el resumen más reciente.

---

## Colección: mapa_calor_actual

Contiene los puntos generados mediante interpolación espacial IDW.

Cada documento representa un punto del mapa de calor.

Ejemplo:

```json
{
  "lat": 20.9721,
  "lon": -89.6214,
  "uhi": 3.8
}
```

Esta colección es utilizada directamente por el frontend para dibujar el heatmap.

---

# Generación del Mapa de Calor

El mapa de calor se construye utilizando el algoritmo IDW (Inverse Distance Weighting).

El proceso es:

1. Se obtienen todos los sensores procesados desde `mediciones_analitica`.
2. Se toman sus coordenadas geográficas.
3. Se genera una cuadrícula de 50 × 50 puntos.
4. Para cada punto de la cuadrícula se calcula un valor UHI interpolado.
5. Los valores cercanos tienen mayor influencia que los lejanos.

La fórmula utilizada es:

Valor interpolado = suma(peso × valor) / suma(pesos)

donde:

peso = 1 / distancia²

Con una cuadrícula de 50 × 50 se generan:

50 × 50 = 2,500 puntos

Por lo tanto:

* 3 sensores → 2,500 puntos interpolados.
* 10 sensores → 2,500 puntos interpolados.
* 100 sensores → 2,500 puntos interpolados.

La cantidad de puntos del mapa no depende del número de sensores sino del tamaño de la cuadrícula.

---

# Ejemplos de Procesamiento

## Caso 1: Un sensor envía 20 lecturas

SensoresRaw:

```text
sensor-01 → 20 documentos
```

Durante la transformación:

```text
GROUP BY device_id
```

Resultado:

```text
mediciones_analitica → 1 documento
```

porque todas las lecturas se agrupan y promedian.

---

## Caso 2: Cinco sensores envían 20 lecturas cada uno

SensoresRaw:

```text
5 sensores × 20 lecturas = 100 documentos
```

Después de la agrupación:

```text
mediciones_analitica = 5 documentos
```

Uno por sensor.

Posteriormente:

```text
mapa_calor_actual = 2,500 documentos
```

porque la cuadrícula permanece fija.
```

y un único documento en:

```text
resumen_ambiental
```

---

# Consideraciones

Actualmente el pipeline procesa únicamente los registros almacenados durante los últimos cinco minutos. Posteriormente agrupa las lecturas por sensor y genera una única representación analítica por dispositivo antes de construir el mapa de calor y los indicadores globales.

Hay un detalle importante: aunque entren 1000 lecturas, el mapa de calor siempre tendrá 2500 puntos, porque está definido por grid_size=50. Lo que cambia no es la cantidad de puntos del mapa, sino la precisión de la interpolación al haber más sensores distribuidos en el territorio.
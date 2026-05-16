# Islas de Calor · Mérida

Plataforma colaborativa de monitoreo urbano que mapea **islas de calor (UHI — Urban Heat Islands)** en la ciudad de Mérida, Yucatán, a partir de una red abierta de sensores ambientales de bajo costo.

El sistema captura temperatura, humedad, salinidad y radiación solar en distintos puntos de la ciudad, calcula índices térmicos en tiempo real y publica los resultados mediante una API REST y un visualizador web con mapa de calor interactivo.

---

## Tabla de contenidos

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Variables de entorno](#variables-de-entorno)
- [Ejecución local](#ejecución-local)
- [API REST](#api-rest)
- [Pipeline de datos](#pipeline-de-datos)
- [Índices y métricas calculadas](#índices-y-métricas-calculadas)
- [Frontend](#frontend)
- [Hoja de ruta](#hoja-de-ruta)
- [Créditos](#créditos)

---

## Características

- **Ingesta en tiempo real** de sensores IoT vía endpoint HTTP (`POST /api/sensores`).
- **Pipeline ETL automatizado** que se ejecuta cada 5 minutos en segundo plano.
- **Cálculo de UHI** (Urban Heat Island Intensity) y clasificación térmica por zonas.
- **Interpolación espacial IDW** (Inverse Distance Weighting) para generar mapas de calor continuos a partir de puntos discretos.
- **Índices derivados**: vegetación (proxy físico), energía radiante, déficit de humedad y tipo de superficie.
- **API REST pública** documentada para consumo por terceros (investigación, gobierno, ciudadanía).
- **Visualizador web** con landing informativa y dashboard con mapa Leaflet + heatmap.
- **Resumen ambiental global** actualizado en cada ciclo del pipeline.

---

## Arquitectura

```
┌─────────────┐    POST     ┌──────────────┐   read    ┌──────────────────┐
│  Sensores   │ ──────────▶ │  FastAPI     │ ────────▶ │  MongoDB         │
│  IoT (UPY)  │             │  /api/...    │           │  SensoresRaw     │
└─────────────┘             └──────┬───────┘           └────────┬─────────┘
                                   │                            │
                                   │  scheduler 5 min           │
                                   ▼                            ▼
                            ┌─────────────────────────────────────────┐
                            │  Pipeline ETL  (dags/weather_pipeline)  │
                            │  extract → transform → IDW → load       │
                            └────────────────┬────────────────────────┘
                                             │
                                             ▼
                            ┌─────────────────────────────────────────┐
                            │  Colecciones procesadas                 │
                            │   · mediciones_analitica  (features)    │
                            │   · mapa_calor_actual     (grid IDW)    │
                            │   · resumen_ambiental     (KPIs)        │
                            └────────────────┬────────────────────────┘
                                             │  GET /api/...
                                             ▼
                                  ┌────────────────────┐
                                  │  Frontend web      │
                                  │  Leaflet + heat    │
                                  └────────────────────┘
```

---

## Stack tecnológico

| Capa            | Tecnología                                                      |
|-----------------|-----------------------------------------------------------------|
| Backend / API   | Python 3.11, FastAPI, Uvicorn                                   |
| Base de datos   | MongoDB (compatible con Azure Cosmos DB API for MongoDB)        |
| ETL / Ciencia   | pandas, numpy, scipy, geopy                                     |
| Persistencia    | pymongo                                                         |
| Frontend        | HTML5, CSS3, JavaScript vanilla, Leaflet, leaflet.heat          |
| Orquestación    | Scheduler en hilo dedicado (Python `threading`) cada 5 minutos  |

---

## Estructura del proyecto

```
Islas_de_Calor_Estancia/
├── API/
│   └── main_api.py              # FastAPI: endpoints + scheduler del pipeline
├── dags/
│   └── weather_pipeline.py      # Orquestación del ETL (extract → transform → load)
├── etl/
│   ├── extract/
│   │   └── extract.py           # Lectura desde MongoDB (SensoresRaw)
│   ├── transform/
│   │   ├── features.py          # Cálculo de UHI, índices y clasificaciones
│   │   ├── grid.py              # Interpolación espacial IDW
│   │   └── resumen.py           # Agregados globales (KPIs)
│   └── load/
│       └── load_mongo.py        # Escritura a colecciones procesadas
├── ml/
│   ├── train.py                 # Entrenamiento de modelos (en desarrollo)
│   └── predict.py               # Inferencia (en desarrollo)
├── web/
│   ├── index.html               # Landing del proyecto
│   ├── app.html                 # Dashboard + documentación de API
│   ├── script.js                # Cliente API + render de mapa de calor
│   ├── style.css                # Estilos del dashboard
│   ├── landing.css              # Estilos de la landing
│   └── assets/                  # Logos del UI
├── requirements.txt
├── .env                         # No versionado
└── .gitignore
```

---

## Requisitos previos

- **Python 3.11+**
- **MongoDB** accesible vía URI (local, Atlas o Cosmos DB API for MongoDB)
- `pip` para instalación de dependencias

---

## Instalación

```bash
git clone https://github.com/RamiroChay/Islas_de_Calor_Estancia.git
cd Islas_de_Calor_Estancia

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Dependencias principales (de `requirements.txt`):

```
fastapi · uvicorn · pymongo · pandas · numpy · scipy · geopy · joblib · sqlalchemy
```

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
MONGO_URI="mongodb+srv://<usuario>:<password>@<cluster>/..."
MONGO_DB="nombre_de_la_base"
```

> El archivo `.env` está excluido por `.gitignore`. Nunca lo subas al repositorio.

Colecciones esperadas en la base de datos:

| Colección                | Contenido                                                  |
|--------------------------|------------------------------------------------------------|
| `SensoresRaw`            | Lecturas crudas enviadas por los sensores                  |
| `mediciones_analitica`   | Features calculadas por el pipeline                        |
| `mapa_calor_actual`      | Grid interpolado (último ciclo)                            |
| `resumen_ambiental`      | KPIs globales (último ciclo)                               |

---

## Ejecución local

### 1. Levantar el API

```bash
uvicorn API.main_api:app --host 127.0.0.1 --port 8000 --reload
```

El scheduler interno comenzará a correr el pipeline cada 5 minutos automáticamente.

### 2. Servir el frontend

```bash
cd web
python3 -m http.server 5500
```

Abrir en el navegador:

- Landing: http://127.0.0.1:5500/index.html
- Dashboard: http://127.0.0.1:5500/app.html

---

## API REST

Base URL: `http://127.0.0.1:8000`

### `POST /api/sensores`

Recibe una lectura individual de un sensor.

**Body (JSON):**

```json
{
  "device_id": "sensor_01",
  "temperatura": 34.2,
  "humedad": 58.0,
  "salinidad": 0.42,
  "radiacion": 712.5,
  "lat": 20.9674,
  "lon": -89.5926,
  "estado": "ok"
}
```

### `GET /api/sensores`

Devuelve todas las lecturas procesadas con features e índices.

### `GET /api/grid`

Devuelve el grid interpolado (mapa de calor de UHI).

### `GET /api/resumen`

Devuelve los KPIs globales del último ciclo del pipeline.

---

## Pipeline de datos

El pipeline (`dags/weather_pipeline.py`) corre cada 5 minutos en un hilo daemon arrancado en el evento `startup` del API.

```
1. EXTRACT      Lee SensoresRaw desde MongoDB
2. TRANSFORM    Limpia, normaliza y calcula features
3. LOAD         Persiste features en mediciones_analitica
4. GRID         Interpolación IDW (50×50) sobre el área de cobertura
5. RESUMEN      Agrega KPIs globales en resumen_ambiental
6. LOAD GRID    Persiste el mapa interpolado en mapa_calor_actual
```

Cada ciclo reemplaza el batch anterior para mantener únicamente la fotografía más reciente del estado térmico de la ciudad.

---

## Índices y métricas calculadas

| Variable               | Fórmula / Definición                                                                |
|------------------------|--------------------------------------------------------------------------------------|
| `uhi`                  | `T - T_ref`, donde `T_ref` es la temperatura mínima del lote (proxy rural)           |
| `temp_norm`            | Normalización min–max de temperatura                                                 |
| `humedad_norm`         | `H / 100`                                                                            |
| `radiacion_norm`       | `R / R_max`                                                                          |
| `deficit_humedad`      | `H_ref - H` (déficit respecto al máximo observado)                                   |
| `indice_vegetacion`    | `-0.6 · temp_norm + 0.4 · humedad_norm` — proxy físico                               |
| `indice_energia`       | `radiacion_norm · (1 - humedad_norm)`                                                |
| `zona_termica`         | `baja` (<2 °C), `media` (2–4 °C), `alta` (>4 °C)                                     |
| `tipo_superficie`      | `urbano` / `natural` según mediana de salinidad                                      |

La interpolación espacial es **IDW (Inverse Distance Weighting)** con potencia `p = 2` sobre un grid de 50 × 50.

---

## Frontend

- **Landing (`index.html`)**: presentación del proyecto, arquitectura, universidades participantes y documentación pública de la API.
- **Dashboard (`app.html`)**: visualizador interactivo con mapa Leaflet, capa de heatmap, lista de sensores activos y panel de KPIs del resumen ambiental.
- Refresh automático cada 60 segundos (`setInterval(fetchAll, 60000)`).
- Sin frameworks: HTML, CSS y JavaScript vanilla.

---

## Hoja de ruta

- [ ] Entrenamiento de modelos predictivos de UHI (`ml/train.py`, `ml/predict.py`).
- [ ] Pronóstico horario por zona térmica.
- [ ] Despliegue productivo (contenedor + CI/CD).
- [ ] Autenticación de dispositivos en `POST /api/sensores`.
- [ ] Histórico navegable de mapas de calor.
- [ ] Exportación de datasets abiertos (CSV / GeoJSON).

---

## Créditos

Proyecto desarrollado en el marco de una estancia de investigación con la participación de:

- **Universidad Politécnica de Yucatán (UPY)**
- **Universidad Autónoma de Yucatán (UADY)**

Sensores, software y visualización: equipo de Islas de Calor — Mérida, Yucatán.

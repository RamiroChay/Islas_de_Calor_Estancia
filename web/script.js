const map = L.map('map').setView([20.97, -89.62], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap'
}).addTo(map);

let heatLayer;
let sensorMarkers = [];
let coverageCircle;

let sensoresData = [];
let heatData = [];
let resumenData = {};

/* ======================
   FETCH
====================== */

async function fetchData(){
  try {
    sensoresData = await fetch("http://127.0.0.1:8000/api/sensores").then(r=>r.json());
    heatData = await fetch("http://127.0.0.1:8000/api/grid").then(r=>r.json());
    resumenData = await fetch("http://127.0.0.1:8000/api/resumen").then(r=>r.json());

    setupSelector();
    showGeneralMode();

  } catch(e){
    console.error("Error cargando datos:", e);
  }
}

/* ======================
   SELECTOR
====================== */

function setupSelector(){

  const sel = document.getElementById("selector");
  sel.innerHTML = "";

  const optGeneral = document.createElement("option");
  optGeneral.value = "general";
  optGeneral.text = "GENERAL";
  sel.appendChild(optGeneral);

  sensoresData.forEach((s, i)=>{
    const opt = document.createElement("option");
    opt.value = i;
    opt.text = "Sensor " + (i+1);
    sel.appendChild(opt);
  });

  sel.onchange = (e)=>{
    if(e.target.value === "general"){
      showGeneralMode();
    } else {
      showSensorMode(sensoresData[e.target.value]);
    }
  };
}

/* ======================
   GENERAL MODE
====================== */

function showGeneralMode(){

  clearMap();

  renderHeatmap(heatData);

  document.getElementById("timestamp").innerText =
    resumenData?.pipeline_timestamp ?? "---";

  document.getElementById("panel-content").innerHTML = `
    <div class="grid">
      <div><div class="label">Temp Prom</div><div class="value">${resumenData?.temp_promedio ?? "N/A"}</div></div>
      <div><div class="label">Humedad</div><div class="value">${resumenData?.humedad_promedio ?? "N/A"}</div></div>
      <div><div class="label">UHI</div><div class="value">${resumenData?.uhi_promedio ?? "N/A"}</div></div>
      <div><div class="label">Zona</div><div class="value">${resumenData?.zona_dominante ?? "N/A"}</div></div>
    </div>
  `;
}

/* ======================
   SENSOR MODE
====================== */

function showSensorMode(sensor){

  clearMap();

  const marker = L.marker([sensor.lat, sensor.lon]).addTo(map);
  sensorMarkers.push(marker);

  map.setView([sensor.lat, sensor.lon], 15);

  coverageCircle = L.circle([sensor.lat, sensor.lon], {
    radius: 500,
    color: 'red',
    fillOpacity: 0.1
  }).addTo(map);

  document.getElementById("panel-content").innerHTML = `
    <div class="grid">

      <div><div class="label">Lat</div><div class="value">${sensor.lat}</div></div>
      <div><div class="label">Lon</div><div class="value">${sensor.lon}</div></div>

      <div><div class="label">Temperatura</div><div class="value">${sensor.temperatura ?? "N/A"}</div></div>
      <div><div class="label">Humedad</div><div class="value">${sensor.humedad ?? "N/A"}</div></div>

      <div><div class="label">Radiación</div><div class="value">${sensor.radiacion ?? "N/A"}</div></div>
      <div><div class="label">Salinidad</div><div class="value">${sensor.salinidad ?? "N/A"}</div></div>

    </div>

    <div class="title" style="margin-top:20px;">PARÁMETROS DERIVADOS</div>

    <div class="grid">

      <div><div class="label">UHI</div><div class="value">${sensor.uhi ?? "N/A"}</div></div>
      <div><div class="label">Déficit humedad</div><div class="value">${sensor.deficit_humedad ?? "N/A"}</div></div>

      <div><div class="label">Tipo superficie</div><div class="value">${sensor.tipo_superficie ?? "N/A"}</div></div>
      <div><div class="label">Índice vegetación</div><div class="value">${sensor.indice_vegetacion ?? "N/A"}</div></div>

      <div><div class="label">Índice energía</div><div class="value">${sensor.indice_energia ?? "N/A"}</div></div>
      <div><div class="label">Zona térmica</div><div class="value">${sensor.zona_termica ?? "N/A"}</div></div>

    </div>
  `;
}

/* ======================
   HEATMAP
====================== */

function renderHeatmap(data){

  const points = data.map(p => [p.lat, p.lon, p.uhi]);

  heatLayer = L.heatLayer(points, {
    radius: 25,
    blur: 20,
    maxZoom: 17
  }).addTo(map);
}

/* ======================
   CLEAR MAP
====================== */

function clearMap(){

  if(heatLayer) map.removeLayer(heatLayer);

  sensorMarkers.forEach(m => map.removeLayer(m));
  sensorMarkers = [];

  if(coverageCircle) map.removeLayer(coverageCircle);
}

/* ======================
   INIT
====================== */

fetchData();
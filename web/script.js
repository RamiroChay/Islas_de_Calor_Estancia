// 1. Configuración del Mapa
const map = L.map('map', {
    preferCanvas: true // Optimización para manejar miles de puntos
}).setView([20.97, -89.62], 12);

// 2. Capa Base Dark (CartoDB)
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO'
}).addTo(map);

let heatLayer = null;
let markersGroup = L.layerGroup().addTo(map);
const loader = document.getElementById('loader');

// 3. Función de Carga y Procesamiento
function actualizarVisualizacion(url) {
    loader.style.display = 'block';
    Papa.parse(url, {
        download: true,
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
        complete: function(results) {
            if (heatLayer) map.removeLayer(heatLayer);
            markersGroup.clearLayers();

            const heatPoints = [];
            const stationData = [];

            results.data.forEach(d => {
                // 1. Detección robusta de coordenadas (evita el error 'undefined')
                const lat = d.latitud || d.lat || d.Latitud;
                const lon = d.longitud || d.lon || d.long || d.Longitud;
                const uhi = d.uhi_intensity || 0;

                if (!lat || !lon) return;

                if (d.is_station === 1) {
                    stationData.push({ ...d, lat: lat, lon: lon });
                } else {
                    // 2. Filtro de sensibilidad:
                    // Si el valor es muy bajo, lo ignoramos para que no "ensucie" con azul
                    if (uhi > 0.4) { 
                        heatPoints.push([lat, lon, uhi]);
                    }
                }
            });

            // 3. Ajuste de la Capa de Calor
            heatLayer = L.heatLayer(heatPoints, {
                radius: 18,
                blur: 20,
                maxZoom: 13, 
                max: 4.0, 
                minOpacity: 0.3, // Muy importante para la transparencia
                gradient: {
                    0.1: 'rgba(0, 255, 255, 0.4)', // Azul traslúcido
                    0.5: 'rgba(255, 255, 0, 0.5)', 
                    0.8: 'rgba(255, 140, 0, 0.6)', 
                    1.0: 'rgba(255, 0, 0, 0.7)'    // Rojo traslúcido
                }
            }).addTo(map);

            // 4. Dibujar estaciones (Validación visual)
            stationData.forEach(st => {
                const marker = L.circleMarker([st.lat, st.lon], {
                    radius: 7, fillColor: "#fff", color: "#000", weight: 2, fillOpacity: 1
                }).addTo(markersGroup);

                marker.bindTooltip(`${(st.temp_est || st.temp_avg).toFixed(1)}°C`, {
                    permanent: true, direction: 'top', className: 'temp-label'
                });
            });

            loader.style.display = 'none';
        }
    });
}
// 6. Eventos
document.getElementById('select-month').addEventListener('change', (e) => {
    actualizarVisualizacion(e.target.value);
});

// Carga Inicial
window.onload = () => {
    actualizarVisualizacion(document.getElementById('select-month').value);
};
/* =====================================================
   Islas de Calor · Plataforma de Análisis Urbano
   ===================================================== */

// En desarrollo apunta a http://127.0.0.1:8000.
// En producción usa el mismo dominio que sirve el frontend.
const API = (location.hostname === "127.0.0.1" || location.hostname === "localhost")
  ? "http://127.0.0.1:8000"
  : "";  // mismo origen — el server sirve tanto /api/* como los estáticos

// Credenciales del dashboard público (auth blanda).
// Deben coincidir con API_USER / API_PASS del .env del servidor.
const API_USER = "publico";
const API_PASS = "islas2026";
const API_HEADERS = { "Authorization": "Basic " + btoa(`${API_USER}:${API_PASS}`) };

function apiGet(path) {
  return fetch(`${API}${path}`, { headers: API_HEADERS }).then(r => {
    if (!r.ok) throw new Error(`${path} → HTTP ${r.status}`);
    return r.json();
  });
}

const ZONA_COLOR = {
  alta:  '#dc2626',
  media: '#f97316',
  baja:  '#10b981',
};

let sensorsData = [];
let gridData    = [];
let resumenData = {};

let heatLayer = null;
let sensorMarkers = [];
let sensorLabels  = [];
let coverageLayers = [];
let highlightCircle = null;

const fmt = (n, dec = 1) => (n == null || isNaN(n)) ? '—' : Number(n).toFixed(dec);
const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : '—';

/* ============================
   MAPA
   ============================ */
const map = L.map('map', {
  zoomControl: true,
  attributionControl: true,
}).setView([20.97, -89.62], 13);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '© OpenStreetMap · © CARTO',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

/* ============================
   FETCH
   ============================ */
async function fetchAll() {
  try {
    setStatus('loading', 'Cargando…');
    const [s, g, r] = await Promise.all([
      apiGet('/api/sensores'),
      apiGet('/api/grid'),
      apiGet('/api/resumen'),
    ]);

    sensorsData = Array.isArray(s) ? s : [];
    gridData    = Array.isArray(g) ? g : [];
    resumenData = r || {};

    setStatus('ok', `${sensorsData.length} sensores en línea`);
    setLastUpdate(resumenData.pipeline_timestamp);

    populateSelector();
    renderAll();
    toast('Datos actualizados', 'ok');
  } catch (e) {
    console.error(e);
    setStatus('offline', 'Sin conexión a la API');
    toast('Error al conectar con la API', 'err');
  }
}

function setStatus(mode, text) {
  const pill = document.getElementById('status-pill');
  pill.classList.remove('offline', 'loading');
  if (mode === 'offline') pill.classList.add('offline');
  if (mode === 'loading') pill.classList.add('loading');
  document.getElementById('status-text').textContent = text;
}

function setLastUpdate(ts) {
  const el = document.getElementById('last-update');
  if (!ts) { el.textContent = '—'; return; }
  const d = new Date(ts);
  el.textContent = d.toLocaleString('es-MX', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

/* ============================
   RENDER MAESTRO
   ============================ */
function renderAll() {
  renderMap();
  renderHero();
  renderOverlays();
  renderKPIs();
  renderDistribution();
  updateDateCount();
}

/* ============================
   MAPA · capas
   ============================ */
function clearMapLayers() {
  if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
  sensorMarkers.forEach(m => map.removeLayer(m)); sensorMarkers = [];
  sensorLabels.forEach(m => map.removeLayer(m));  sensorLabels  = [];
  coverageLayers.forEach(c => map.removeLayer(c)); coverageLayers = [];
}

function getChecked(sel) {
  return Array.from(document.querySelectorAll(sel + ':checked')).map(el => el.value);
}

function getDateRange() {
  const from = document.getElementById('date-from')?.value;
  const to   = document.getElementById('date-to')?.value;
  const fromTs = from ? new Date(from + 'T00:00:00').getTime() : null;
  const toTs   = to   ? new Date(to   + 'T23:59:59.999').getTime() : null;
  return { fromTs, toTs };
}

function inDateRange(sensor, range) {
  if (!sensor.timestamp) return true;
  const t = new Date(sensor.timestamp).getTime();
  if (range.fromTs != null && t < range.fromTs) return false;
  if (range.toTs   != null && t > range.toTs)   return false;
  return true;
}

function filteredSensors() {
  const z = getChecked('.zona-filter');
  const s = getChecked('.sup-filter');
  const range = getDateRange();
  return sensorsData.filter(d =>
    z.includes(d.zona_termica) &&
    s.includes(d.tipo_superficie) &&
    inDateRange(d, range)
  );
}

function updateDateCount() {
  const el = document.getElementById('date-count');
  if (!el) return;
  const total = sensorsData.length;
  const matched = filteredSensors().length;
  el.textContent = `${matched} / ${total}`;
}

function renderMap() {
  clearMapLayers();

  const showHeat   = document.getElementById('layer-heat').checked;
  const showSens   = document.getElementById('layer-sensors').checked;
  const showCov    = document.getElementById('layer-coverage').checked;
  const showLabels = document.getElementById('layer-labels').checked;

  if (showHeat && gridData.length) {
    const maxU = Math.max(...gridData.map(p => p.uhi)) || 1;
    const points = gridData.map(p => [p.lat, p.lon, p.uhi / maxU]);
    heatLayer = L.heatLayer(points, {
      radius: 28,
      blur: 24,
      maxZoom: 17,
      minOpacity: 0.35,
      gradient: {
        0.0: '#1e3a8a',
        0.25: '#06b6d4',
        0.5: '#fbbf24',
        0.75: '#ef4444',
        1.0: '#7f1d1d',
      },
    }).addTo(map);
  }

  if (showSens) {
    filteredSensors().forEach(s => {
      const idx = sensorsData.indexOf(s);
      const color = ZONA_COLOR[s.zona_termica] || '#6b7280';
      const marker = L.circleMarker([s.lat, s.lon], {
        radius: 8,
        color: 'white',
        weight: 2,
        fillColor: color,
        fillOpacity: 0.95,
      }).addTo(map);

      marker.bindTooltip(
        `<b>Sensor ${idx + 1}</b> · ${s.device_id || ''}<br>
         🌡 ${fmt(s.temperatura)}°C · 💧 ${fmt(s.humedad)}%<br>
         UHI <b>${fmt(s.uhi, 2)}</b> · Zona ${s.zona_termica}`,
        { direction: 'top', offset: [0, -8] }
      );
      marker.on('click', () => {
        document.getElementById('selector').value = String(idx);
        onSelectorChange();
      });
      sensorMarkers.push(marker);

      if (showCov) {
        const c = L.circle([s.lat, s.lon], {
          radius: 400,
          color,
          weight: 1,
          fillOpacity: 0.06,
          dashArray: '4 4',
        }).addTo(map);
        coverageLayers.push(c);
      }

      if (showLabels) {
        const lbl = L.marker([s.lat, s.lon], {
          icon: L.divIcon({
            className: 'sensor-label',
            html: `${fmt(s.temperatura)}°`,
            iconSize: null,
            iconAnchor: [-12, 8],
          }),
          interactive: false,
        }).addTo(map);
        sensorLabels.push(lbl);
      }
    });
  }
}

/* ============================
   OVERLAY CARDS
   ============================ */
function renderOverlays() {
  document.getElementById('ov-sensors').textContent = sensorsData.length || '0';
  document.getElementById('ov-grid').textContent    = gridData.length ? `${gridData.length} pts` : '—';
  document.getElementById('ov-uhi').innerHTML       = `${fmt(resumenData.uhi_max, 2)}<span class="ou">°C</span>`;
}

/* ============================
   HERO + DISTRIBUTION
   ============================ */
function renderHero() {
  const r = resumenData || {};
  document.getElementById('hero-temp').textContent = fmt(r.temp_promedio);
  document.getElementById('hero-uhi').textContent  = fmt(r.uhi_promedio, 2);

  const zona = (r.zona_dominante || 'media').toLowerCase();
  const chip = document.getElementById('hero-zona');
  chip.textContent = `Zona ${cap(zona)}`;
  chip.className = `zona-chip ${zona}`;

  document.getElementById('hero-count').textContent = r.num_sensores ?? sensorsData.length ?? '—';
}

function renderKPIs() {
  const r = resumenData || {};
  const kpis = [
    { label: 'Temp máx', value: fmt(r.temp_max), unit: '°C', bar: ((r.temp_max ?? 25) - 25) / 15 },
    { label: 'Temp mín', value: fmt(r.temp_min), unit: '°C', bar: ((r.temp_min ?? 25) - 25) / 15 },
    { label: 'Humedad prom', value: fmt(r.humedad_promedio), unit: '%', bar: (r.humedad_promedio ?? 0) / 100 },
    { label: 'UHI máx',  value: fmt(r.uhi_max, 2), unit: '°C', bar: (r.uhi_max ?? 0) / 10 },
    { label: 'Zona dominante', value: cap(r.zona_dominante || '—'), sub: 'modo térmico' },
    { label: 'Sensores activos', value: r.num_sensores ?? sensorsData.length ?? '—', sub: 'en red' },
  ];

  document.getElementById('kpi-grid').innerHTML = kpis.map(k => `
    <div class="kpi-card">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.value}${k.unit ? `<span class="kpi-unit">${k.unit}</span>` : ''}</div>
      ${k.sub ? `<div class="kpi-sub">${k.sub}</div>` : ''}
      ${k.bar != null ? `<div class="kpi-bar"><div class="kpi-bar-fill" style="width:${Math.min(100, Math.max(0, k.bar*100))}%"></div></div>` : ''}
    </div>
  `).join('');
}

function renderDistribution() {
  const counts = { alta: 0, media: 0, baja: 0 };
  sensorsData.forEach(s => {
    const z = s.zona_termica;
    if (counts[z] != null) counts[z]++;
  });
  const total = sensorsData.length || 1;

  document.getElementById('dist-chart').innerHTML = ['alta', 'media', 'baja'].map(z => {
    const pct = ((counts[z] / total) * 100).toFixed(0);
    return `
      <div class="dist-row">
        <span class="lbl">${cap(z)}</span>
        <div class="dist-bar-track"><div class="dist-bar-fill ${z}" style="width:${pct}%"></div></div>
        <span class="dist-count">${counts[z]}<span class="pct">${pct}%</span></span>
      </div>
    `;
  }).join('');
}

/* ============================
   SELECTOR
   ============================ */
function populateSelector() {
  const sel = document.getElementById('selector');
  sel.innerHTML =
    '<option value="general">Vista general</option>' +
    sensorsData.map((s, i) =>
      `<option value="${i}">Sensor ${i + 1} · ${cap(s.zona_termica)} · ${cap(s.tipo_superficie)}</option>`
    ).join('');
  sel.onchange = onSelectorChange;
}

function onSelectorChange() {
  const v = document.getElementById('selector').value;
  const section = document.getElementById('sensor-detail-section');

  if (highlightCircle) { map.removeLayer(highlightCircle); highlightCircle = null; }

  if (v === 'general') {
    section.hidden = true;
    map.setView([20.97, -89.62], 13);
    return;
  }

  const s = sensorsData[Number(v)];
  if (!s) return;

  section.hidden = false;
  document.getElementById('sensor-detail').innerHTML = `
    <div class="sd-header">
      <div class="sd-title">Sensor ${Number(v) + 1}${s.device_id ? ` · ${s.device_id}` : ''}</div>
      <span class="sd-tag ${s.zona_termica}">${s.zona_termica}</span>
    </div>

    <div class="sd-row"><span class="lbl">Temperatura</span><span class="val">${fmt(s.temperatura)} °C</span></div>
    <div class="sd-row"><span class="lbl">Humedad</span><span class="val">${fmt(s.humedad)} %</span></div>
    <div class="sd-row"><span class="lbl">Radiación</span><span class="val">${fmt(s.radiacion, 0)} W/m²</span></div>
    <div class="sd-row"><span class="lbl">Salinidad</span><span class="val">${fmt(s.salinidad, 3)}</span></div>
    <div class="sd-row"><span class="lbl">UHI</span><span class="val">${fmt(s.uhi, 2)} °C</span></div>
    <div class="sd-row"><span class="lbl">Déficit humedad</span><span class="val">${fmt(s.deficit_humedad)} %</span></div>
    <div class="sd-row"><span class="lbl">Tipo de superficie</span><span class="val">${cap(s.tipo_superficie)}</span></div>
    <div class="sd-row"><span class="lbl">Índice vegetación</span><span class="val">${fmt(s.indice_vegetacion, 3)}</span></div>
    <div class="sd-row"><span class="lbl">Índice energía</span><span class="val">${fmt(s.indice_energia, 3)}</span></div>
    <div class="sd-row"><span class="lbl">Coordenadas</span><span class="val">${fmt(s.lat, 4)}, ${fmt(s.lon, 4)}</span></div>
  `;

  map.flyTo([s.lat, s.lon], 16, { duration: 0.8 });
  highlightCircle = L.circle([s.lat, s.lon], {
    radius: 80, color: '#dc2626', weight: 3, fillOpacity: 0.15,
  }).addTo(map);
}

/* ============================
   EVENTOS UI
   ============================ */
['layer-heat', 'layer-sensors', 'layer-coverage', 'layer-labels'].forEach(id => {
  document.getElementById(id).addEventListener('change', renderMap);
});
document.querySelectorAll('.zona-filter, .sup-filter').forEach(el => el.addEventListener('change', () => {
  renderMap();
  updateDateCount();
}));

/* Filtro de rango de fechas */
['date-from', 'date-to'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('change', () => {
    renderMap();
    updateDateCount();
  });
});

document.getElementById('date-reset')?.addEventListener('click', () => {
  document.getElementById('date-from').value = '';
  document.getElementById('date-to').value   = '';
  renderMap();
  updateDateCount();
});

function toggleLeftPanel() {
  document.getElementById('layout').classList.toggle('left-collapsed');
  setTimeout(() => map.invalidateSize(), 260);
}

document.getElementById('left-collapse').addEventListener('click', toggleLeftPanel);
document.getElementById('floating-expand').addEventListener('click', toggleLeftPanel);

document.getElementById('btn-refresh').addEventListener('click', fetchAll);

/* ============================
   EXPORTACIÓN
   ============================ */
const exportBtn  = document.getElementById('btn-export');
const exportMenu = document.getElementById('export-menu');

exportBtn.addEventListener('click', e => {
  e.stopPropagation();
  exportMenu.hidden = !exportMenu.hidden;
});

document.addEventListener('click', () => { exportMenu.hidden = true; });

exportMenu.addEventListener('click', e => {
  e.stopPropagation();
  const btn = e.target.closest('button[data-export]');
  if (!btn) return;
  exportMenu.hidden = true;
  const action = btn.dataset.export;

  if (action === 'sensors-csv') downloadCSV('sensores', sensorsData);
  else if (action === 'grid-csv') downloadCSV('grid_heatmap', gridData);
  else if (action === 'xlsx') downloadXLSX();
});

function downloadCSV(name, rows) {
  if (!rows || !rows.length) { toast('No hay datos para exportar', 'err'); return; }
  const keys = Object.keys(rows[0]);
  const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const csv = [keys.join(','), ...rows.map(r => keys.map(k => esc(r[k])).join(','))].join('\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${name}_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
  toast(`${name}.csv descargado`, 'ok');
}

function downloadXLSX() {
  if (!window.XLSX) { toast('Excel no disponible (cargando…)', 'err'); return; }
  if (!sensorsData.length && !gridData.length) { toast('No hay datos para exportar', 'err'); return; }

  const wb = XLSX.utils.book_new();

  if (sensorsData.length) {
    const ws = XLSX.utils.json_to_sheet(sensorsData);
    XLSX.utils.book_append_sheet(wb, ws, 'Sensores');
  }
  if (gridData.length) {
    const ws = XLSX.utils.json_to_sheet(gridData);
    XLSX.utils.book_append_sheet(wb, ws, 'Grid_UHI');
  }
  if (resumenData && Object.keys(resumenData).length) {
    const ws = XLSX.utils.json_to_sheet([resumenData]);
    XLSX.utils.book_append_sheet(wb, ws, 'Resumen');
  }

  XLSX.writeFile(wb, `islas_calor_merida_${new Date().toISOString().slice(0, 10)}.xlsx`);
  toast('Reporte Excel descargado', 'ok');
}

/* ============================
   TOAST
   ============================ */
function toast(msg, kind = '') {
  const old = document.querySelector('.toast');
  if (old) old.remove();
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = msg;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 250);
  }, 2500);
}

/* ============================
   TAB SWITCHING · Dashboard / Docs
   ============================ */
const navTabs    = document.querySelectorAll('.topbar-tab');
const viewMain   = document.getElementById('layout');
const viewDocs   = document.getElementById('docs-view');
const topActions = document.querySelector('.topbar-actions');
const topCenter  = document.querySelector('.topbar-center');

function setView(name) {
  navTabs.forEach(t => t.classList.toggle('active', t.dataset.view === name));
  viewMain.hidden = name !== 'dashboard';
  viewDocs.hidden = name !== 'docs';

  // Esconde controles del dashboard cuando estás en docs
  topActions.style.visibility = name === 'dashboard' ? 'visible' : 'hidden';
  topCenter.style.visibility  = name === 'dashboard' ? 'visible' : 'hidden';

  if (name === 'dashboard') {
    setTimeout(() => map.invalidateSize(), 60);
  }
  if (name === 'docs' && window.hljs) {
    window.hljs.highlightAll();
  }
  if (name === 'docs') {
    document.querySelector('.docs-content')?.scrollTo({ top: 0 });
  }
}

navTabs.forEach(t => t.addEventListener('click', () => setView(t.dataset.view)));

// Permite que el landing enlace directo a la docu con ?view=docs
const _initialView = new URLSearchParams(window.location.search).get('view');
if (_initialView === 'docs') {
  document.addEventListener('DOMContentLoaded', () => setView('docs'));
  if (document.readyState !== 'loading') setView('docs');
}

/* ============================
   DOCS · Copy-to-clipboard
   ============================ */
document.addEventListener('click', async e => {
  const btn = e.target.closest('.code-copy');
  if (!btn) return;
  const code = btn.closest('.code-block')?.querySelector('code')?.innerText;
  if (!code) return;
  try {
    await navigator.clipboard.writeText(code);
    btn.textContent = '✓ Copiado';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copiar'; btn.classList.remove('copied'); }, 1600);
  } catch {
    toast('No se pudo copiar', 'err');
  }
});

document.addEventListener('click', async e => {
  const btn = e.target.closest('[data-copy-target]');
  if (!btn) return;
  const target = document.getElementById(btn.dataset.copyTarget);
  if (!target) return;
  try {
    await navigator.clipboard.writeText(target.innerText);
    const txt = btn.textContent;
    btn.textContent = '✓ Copiado';
    setTimeout(() => { btn.textContent = txt; }, 1600);
  } catch {}
});

/* ============================
   DOCS · TOC active highlight
   ============================ */
const tocLinks = document.querySelectorAll('.toc-link');
const sections = Array.from(tocLinks)
  .map(l => document.querySelector(l.getAttribute('href')))
  .filter(Boolean);

const docsContent = document.querySelector('.docs-content');
if (docsContent) {
  const setActive = id => {
    tocLinks.forEach(l => l.classList.toggle('active', l.getAttribute('href') === `#${id}`));
  };

  const io = new IntersectionObserver(
    entries => {
      const visible = entries.filter(e => e.isIntersecting)
                             .sort((a, b) => a.target.offsetTop - b.target.offsetTop)[0];
      if (visible) setActive(visible.target.id);
    },
    { root: docsContent, rootMargin: '-20% 0px -70% 0px', threshold: 0 }
  );
  sections.forEach(s => io.observe(s));

  tocLinks.forEach(l => l.addEventListener('click', e => {
    e.preventDefault();
    const id = l.getAttribute('href').slice(1);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setActive(id);
  }));
}

/* ============================
   AUTO-REFRESH cada 60s
   ============================ */
setInterval(fetchAll, 60000);

/* ============================
   INIT
   ============================ */
fetchAll();

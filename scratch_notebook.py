! pip install numpy pandas matplotlib seaborn folium branca geopandas mapclassify h3pandas h3 networkx statsmodels scikit-learn groq --quiet


# --- CELL ---
import json
import os
import pathlib
import re
import warnings
from difflib import SequenceMatcher

from groq import Groq

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns

import folium
from folium.plugins import MarkerCluster, HeatMap
import branca.colormap as cm_folium
from branca.element import MacroElement, Template
import h3pandas
import networkx as nx
from sklearn.neighbors import BallTree
from statsmodels.tsa.seasonal import seasonal_decompose

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', palette='Set2')
plt.rcParams.update({'figure.dpi': 100})
print('Librerías cargadas correctamente.')


# --- CELL ---
DATA_DIR  = 'data_london'
DASH_DIR  = 'dashboard'
os.makedirs(f'{DASH_DIR}/img',  exist_ok=True)
os.makedirs(f'{DASH_DIR}/maps', exist_ok=True)

# STATION_INFO: todas las estaciones LAQN de Londres con archivo descargado
# Se construye dinámicamente comprobando qué archivos existen en data_london/raw/laqn/
_laqn_meta = json.load(open(f'{DATA_DIR}/metadata/laqn_all_no2_stations.json', encoding='utf-8'))
_avail = {p.parent.name for p in pathlib.Path(f'{DATA_DIR}/raw/laqn').glob('*/no2_pm25_o3_2019_2024.csv')}

STATION_INFO = {
    s['code']: {
        'name': s['name'],
        'type': s['type'],
        'lat':  float(s['lat']),
        'lon':  float(s['lon']),
        'authority': s['authority'],
    }
    for s in _laqn_meta
    if s['code'] in _avail
}
# Añadir WM6 y CT3 si están presentes (descargadas previamente, no en la lista API)
_extra = {
    'WM6': {'name': 'Westminster - Oxford Street',     'type': 'Kerbside',         'lat': 51.51393, 'lon': -0.15279, 'authority': 'Westminster'},
    'CT3': {'name': 'City of London - Aldgate School', 'type': 'Urban Background', 'lat': 51.52185, 'lon': -0.12740, 'authority': 'City of London'},
}
for code, info in _extra.items():
    if code in _avail and code not in STATION_INFO:
        STATION_INFO[code] = info

print(f'Estaciones LAQN cargadas: {len(STATION_INFO)}')

def load_no2_station(station):
    path = f'{DATA_DIR}/raw/laqn/{station}/no2_pm25_o3_2019_2024.csv'
    df = pd.read_csv(path)
    df['ReadingDateTime'] = pd.to_datetime(df['ReadingDateTime'], dayfirst=True, format='mixed')
    no2 = df[df['Species'] == 'NO2'].set_index('ReadingDateTime')['Value']
    return no2[~no2.index.duplicated(keep='first')]

no2_raw = pd.DataFrame({s: load_no2_station(s) for s in STATION_INFO})
no2_raw = no2_raw.sort_index().asfreq('h')

stops         = pd.read_csv(f'{DATA_DIR}/metadata/tfl_geo_stops.csv').dropna(subset=['stop_lat','stop_lon'])
gtfs_stops    = pd.read_csv(f'{DATA_DIR}/raw/tfl/tfl_stationdata_gtfs/stops.txt')
gtfs_pathways = pd.read_csv(f'{DATA_DIR}/raw/tfl/tfl_stationdata_gtfs/pathways.txt')
gtfs_stations = gtfs_stops[gtfs_stops['location_type'] == 1].copy()

RUTAS_DIR = f'{DATA_DIR}/raw/rutas'
BUS_ROUTES_PATH = f'{RUTAS_DIR}/rutas_bus_londres.csv'
METRO_ROUTES_PATH = f'{RUTAS_DIR}/rutas_metro_londres.csv'
routes_bus = pd.read_csv(BUS_ROUTES_PATH)
routes_metro = pd.read_csv(METRO_ROUTES_PATH)
routes_bus['Linea'] = routes_bus['Linea'].astype(str)
routes_metro['Linea'] = routes_metro['Linea'].astype(str)

print(f'NO2  crudo : {no2_raw.shape[0]:,} horas x {no2_raw.shape[1]} estaciones')
print(f'Periodo    : {no2_raw.index[0].date()} -> {no2_raw.index[-1].date()}')
print(f'Paradas TfL: {len(stops):,}')
print(f'Hubs GTFS  : {len(gtfs_stations)}')
print(f'Pathways   : {len(gtfs_pathways):,}')
print(f'Rutas bus  : {routes_bus.shape[0]:,} puntos | {routes_bus["Linea"].nunique()} líneas')
print(f'Rutas metro: {routes_metro.shape[0]:,} puntos | {routes_metro["Linea"].nunique()} líneas')

mask_bus   = stops['stop_name'].str.contains('Bus', case=False, na=False)
mask_metro = stops['parent_station'].astype(str).str.startswith('940') & ~mask_bus

def _collapse_stops(df, tipo):
    g = (df.dropna(subset=['parent_station'])
            .groupby('parent_station')
            .agg(stop_lat=('stop_lat', 'mean'),
                 stop_lon=('stop_lon', 'mean'),
                 n_puntos=('stop_id', 'size'))
            .reset_index())
    g['transport'] = tipo
    return g

stops_bus   = _collapse_stops(stops[mask_bus],   'bus')
stops_metro = _collapse_stops(stops[mask_metro], 'metro')
stops_pt    = pd.concat([stops_bus, stops_metro], ignore_index=True)

print(f'  Bus   colapsadas: {len(stops_bus):>4d}  (de {int(mask_bus.sum()):>4d} puntos)')
print(f'  Metro colapsadas: {len(stops_metro):>4d}  (de {int(mask_metro.sum()):>4d} puntos)')

no2_raw_full = no2_raw.copy()  # snapshot completo antes de filtros


# --- CELL ---
print('=' * 70)
print(f'  DATOS LAQN — NO\u2082 (2019-2023)  |  {no2_raw.shape[1]} estaciones')
print('=' * 70)
print(f'Dimensiones : {no2_raw.shape[0]:,} horas x {no2_raw.shape[1]} estaciones')
print(f'Periodo     : {no2_raw.index[0].date()} -> {no2_raw.index[-1].date()}')
print(f'Frecuencia  : {no2_raw.index.freq}')
print('\nEstadisticas globales NO\u2082 (\u03bcg/m\u00b3):')
display(no2_raw.describe().round(2))
print('\nMedia por estacion (\u03bcg/m\u00b3):')
display(no2_raw.mean().sort_values(ascending=False).round(1).to_frame('NO2_medio').T)


# --- CELL ---
# Usar el snapshot completo (incluye 2023 aunque cell 12 ya haya filtrado)
null_pct_full    = no2_raw_full.isna().mean().mul(100).sort_values(ascending=False)
yearly_null_full = no2_raw_full.resample('YE').apply(lambda x: x.isna().mean() * 100)
# yearly_null_full: filas=años (2019-2023), columnas=estaciones

# Ordenar columnas de mayor a menor nulo
hm_full = yearly_null_full[null_pct_full.index]
n_st = hm_full.shape[1]
n_yr = hm_full.shape[0]
THRESH_G = 40

fig, ax = plt.subplots(figsize=(min(n_st * 0.45, 28), max(3.5, n_yr * 0.9)))

sns.heatmap(
    hm_full, ax=ax,
    cmap=sns.light_palette('#c65f46', as_cmap=True),
    vmin=0, vmax=100,
    annot=True, fmt='.0f',
    annot_kws={'size': max(5, 8 - n_st // 20)},
    linewidths=0.4, linecolor='white',
    cbar_kws={'label': '% nulos', 'shrink': 0.6, 'pad': 0.01}
)
ax.set_title('% de valores nulos por estacion y ano — periodo completo (2019-2023)',
             fontweight='bold', fontsize=11)
ax.set_ylabel('Ano'); ax.set_xlabel('')
ax.set_yticklabels([str(y) for y in hm_full.index.year], rotation=0, fontsize=9)
ax.set_xticklabels(ax.get_xticklabels(), rotation=90,
                   fontsize=max(5, 8 - n_st // 20))

# Borde rojo en columnas sobre el umbral de descarte
for j, col in enumerate(hm_full.columns):
    if null_pct_full[col] > THRESH_G:
        ax.add_patch(plt.Rectangle((j, 0), 1, n_yr,
                                    fill=False, edgecolor='#c65f46',
                                    lw=2, clip_on=False))

plt.tight_layout()
plt.savefig(f'{DASH_DIR}/img/fig_nulos_no2_full.png', bbox_inches='tight', dpi=160)
plt.show()

print(f'Anios en heatmap: {list(hm_full.index.year)}')
print(f'Estaciones con >{THRESH_G}% nulos: {(null_pct_full > THRESH_G).sum()}')


# --- CELL ---
# ── Recorte temporal ─────────────────────────────────────────────────────
no2_raw = no2_raw[no2_raw.index.year < 2023]

null_pct    = no2_raw.isna().mean().mul(100).sort_values(ascending=False)
yearly_null = no2_raw.resample('YE').apply(lambda x: x.isna().mean() * 100)

# ── Criterios de descarte ─────────────────────────────────────────────────
THRESH_GLOBAL = 40
THRESH_YEAR   = 50

bad_global = set(null_pct[null_pct > THRESH_GLOBAL].index)
bad_year   = set(yearly_null.columns[(yearly_null > THRESH_YEAR).any(axis=0)])
drop_cols  = sorted(bad_global | bad_year)
keep_cols  = [s for s in null_pct.index if s not in drop_cols]

print(f'Estaciones originales              : {len(null_pct)}')
print(f'Descartadas (global>{THRESH_GLOBAL}% o año>{THRESH_YEAR}%): {len(drop_cols)}')
for s in drop_cols:
    g     = null_pct[s]
    yr_mx = yearly_null[s].max()
    reason = []
    if g     > THRESH_GLOBAL: reason.append(f'global {g:.0f}%')
    if yr_mx > THRESH_YEAR:   reason.append(f'max año {yr_mx:.0f}%')
    print(f'  ✗ {s:6s} ({STATION_INFO[s]["type"]:22s}) — {", ".join(reason)}')
print(f'Estaciones conservadas             : {len(keep_cols)}')

# ── Aplicar filtro ────────────────────────────────────────────────────────
no2_raw      = no2_raw[keep_cols]
STATION_INFO = {s: v for s, v in STATION_INFO.items() if s in keep_cols}

null_pct    = no2_raw.isna().mean().mul(100).sort_values(ascending=False)
yearly_null = no2_raw.resample('YE').apply(lambda x: x.isna().mean() * 100)
n_st        = yearly_null.shape[1]
n_yr        = yearly_null.shape[0]

# ── Heatmap: estaciones en eje X, años en eje Y, con anotaciones ──────────
hm_data = yearly_null[[c for c in null_pct.index if c != 'WAB']]   # ordenado por nulo desc., sin WAB

fig, ax = plt.subplots(figsize=(min(n_st * 0.45, 28), max(3.5, n_yr * 0.9)))

sns.heatmap(
    hm_data, ax=ax,
    cmap=sns.light_palette('#c65f46', as_cmap=True),
    vmin=0, vmax=max(20, float(np.nanmax(hm_data.to_numpy()))),
    annot=True, fmt='.0f',
    annot_kws={'size': max(5, 8 - n_st // 20)},
    linewidths=0.4, linecolor='white',
    cbar_kws={'label': '% nulos', 'shrink': 0.6, 'pad': 0.01}
)
ax.set_title(
    f'% de valores nulos — {n_st} estaciones conservadas (2019-2022)',
    fontweight='bold', fontsize=11)
ax.set_ylabel('Ano'); ax.set_xlabel('')
ax.set_yticklabels(hm_data.index.year, rotation=0, fontsize=9)
ax.set_xticklabels(ax.get_xticklabels(), rotation=90,
                   fontsize=max(5, 8 - n_st // 20))

plt.tight_layout()
plt.savefig(f'{DASH_DIR}/img/fig_nulos_no2.png', bbox_inches='tight', dpi=160)
plt.show()

print('\nNulos por estacion (2019-2022):')
for s, pct in null_pct.items():
    print(f'  {s:6s} ({STATION_INFO[s]["type"]:22s}): {pct:5.1f}%')


# --- CELL ---
no2_filled = no2_raw.interpolate(method='time', limit=48)

def seasonal_impute(df):
    out = df.copy()
    out['_h'] = out.index.hour
    out['_m'] = out.index.month
    for col in df.columns:
        grp = out.groupby(['_m','_h'])[col].transform('mean')
        out[col] = out[col].fillna(grp)
    return out.drop(columns=['_h','_m'])

no2_filled = seasonal_impute(no2_filled)
print(f'Nulos tras imputacion — NO2: {no2_filled.isna().sum().sum()}')
print(f'Dataset final: {no2_filled.shape[1]} estaciones x {no2_filled.shape[0]:,} horas')

# --- CELL ---
# Paleta por TIPO (compacta, legible con 63 estaciones)
TYPE_COLORS = {
    'Kerbside':         '#c65f46',
    'Roadside':         '#e67e22',
    'Urban Background': '#2a7db5',
    'Suburban':         '#2ecc71',
    'Industrial':       '#9b59b6',
}
def tipo_color(s):
    t = STATION_INFO[s]['type']
    return TYPE_COLORS.get(t, '#7f8c8d')

# Paleta individual para usar en las celdas de patrones
PALETTE = [tipo_color(s) for s in STATION_INFO]
STATION_COLORS = {s: tipo_color(s) for s in STATION_INFO}

# --- Panel 1: boxplot todas las estaciones ordenadas por mediana ---
no2_filled_cols = [c for c in STATION_INFO if c in no2_filled.columns]
orden = no2_filled[no2_filled_cols].median().sort_values().index.tolist()
colores_orden = [tipo_color(s) for s in orden]

fig, ax_box = plt.subplots(figsize=(10, 6))

data_bp = no2_filled[orden].clip(lower=0)
bp = ax_box.boxplot(
    [data_bp[s].dropna() for s in orden],
    patch_artist=True,
    showfliers=False,
    medianprops={'color': 'white', 'lw': 1.8},
    whiskerprops={'lw': 0.8},
    capprops={'lw': 0.8},
)
for patch, color in zip(bp['boxes'], colores_orden):
    patch.set_facecolor(color); patch.set_alpha(0.85)
ax_box.axhline(40, color='green', ls='--', lw=1.4, label='OMS 40 \u03bcg/m\u00b3')
ax_box.set_xticks(range(1, len(orden)+1))
ax_box.set_xticklabels(orden, rotation=90, fontsize=7)
ax_box.set_ylabel('NO\u2082 (\u03bcg/m\u00b3)')
ax_box.set_title('Distribucion por estacion (ordenadas por mediana)', fontweight='bold')
ax_box.legend(fontsize=9); ax_box.grid(axis='y', alpha=0.2)
handles = [Patch(color=c, label=t) for t, c in TYPE_COLORS.items()
           if any(STATION_INFO[s]['type']==t for s in no2_filled_cols)]
ax_box.legend(handles=handles + [plt.Line2D([0],[0],color='green',ls='--',label='OMS 40')],
               fontsize=8, loc='upper left')

plt.suptitle('Distribucion de NO\u2082 (2019-2022) — todas las estaciones', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{DASH_DIR}/img/fig_distribuciones.png', bbox_inches='tight', dpi=160)
plt.show()

# Outliers resumen por tipo
print('Outliers IQR por estacion:')
for s in no2_filled_cols:
    q1, q3 = no2_raw[s].quantile(0.25), no2_raw[s].quantile(0.75)
    iqr = q3 - q1
    mask = (no2_raw[s] < q1-1.5*iqr) | (no2_raw[s] > q3+1.5*iqr)
    pct = mask.sum() / no2_raw[s].notna().sum() * 100
    print(f'  {s:5s} ({STATION_INFO[s]["type"]:20s}): {pct:.1f}%')

no2_clip = no2_filled.clip(lower=0, upper=no2_filled.quantile(0.995).max())
print(f'\nno2_clip: {no2_clip.shape[1]} estaciones, {no2_clip.shape[0]:,} horas')


# --- CELL ---
DASH_BLOCKS = {'eda': '', 'no2': '', 'mapas': ''}

DASH_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Movilidad y sostenibilidad en Londres</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',Arial,sans-serif;background:#f5f6fa;color:#2c3e50}
  header{background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);color:#fff;
         padding:2rem 2.5rem;box-shadow:0 2px 8px rgba(0,0,0,.3)}
  header h1{font-size:1.6rem;margin-bottom:.3rem}
  header p{opacity:.9;font-size:.9rem}
  .tab-bar{display:flex;background:#fff;border-bottom:2px solid #e0e0e0;
           padding:0 2rem;box-shadow:0 1px 4px rgba(0,0,0,.06)}
  .tab-btn{padding:1rem 1.4rem;border:none;background:none;cursor:pointer;
           font-size:.95rem;color:#555;border-bottom:3px solid transparent;
           transition:all .2s;font-weight:500}
  .tab-btn:hover{color:#0f3460;background:#f0f4ff}
  .tab-btn.active{color:#0f3460;border-bottom-color:#0f3460;font-weight:700}
  .tab-content{display:none;padding:2rem 2.5rem}
  .tab-content.active{display:block}
  .img-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:1.5rem;margin-top:1rem}
  .img-card{background:#fff;border-radius:12px;padding:1rem;
            box-shadow:0 2px 8px rgba(0,0,0,.07)}
  .img-card img{width:100%;border-radius:8px}
  .img-card p{font-size:.82rem;color:#555;margin-top:.5rem;text-align:center}
  .map-selector{display:flex;gap:.8rem;flex-wrap:wrap;margin-bottom:1.2rem}
  .map-btn{padding:.55rem 1.1rem;border:2px solid #0f3460;border-radius:20px;
           background:#fff;cursor:pointer;font-size:.88rem;color:#0f3460;
           font-weight:500;transition:all .2s}
  .map-btn:hover,.map-btn.active{background:#0f3460;color:#fff}
  .map-frame{display:none;border-radius:12px;overflow:hidden;
             box-shadow:0 3px 12px rgba(0,0,0,.12)}
  .map-frame.active{display:block}
  .map-frame iframe{width:100%;height:580px;border:none}
  .data-table{width:100%;border-collapse:collapse;background:#fff;
              border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-top:1rem}
  .data-table th{background:#0f3460;color:#fff;padding:.7rem 1rem;
                 text-align:left;font-size:.85rem}
  .data-table td{padding:.6rem 1rem;border-bottom:1px solid #f0f0f0;font-size:.85rem}
  .data-table tr:last-child td{border-bottom:none}
  .section-title{font-size:1.1rem;font-weight:700;color:#0f3460;margin-bottom:1rem}
  .pending{background:#fff;border-radius:12px;padding:2rem;text-align:center;color:#999;
           font-style:italic;box-shadow:0 2px 8px rgba(0,0,0,.07)}
  .badge{display:inline-block;background:#e8f0fe;color:#0f3460;border-radius:6px;
         padding:.2rem .6rem;font-size:.78rem;font-weight:600;margin:.1rem}
</style>
</head>
<body>
<header>
  <h1>Movilidad y sostenibilidad ambiental en Londres</h1>
  <p>Trabajo final &middot; Ciudades Inteligentes &middot; Universidad Carlos III de Madrid &middot; 2025/2026</p>
  <p style="margin-top:.35rem">
    Emilio Hermosa Schiantarelli (100451150) &middot;
    Carlos Sanchez Arroyo (100451282) &middot;
    Rodrigo Valderrey Tarrero (100451271)
  </p>
  <p style="margin-top:.5rem">
    <span class="badge">RQ1 Ciudad real</span>
    <span class="badge">RQ2 Movilidad + Sostenibilidad</span>
    <span class="badge">RQ3 Dashboard</span>
    <span class="badge">RQ4 Series temporales + Grafo</span>
    <span class="badge">RQ5 Mapas geográficos</span>
  </p>
</header>
<div class="tab-bar">
  <button class="tab-btn active" onclick="showTab('eda',this)">1. EDA</button>
  <button class="tab-btn" onclick="showTab('no2',this)">2. Análisis NO₂</button>
  <button class="tab-btn" onclick="showTab('mapas',this)">3. Mapas</button>
</div>
<div id="tab-eda" class="tab-content active">
  <p class="section-title">Análisis Exploratorio de los datos LAQN (NO₂, 2019-2022)</p>
  __EDA__
</div>
<div id="tab-no2" class="tab-content">
  <p class="section-title">Patrones temporales de NO₂ por estación</p>
  __NO2__
</div>
<div id="tab-mapas" class="tab-content">
  <p class="section-title">Representación geográfica</p>
  __MAPAS__
</div>
<script>
function showTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}
function showMap(name, btn) {
  document.querySelectorAll('.map-frame').forEach(f => f.classList.remove('active'));
  document.querySelectorAll('.map-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('map-' + name).classList.add('active');
  btn.classList.add('active');
}
</script>
</body>
</html>
"""

PENDING = '<div class="pending">Sección pendiente de generar — ejecuta las celdas correspondientes.</div>'

def render_dashboard():
    html = DASH_TEMPLATE
    html = html.replace('__EDA__',    DASH_BLOCKS['eda']    or PENDING)
    html = html.replace('__NO2__',    DASH_BLOCKS['no2']    or PENDING)
    html = html.replace('__MAPAS__',  DASH_BLOCKS['mapas']  or PENDING)
    out = f'{DASH_DIR}/index.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    return out

DASH_BLOCKS['eda'] = """
<div class="img-grid">
  <div class="img-card"><img src="img/fig_nulos_no2.png"/><p>Calidad de los datos: nulos por estación y año</p></div>
  <div class="img-card"><img src="img/fig_distribuciones.png"/><p>Distribución de NO₂ por estación con umbral OMS (40 μg/m³)</p></div>
</div>
"""

print('Dashboard inicializado en', render_dashboard())

# --- CELL ---
# Todas las estaciones: lineas finas semitransparentes + mediana gruesa por tipo
# Esto muestra variabilidad individual + patron por tipo con leyenda compacta.
cols_disp = [s for s in STATION_INFO if s in no2_clip.columns]
hourly = no2_clip[cols_disp].groupby(no2_clip.index.hour).mean()

fig, ax = plt.subplots(figsize=(12, 5))
# Lineas individuales (finas)
for s in cols_disp:
    ax.plot(hourly.index, hourly[s], lw=0.7, alpha=0.18, color=STATION_COLORS[s])
# Mediana por tipo (gruesa)
for tipo, color in TYPE_COLORS.items():
    cols_t = [s for s in cols_disp if STATION_INFO[s]['type'] == tipo]
    if not cols_t: continue
    med = hourly[cols_t].median(axis=1)
    ax.plot(hourly.index, med, lw=2.4, color=color, label=f'{tipo} (n={len(cols_t)})')
ax.axhline(40, color='green', ls='--', lw=1.4, alpha=0.8, label='OMS 40 \u03bcg/m\u00b3')
ax.set_title('NO\u2082 medio por hora del d\u00eda (2019-2022) — todas las estaciones', fontweight='bold')
ax.set_xlabel('Hora del d\u00eda'); ax.set_ylabel('NO\u2082 medio (\u03bcg/m\u00b3)')
ax.set_xticks(range(0, 24, 2)); ax.legend(loc='upper right', fontsize=8); ax.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(f'{DASH_DIR}/img/fig_no2_diario.png', bbox_inches='tight', dpi=160)
plt.show()


# --- CELL ---
# Todas las estaciones: lineas finas semitransparentes + mediana gruesa por tipo
# Esto muestra variabilidad individual + patron por tipo con leyenda compacta.
cols_disp = [s for s in STATION_INFO if s in no2_clip.columns]
DAYS = ['Lun','Mar','Mi\u00e9','Jue','Vie','S\u00e1b','Dom']
weekly = no2_clip[cols_disp].groupby(no2_clip.index.dayofweek).mean()

fig, ax = plt.subplots(figsize=(10, 5))
for s in cols_disp:
    ax.plot(weekly.index, weekly[s], lw=0.7, alpha=0.18, color=STATION_COLORS[s])
for tipo, color in TYPE_COLORS.items():
    cols_t = [s for s in cols_disp if STATION_INFO[s]['type'] == tipo]
    if not cols_t: continue
    ax.plot(weekly.index, weekly[cols_t].median(axis=1), lw=2.4, color=color, label=f'{tipo} (n={len(cols_t)})')
ax.axhline(40, color='green', ls='--', lw=1.4, alpha=0.8, label='OMS 40 \u03bcg/m\u00b3')
ax.set_title('NO\u2082 medio por d\u00eda de la semana (2019-2022)', fontweight='bold')
ax.set_xlabel('D\u00eda'); ax.set_ylabel('NO\u2082 medio (\u03bcg/m\u00b3)')
ax.set_xticks(range(7)); ax.set_xticklabels(DAYS)
ax.legend(loc='upper right', fontsize=8); ax.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(f'{DASH_DIR}/img/fig_no2_semanal.png', bbox_inches='tight', dpi=160)
plt.show()


# --- CELL ---
# Todas las estaciones: lineas finas semitransparentes + mediana gruesa por tipo
# Esto muestra variabilidad individual + patron por tipo con leyenda compacta.
cols_disp = [s for s in STATION_INFO if s in no2_clip.columns]
MONTHS = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
monthly = no2_clip[cols_disp].groupby(no2_clip.index.month).mean()

fig, ax = plt.subplots(figsize=(11, 5))
for s in cols_disp:
    ax.plot(monthly.index, monthly[s], lw=0.7, alpha=0.18, color=STATION_COLORS[s])
for tipo, color in TYPE_COLORS.items():
    cols_t = [s for s in cols_disp if STATION_INFO[s]['type'] == tipo]
    if not cols_t: continue
    ax.plot(monthly.index, monthly[cols_t].median(axis=1), lw=2.4, color=color, label=f'{tipo} (n={len(cols_t)})')
ax.axhline(40, color='green', ls='--', lw=1.4, alpha=0.8, label='OMS 40 \u03bcg/m\u00b3')
ax.set_title('NO\u2082 medio por mes (2019-2022)', fontweight='bold')
ax.set_xlabel('Mes'); ax.set_ylabel('NO\u2082 medio (\u03bcg/m\u00b3)')
ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS)
ax.legend(loc='upper right', fontsize=8); ax.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(f'{DASH_DIR}/img/fig_no2_mensual.png', bbox_inches='tight', dpi=160)
plt.show()


# --- CELL ---
# Todas las estaciones: lineas finas semitransparentes + mediana gruesa por tipo
# Esto muestra variabilidad individual + patron por tipo con leyenda compacta.
cols_disp = [s for s in STATION_INFO if s in no2_clip.columns]
yearly = no2_clip[cols_disp].resample('YE').mean()
yearly.index = yearly.index.year

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Panel izq: todas las lineas
for s in cols_disp:
    axes[0].plot(yearly.index, yearly[s], lw=0.8, alpha=0.25, color=STATION_COLORS[s])
for tipo, color in TYPE_COLORS.items():
    cols_t = [s for s in cols_disp if STATION_INFO[s]['type'] == tipo]
    if not cols_t: continue
    axes[0].plot(yearly.index, yearly[cols_t].median(axis=1), lw=2.6,
                 marker='o', ms=7, color=color, label=f'{tipo} (n={len(cols_t)})')
axes[0].axhline(40, color='green', ls='--', lw=1.4, alpha=0.8, label='OMS 40')
axes[0].set_title('Tendencia anual NO\u2082 (2019-2022)', fontweight='bold')
axes[0].set_xlabel('A\u00f1o'); axes[0].set_ylabel('NO\u2082 medio (\u03bcg/m\u00b3)')
axes[0].set_xticks(yearly.index)
axes[0].legend(fontsize=8); axes[0].grid(alpha=0.25)

# Panel dcha: boxplot todas las estaciones por año
yr_long = pd.melt(
    no2_clip[cols_disp].assign(year=no2_clip.index.year),
    id_vars='year', var_name='station', value_name='NO2'
)
yr_long = yr_long[yr_long['year'].isin(yearly.index)]
sns.boxplot(data=yr_long, x='year', y='NO2', ax=axes[1],
            color='#7aa6c2', showfliers=False, linewidth=0.8)
axes[1].axhline(40, color='green', ls='--', lw=1.4)
axes[1].set_title('Distribucion anual (todas las estaciones)', fontweight='bold')
axes[1].set_xlabel('A\u00f1o'); axes[1].set_ylabel('NO\u2082 (\u03bcg/m\u00b3)')
axes[1].grid(axis='y', alpha=0.25)

plt.suptitle('Evolucion anual del NO\u2082 — red LAQN Londres', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{DASH_DIR}/img/fig_no2_anual.png', bbox_inches='tight', dpi=160)
plt.show()


# --- CELL ---
cols_disp = [s for s in STATION_INFO if s in no2_clip.columns]

# Serie media por tipo de estacion: una observacion horaria por tipo.
type_hourly = {}
type_counts = {}
for tipo in TYPE_COLORS:
    cols_t = [s for s in cols_disp if STATION_INFO[s]['type'] == tipo]
    if not cols_t:
        continue
    type_hourly[tipo] = no2_clip[cols_t].mean(axis=1)
    type_counts[tipo] = len(cols_t)

# Descomposicion diaria por tipo. Se muestran componentes superpuestas por tipo
# para evitar una matriz demasiado densa en el dashboard.
decomp_by_type = {}
for tipo, serie in type_hourly.items():
    daily = serie.resample('D').mean().dropna()
    if len(daily) < 730:  # seasonal_decompose necesita al menos dos ciclos anuales.
        print(f'{tipo}: datos insuficientes para descomposicion anual')
        continue
    decomp_by_type[tipo] = seasonal_decompose(daily, model='additive', period=365)

component_specs = [
    ('observed', 'Serie observada', 'NO2 medio (ug/m3)'),
    ('trend', 'Tendencia anual', 'NO2 medio (ug/m3)'),
    ('seasonal', 'Patron estacional', 'Desviacion (ug/m3)'),
    ('resid', 'Residuo suavizado (media movil 14 dias)', 'Residuo (ug/m3)'),
]

fig, axes = plt.subplots(
    len(component_specs), 1,
    figsize=(14, 11),
    sharex=True,
    constrained_layout=True,
)
fig.patch.set_facecolor('white')

for ax, (attr, title, ylabel) in zip(axes, component_specs):
    for tipo, result in decomp_by_type.items():
        comp = getattr(result, attr)
        if attr == 'resid':
            comp = comp.rolling(14, center=True, min_periods=4).mean()
        ax.plot(
            comp.index, comp.values,
            color=TYPE_COLORS[tipo],
            lw=1.7 if attr != 'resid' else 1.2,
            alpha=0.9,
            label=f'{tipo} (n={type_counts[tipo]})',
        )
    ax.set_title(title, loc='left', fontsize=11, fontweight='bold', pad=6)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(axis='y', alpha=0.22)
    ax.grid(axis='x', alpha=0.08)
    ax.spines[['top', 'right']].set_visible(False)

axes[0].legend(
    loc='upper center',
    bbox_to_anchor=(0.5, 1.38),
    ncol=min(3, max(1, len(decomp_by_type))),
    frameon=False,
    fontsize=9,
)
axes[-1].set_xlabel('Fecha')
fig.suptitle(
    'Descomposicion estacional de NO2 por tipo de estacion',
    fontsize=15,
    fontweight='bold',
)
plt.savefig(f'{DASH_DIR}/img/fig_estacionalidad.png', bbox_inches='tight', dpi=170)
plt.show()

# Resumen: perfil horario medio por tipo.
fig, ax = plt.subplots(figsize=(13.5, 5.8), constrained_layout=True)
fig.patch.set_facecolor('white')

# Bandas sutiles para separar noche, manana, tarde y noche.
for x0, x1, color, alpha in [
    (0, 6, '#e5e7eb', 0.35),
    (6, 12, '#fef3c7', 0.28),
    (12, 18, '#dbeafe', 0.22),
    (18, 24, '#e5e7eb', 0.35),
]:
    ax.axvspan(x0, x1, color=color, alpha=alpha, lw=0)

for tipo, serie in type_hourly.items():
    hourly_mean = serie.groupby(serie.index.hour).mean()
    ax.plot(
        hourly_mean.index,
        hourly_mean.values,
        lw=2.6,
        color=TYPE_COLORS[tipo],
        marker='o',
        ms=5.5,
        label=f'{tipo} (n={type_counts[tipo]})',
    )

ax.axhline(40, color='#15803d', ls='--', lw=1.5, alpha=0.85, label='Referencia 40 ug/m3')
ax.set_title('Perfil horario medio de NO2 por tipo de estacion', loc='left', fontsize=13, fontweight='bold')
ax.set_xlabel('Hora del dia')
ax.set_ylabel('NO2 medio (ug/m3)')
ax.set_xlim(0, 23)
ax.set_xticks(range(0, 24, 2))
ax.grid(axis='y', alpha=0.24)
ax.spines[['top', 'right']].set_visible(False)
ax.legend(
    loc='upper center',
    bbox_to_anchor=(0.5, -0.18),
    ncol=min(3, max(1, len(type_hourly) + 1)),
    frameon=False,
    fontsize=9,
)
plt.savefig(f'{DASH_DIR}/img/fig_media_horaria_tipo.png', bbox_inches='tight', dpi=170)
plt.show()


# --- CELL ---
DASH_BLOCKS['no2'] = """
<div class="img-grid">
  <div class="img-card"><img src="img/fig_no2_diario.png"/><p>3.1 — NO₂ medio por hora del día</p></div>
  <div class="img-card"><img src="img/fig_no2_semanal.png"/><p>3.2 — NO₂ medio por día de la semana</p></div>
  <div class="img-card"><img src="img/fig_no2_mensual.png"/><p>3.3 — NO₂ medio por mes</p></div>
  <div class="img-card"><img src="img/fig_no2_anual.png"/><p>3.4 — NO₂ medio anual</p></div>
  <div class="img-card"><img src="img/fig_estacionalidad.png"/><p>3.5 — Descomposición estacional por tipo</p></div>
  <div class="img-card"><img src="img/fig_media_horaria_tipo.png"/><p>3.5 — Media horaria por tipo</p></div>
</div>
"""
print('Dashboard actualizado:', render_dashboard())

# --- CELL ---
estaciones_disp = [s for s in STATION_INFO if s in no2_clip.columns]
print(f'Estaciones en mapa: {len(estaciones_disp)}')

# Mapeo de TYPE_COLORS a colores de icono Folium
FOLIUM_ICON_COLORS = {
    'Kerbside':         'red',
    'Roadside':         'orange',
    'Urban Background': 'blue',
    'Suburban':         'green',
    'Industrial':       'purple',
}

mapa_estaciones = folium.Map(location=[51.505, -0.09], zoom_start=11,
                              tiles='cartodbpositron')

for s in estaciones_disp:
    info = STATION_INFO[s]
    icon_color = FOLIUM_ICON_COLORS.get(info['type'], 'gray')
    popup_html = (
        f'<b>{s}</b> &mdash; {info["name"]}<br>'
        f'Tipo: {info["type"]}<br>'
        f'Municipio: {info.get("authority", "")}'
    )
    folium.Marker(
        location=[info['lat'], info['lon']],
        popup=folium.Popup(popup_html, max_width=260),
        tooltip=f'{s} \u2014 {info["name"]} ({info["type"]})',
        icon=folium.Icon(color=icon_color, icon='map-marker', prefix='fa'),
    ).add_to(mapa_estaciones)

# Leyenda HTML
legend_html = '<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;padding:10px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.3);font-size:12px;">'
legend_html += '<b>Tipo de estaci\u00f3n</b><br>'
for tipo, color in FOLIUM_ICON_COLORS.items():
    if any(STATION_INFO[s]['type'] == tipo for s in estaciones_disp):
        legend_html += f'<i style="background:{TYPE_COLORS[tipo]};width:12px;height:12px;display:inline-block;border-radius:50%;margin-right:5px;"></i> {tipo}<br>'
legend_html += '</div>'
mapa_estaciones.get_root().html.add_child(folium.Element(legend_html))

mapa_estaciones.save(f'{DASH_DIR}/maps/mapa_estaciones.html')
mapa_estaciones


# --- CELL ---
mapa_cluster = folium.Map(location=[51.51, -0.12], zoom_start=11, tiles='cartodbpositron')

# Un cluster por tipo de transporte; cada parada (parent_station) aparece una vez.
cluster_bus   = MarkerCluster(name='Bus',   show=True).add_to(mapa_cluster)
cluster_metro = MarkerCluster(name='Metro', show=True).add_to(mapa_cluster)

ICONS = {
    'bus':   {'icon': 'bus',   'color': 'green'},
    'metro': {'icon': 'train', 'color': 'blue'},
}

for _, r in stops_pt.iterrows():
    style  = ICONS[r['transport']]
    target = cluster_bus if r['transport'] == 'bus' else cluster_metro
    folium.Marker(
        location=[r['stop_lat'], r['stop_lon']],
        icon=folium.Icon(icon=style['icon'], prefix='fa', color=style['color']),
        popup=f"{r['transport'].upper()} · {r['parent_station']} ({int(r['n_puntos'])} puntos)",
        tooltip=f"{r['transport'].upper()} · {r['parent_station']}",
    ).add_to(target)

folium.LayerControl(collapsed=False).add_to(mapa_cluster)
mapa_cluster.save(f'{DASH_DIR}/maps/mapa_cluster_paradas.html')
print(f'MarkerCluster (bus + metro) con {len(stops_pt):,} paradas '
      f'({len(stops_bus):,} bus, {len(stops_metro):,} metro) guardado.')
mapa_cluster


# --- CELL ---
H3_RES = 8

# Usa stops_pt (bus + metro, una fila por parent_station) — coherente con los
# mapas de cluster y de grafo. Cada parada cuenta una sola vez por hexágono.
stops_h3 = stops_pt[['stop_lat', 'stop_lon', 'transport']].copy()
stops_h3['count'] = 1
stops_h3 = stops_h3.h3.geo_to_h3(H3_RES, lat_col='stop_lat', lng_col='stop_lon')

idx_col = next(c for c in stops_h3.index.names + list(stops_h3.columns)
               if isinstance(c, str) and c.startswith('h3_'))

# Agregación: total + desglose por tipo de transporte (bus / metro)
if idx_col in stops_h3.columns:
    grouper = stops_h3.groupby(idx_col)
else:
    grouper = stops_h3.groupby(level=idx_col)

agg = grouper['count'].sum().to_frame()
agg['bus']   = grouper.apply(lambda g: int((g['transport'] == 'bus').sum()))
agg['metro'] = grouper.apply(lambda g: int((g['transport'] == 'metro').sum()))
agg.index.name = idx_col

mapa_h3 = folium.Map(location=[51.51, -0.12], zoom_start=11, tiles='cartodbpositron')

agg.h3.h3_to_geo_boundary().explore(
    column='count',
    cmap='YlOrRd',
    tooltip=['count', 'bus', 'metro'],
    popup=['count', 'bus', 'metro'],
    legend=True,
    style_kwds={'fillOpacity': 0.6, 'weight': 1, 'color': '#444'},
    m=mapa_h3,
)

mapa_h3.save(f'{DASH_DIR}/maps/mapa_h3.html')
print(f'Hexágonos H3 (res {H3_RES}) sobre {len(stops_pt):,} paradas '
      f'({len(stops_bus):,} bus + {len(stops_metro):,} metro) → '
      f'{len(agg)} celdas, mediana paradas/celda = {agg["count"].median():.0f}')
mapa_h3


# --- CELL ---
if 'stops_bus' not in dir() or 'stops_metro' not in dir():
    raise NameError('stops_bus / stops_metro no definidos: re-ejecuta la celda de carga de datos.')

def build_knn_graph(df, k=3):
    df = df.reset_index(drop=True)
    coords = np.radians(df[['stop_lat', 'stop_lon']].values)
    tree = BallTree(coords, metric='haversine')
    dist, idx = tree.query(coords, k=min(k + 1, len(df)))
    G = nx.Graph()
    ids = df['parent_station'].values
    for i, row in df.iterrows():
        G.add_node(ids[i], lat=float(row['stop_lat']), lon=float(row['stop_lon']))
    for i in range(len(df)):
        for j, d in zip(idx[i, 1:], dist[i, 1:]):
            G.add_edge(ids[i], ids[int(j)], km=float(d) * 6371.0)
    return G

def normalize(values):
    values = np.asarray(values, dtype=float)
    lo, hi = np.nanquantile(values, [0.05, 0.95])
    if not np.isfinite(hi - lo) or hi <= lo:
        hi = lo + 1.0
    return np.clip((values - lo) / (hi - lo), 0, 1), float(lo), float(hi)

def idw_at_points(target_coords, station_coords, station_values, k=6, power=2.0):
    valid = np.isfinite(station_values)
    coords = np.asarray(station_coords[valid], dtype=float)
    values = np.asarray(station_values[valid], dtype=float)
    tree = BallTree(np.radians(coords), metric='haversine')
    dist_rad, idx = tree.query(np.radians(np.asarray(target_coords, dtype=float)), k=min(k, len(values)))
    dist_km = np.maximum(dist_rad * 6371.0, 0.15)
    weights = 1.0 / (dist_km ** power)
    return (weights * values[idx]).sum(axis=1) / weights.sum(axis=1)

G_bus = build_knn_graph(stops_bus, k=3)
G_metro = build_knn_graph(stops_metro, k=3)
print(f'Grafo BUS  : {G_bus.number_of_nodes():>4d} nodos | {G_bus.number_of_edges():>5d} aristas')
print(f'Grafo METRO: {G_metro.number_of_nodes():>4d} nodos | {G_metro.number_of_edges():>5d} aristas')

cols_map = [s for s in STATION_INFO if s in no2_clip.columns]
weekly_no2 = no2_clip[cols_map].resample('W').mean()
print(f'Semanas: {len(weekly_no2)}, Estaciones: {len(cols_map)}')

st_lats = np.array([STATION_INFO[s]['lat'] for s in cols_map])
st_lons = np.array([STATION_INFO[s]['lon'] for s in cols_map])
st_coords = np.column_stack([st_lats, st_lons])

example_week = weekly_no2.index[len(weekly_no2) // 2]
vals = weekly_no2.loc[example_week, cols_map].values.astype(float)
valid = np.isfinite(vals)
weights, heat_lo, heat_hi = normalize(vals[valid])

combined = stops_pt.reset_index(drop=True).copy()
combined['no2_interp'] = idw_at_points(
    combined[['stop_lat', 'stop_lon']].values,
    st_coords,
    vals,
    k=6,
    power=2.0,
)

mapa_grafo = folium.Map(location=[51.51, -0.12], zoom_start=11, tiles='cartodbpositron')

colormap = cm_folium.LinearColormap(
    colors=['#2563eb', '#22c55e', '#facc15', '#f97316', '#dc2626'],
    vmin=heat_lo,
    vmax=heat_hi,
    caption=f'NO2 medido en estaciones LAQN (ug/m3), escala p5-p95 - semana {example_week.strftime("%Y-%m-%d")}'
)
colormap.add_to(mapa_grafo)

# Heatmap real de contaminacion: se dibuja primero para que el grafo quede encima.
heat_data = [
    [float(lat), float(lon), float(w)]
    for lat, lon, w in zip(st_lats[valid], st_lons[valid], weights)
]
HeatMap(
    heat_data,
    radius=42,
    blur=36,
    min_opacity=0.16,
    max_zoom=13,
    gradient={
        0.00: '#2563eb',
        0.35: '#22c55e',
        0.60: '#facc15',
        0.80: '#f97316',
        1.00: '#dc2626',
    },
    name=f'Heatmap NO2 LAQN (semana {example_week.strftime("%Y-%m-%d")})',
).add_to(mapa_grafo)

STYLES = {
    'bus': {'edge': '#047857', 'fill': '#10b981', 'border': '#ffffff'},
    'metro': {'edge': '#1d4ed8', 'fill': '#60a5fa', 'border': '#ffffff'},
}

def render_graph(G, tipo, mapa, stop_df):
    s = STYLES[tipo]
    fg = folium.FeatureGroup(name=f'Grafo {tipo}', show=True)
    for u, v, attrs in G.edges(data=True):
        a, b = G.nodes[u], G.nodes[v]
        edge = [(a['lat'], a['lon']), (b['lat'], b['lon'])]
        folium.PolyLine(edge, color='#ffffff', weight=5.0, opacity=0.90).add_to(fg)
        folium.PolyLine(
            edge,
            color=s['edge'],
            weight=2.8,
            opacity=1.0,
            tooltip=f'{tipo}: {attrs["km"]:.2f} km',
        ).add_to(fg)

    tipo_stops = stop_df[stop_df['transport'] == tipo]
    stop_no2_map = dict(zip(tipo_stops['parent_station'], tipo_stops['no2_interp']))
    for n, attr in G.nodes(data=True):
        no2_val = stop_no2_map.get(n, float('nan'))
        popup_txt = (f'<b>{tipo.upper()} - {n}</b><br>'
                     f'Grado: {G.degree[n]}<br>'
                     f'NO2 estimado: <b>{no2_val:.1f} ug/m3</b>')
        folium.CircleMarker(
            [attr['lat'], attr['lon']],
            radius=3.5,
            color=s['border'],
            weight=1.2,
            fill=True,
            fill_color=s['fill'],
            fill_opacity=0.95,
            popup=folium.Popup(popup_txt, max_width=220),
            tooltip=f'{tipo} | {n} | NO2: {no2_val:.1f}',
        ).add_to(fg)
    fg.add_to(mapa)

render_graph(G_bus, 'bus', mapa_grafo, combined)
render_graph(G_metro, 'metro', mapa_grafo, combined)

fg_laqn = folium.FeatureGroup(name='Estaciones LAQN', show=True)
for s, val in zip(np.array(cols_map)[valid], vals[valid]):
    info = STATION_INFO[s]
    folium.CircleMarker(
        [info['lat'], info['lon']],
        radius=7,
        color='#7f1d1d',
        weight=1.8,
        fill=True,
        fill_color=colormap(float(np.clip(val, heat_lo, heat_hi))),
        fill_opacity=0.95,
        popup=f'<b>LAQN {s}</b><br>{info["name"]}<br>NO2 medido: {val:.1f} ug/m3',
        tooltip=f'LAQN {s}: {val:.1f} ug/m3',
    ).add_to(fg_laqn)
fg_laqn.add_to(mapa_grafo)

folium.LayerControl(collapsed=False).add_to(mapa_grafo)
mapa_grafo.save(f'{DASH_DIR}/maps/mapa_grafo.html')

# Datos semanales para posibles controles del dashboard: estaciones LAQN ponderadas.
slider_dir = f'{DASH_DIR}/maps/weekly_data'
os.makedirs(slider_dir, exist_ok=True)
saved = 0
for week_date in weekly_no2.index:
    vals_w = weekly_no2.loc[week_date, cols_map].values.astype(float)
    valid_w = np.isfinite(vals_w)
    if valid_w.sum() < 3:
        continue
    weights_w, _, _ = normalize(vals_w[valid_w])
    week_data = [
        [float(lat), float(lon), float(w)]
        for lat, lon, w in zip(st_lats[valid_w], st_lons[valid_w], weights_w)
    ]
    with open(f'{slider_dir}/{week_date.strftime("%Y-%m-%d")}.json', 'w', encoding='utf-8') as f:
        json.dump(week_data, f)
    saved += 1

print(f'Datos semanales calor guardados en {slider_dir}: {saved} archivos')
print(f'Mapa ejemplo: semana {example_week.strftime("%Y-%m-%d")}')
mapa_grafo


# --- CELL ---
import folium

def generar_mapa_25_rutas_colores(df_b):
    print("Generando mapa detallado de las 25 rutas principales...")
    m_bus = folium.Map(location=[51.5074, -0.1278], zoom_start=13, tiles='cartodbpositron')
    
    # Lista de las 25 líneas seleccionadas
    top_25_lines = [
        '9', '11', '14', '15', '24', '38', '73', '139', '159', 'RV1', 
        '18', '25', '29', '36', '52', '74', '88', '94', '98', '148', 
        '205', '211', '390', '453', 'C2'
    ]

    # Paleta de 25 colores variados para que cada ruta sea distinta
    colores_hex = [
        '#E31837', '#00A4A7', '#F3A9BB', '#FFD300', '#00782A', '#9B0056', '#003688', '#0098D4', '#95CDBA', '#B36305',
        '#A0A5A9', '#EE7C0E', '#84B817', '#E21836', '#001155', '#552200', '#225500', '#005522', '#550022', '#111111',
        '#777777', '#AA3333', '#33AA33', '#3333AA', '#AAAA33'
    ]
    
    # Diccionario para asignar un color a cada línea
    asignacion_colores = {linea: colores_hex[i] for i, linea in enumerate(top_25_lines)}

    for linea in top_25_lines:
        # Filtrar datos solo de esta línea
        df_ruta = df_b[df_b['Linea'] == linea].sort_values('Orden')
        
        if not df_ruta.empty:
            color_actual = asignacion_colores[linea]
            puntos_ruta = list(zip(df_ruta['Lat'], df_ruta['Lon']))
            
            # 1. Crear un FeatureGroup por cada línea para poder encenderlas/apagarlas
            capa_linea = folium.FeatureGroup(name=f"Bus {linea}")
            
            # 2. Dibujar el Grafo (Línea)
            folium.PolyLine(
                puntos_ruta, 
                color=color_actual, 
                weight=4, 
                opacity=0.8,
                tooltip=f"Línea de Bus: {linea}"
            ).add_to(capa_linea)
            
            # 3. Dibujar las Paradas de esta línea específica con Markers
            for _, row in df_ruta.iterrows():
                folium.CircleMarker(
                    location=[row['Lat'], row['Lon']],
                    radius=5,
                    color=color_actual,
                    fill=True,
                    fill_color=color_actual,
                    fill_opacity=0.9,
                    popup=f"Línea {linea} - Parada: {row['Nombre_Parada']}"
                ).add_to(capa_linea)
            
            capa_linea.add_to(m_bus)

    folium.LayerControl().add_to(m_bus)
    return m_bus

# Ejecución
mapa_buses_pro = generar_mapa_25_rutas_colores(df_bus)
mapa_buses_pro

# --- CELL ---
def generar_mapa_metro(df_m):
    print("Generando mapa de metro...")
    m_metro = folium.Map(location=[51.5074, -0.1278], zoom_start=12, tiles='cartodbpositron')

    capa_metro = folium.FeatureGroup(name="Metro de Londres")
    
    # Diccionario de colores oficiales (puedes añadir más líneas)
    colores_tfl = {
        'Northern': 'black', 'Central': 'red', 'Victoria': '#0098D4', 
        'Piccadilly': '#003688', 'District': '#00782A', 'Jubilee': '#A0A5A9'
    }

    for linea in df_m['Linea'].unique():
        df_linea = df_m[df_m['Linea'] == linea].sort_values('Orden')
        puntos = list(zip(df_linea['Lat'], df_linea['Lon']))
        color_linea = colores_tfl.get(linea, 'purple')
        
        # 1. Dibujamos la línea que une las estaciones
        folium.PolyLine(
            puntos, 
            color=color_linea, 
            weight=5, 
            opacity=0.8,
            tooltip=f"Línea {linea}"
        ).add_to(capa_metro)
        
        # 2. Dibujamos los marcadores de las estaciones
        for _, row in df_linea.iterrows():
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=f"Estación: {row['Estacion']} ({linea})",
                icon=folium.Icon(color='white', icon_color=color_linea, icon='subway', prefix='fa')
            ).add_to(capa_metro)

    capa_metro.add_to(m_metro)
    return m_metro

# Ejecución
mapa_solo_metro = generar_mapa_metro(df_metro)
mapa_solo_metro

# --- CELL ---
DASH_BLOCKS['mapas'] = """
<div class="map-selector">
  <button class="map-btn active" onclick="showMap('estaciones',this)">4.1 Estaciones LAQN</button>
  <button class="map-btn"        onclick="showMap('cluster',this)">4.2 Cluster paradas</button>
  <button class="map-btn"        onclick="showMap('h3',this)">4.3 Hexágonos H3</button>
  <button class="map-btn"        onclick="showMap('grafo',this)">4.4 Grafo + HeatMap NO2</button>
</div>
<div id="map-estaciones" class="map-frame active"><iframe src="maps/mapa_estaciones.html"></iframe></div>
<div id="map-cluster"    class="map-frame"       ><iframe src="maps/mapa_cluster_paradas.html"></iframe></div>
<div id="map-h3"         class="map-frame"       ><iframe src="maps/mapa_h3.html"></iframe></div>
<div id="map-grafo"      class="map-frame"       ><iframe src="maps/mapa_grafo.html"></iframe></div>
"""
print('Dashboard actualizado:', render_dashboard())

# --- CELL ---
GROQ_API_KEY = os.getenv('GROQ_API_KEY', 'PEGA_AQUI_TU_API_KEY')
GROQ_MODEL = 'llama-3.1-8b-instant'

def normalizar_texto(txt):
    txt = str(txt).lower().strip()
    txt = re.sub(r'[^a-z0-9\s/-]+', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()

def construir_busqueda_paradas():
    bus_lookup = routes_bus[['Linea', 'Orden', 'Nombre_Parada', 'Lat', 'Lon']].copy()
    bus_lookup['modo'] = 'bus'
    bus_lookup['nombre'] = bus_lookup['Nombre_Parada'].fillna('').astype(str)

    metro_names = routes_metro['Estacion'].fillna('').astype(str).str.strip()
    metro_lookup = routes_metro[['Linea', 'Orden', 'ID_Estacion', 'Lat', 'Lon']].copy()
    metro_lookup['modo'] = 'metro'
    metro_lookup['nombre'] = np.where(metro_names.ne(''), metro_names, metro_lookup['ID_Estacion'].astype(str))

    lookup = pd.concat(
        [
            bus_lookup[['modo', 'Linea', 'Orden', 'nombre', 'Lat', 'Lon']],
            metro_lookup[['modo', 'Linea', 'Orden', 'nombre', 'Lat', 'Lon']],
        ],
        ignore_index=True,
    ).dropna(subset=['Lat', 'Lon'])
    lookup['nombre_norm'] = lookup['nombre'].map(normalizar_texto)
    return lookup[lookup['nombre_norm'].ne('')].reset_index(drop=True)

ROUTE_STOP_LOOKUP = construir_busqueda_paradas()

def score_lugar(query_norm, nombre_norm):
    q_tokens = set(query_norm.split())
    n_tokens = set(nombre_norm.split())
    overlap = len(q_tokens & n_tokens) / max(len(q_tokens), 1)
    substring = 1.0 if query_norm in nombre_norm or nombre_norm in query_norm else 0.0
    similaridad = SequenceMatcher(None, query_norm, nombre_norm).ratio()
    return 0.45 * overlap + 0.35 * substring + 0.20 * similaridad

def localizar_lugar_en_rutas(nombre, min_score=0.30):
    """Busca el lugar escrito por el agente en las paradas reales del dataset de rutas."""
    query_norm = normalizar_texto(nombre)
    if not query_norm:
        raise ValueError('El origen o destino está vacío.')

    candidatos = ROUTE_STOP_LOOKUP.copy()
    candidatos['score'] = candidatos['nombre_norm'].map(lambda x: score_lugar(query_norm, x))
    candidatos = candidatos.sort_values('score', ascending=False).head(8)
    mejor = candidatos.iloc[0]
    if float(mejor['score']) < min_score:
        raise ValueError(
            f'No encontré "{nombre}" en las paradas del dataset. '
            f'Prueba con un nombre de parada o zona más específico.'
        )
    return {
        'texto': nombre,
        'nombre_match': mejor['nombre'],
        'coords': (float(mejor['Lat']), float(mejor['Lon'])),
        'modo_match': mejor['modo'],
        'linea_match': mejor['Linea'],
        'score': float(mejor['score']),
        'candidatos': candidatos[['modo', 'Linea', 'nombre', 'Lat', 'Lon', 'score']],
    }

def extraer_origen_destino_groq(consulta, api_key=None):
    """Extrae origen y destino con Groq. Devuelve dos textos que luego se buscan en el dataset."""
    api_key = api_key or GROQ_API_KEY
    if not api_key or api_key == 'PEGA_AQUI_TU_API_KEY':
        raise ValueError('Configura GROQ_API_KEY antes de llamar al agente ECO.')
    client = Groq(api_key=api_key, timeout=20.0)
    res = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                'role': 'system',
                'content': (
                    'Extrae origen y destino de una consulta de movilidad en Londres. '
                    'Responde solo JSON válido con las claves "origen" y "destino". '
                    'No añadas explicación.'
                ),
            },
            {'role': 'user', 'content': consulta},
        ],
        temperature=0,
    )
    data = json.loads(res.choices[0].message.content)
    return str(data['origen']).strip(), str(data['destino']).strip()

def distancia_haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))

# Modelo local de contaminación: estima NO2 por proximidad a estaciones LAQN.
cols_agent = [s for s in STATION_INFO if s in no2_clip.columns]
weekly_agent = no2_clip[cols_agent].resample('W').mean()
agent_week = weekly_agent.index[len(weekly_agent) // 2]
station_values_agent = weekly_agent.loc[agent_week, cols_agent].values.astype(float)
valid_station_agent = np.isfinite(station_values_agent)
station_coords_agent = np.array([[STATION_INFO[s]['lat'], STATION_INFO[s]['lon']] for s in cols_agent], dtype=float)
station_tree_agent = BallTree(np.radians(station_coords_agent[valid_station_agent]), metric='haversine')
station_values_valid_agent = station_values_agent[valid_station_agent]

def estimar_no2_en_coords(coords, k=4, power=2.0):
    coords = np.asarray(coords, dtype=float)
    dist_rad, idx = station_tree_agent.query(np.radians(coords), k=min(k, len(station_values_valid_agent)))
    dist_km = np.maximum(dist_rad * 6371.0, 0.20)
    pesos = 1.0 / (dist_km ** power)
    return (pesos * station_values_valid_agent[idx]).sum(axis=1) / pesos.sum(axis=1)

def preparar_rutas_por_modo():
    bus = routes_bus[['Linea', 'Orden', 'Nombre_Parada', 'Lat', 'Lon']].copy()
    bus['modo'] = 'bus'
    bus['nombre'] = bus['Nombre_Parada'].fillna('').astype(str)

    metro_names = routes_metro['Estacion'].fillna('').astype(str).str.strip()
    metro = routes_metro[['Linea', 'Orden', 'ID_Estacion', 'Lat', 'Lon']].copy()
    metro['modo'] = 'metro'
    metro['nombre'] = np.where(metro_names.ne(''), metro_names, metro['ID_Estacion'].astype(str))

    return {
        'bus': bus[['modo', 'Linea', 'Orden', 'nombre', 'Lat', 'Lon']].dropna(subset=['Lat', 'Lon']),
        'metro': metro[['modo', 'Linea', 'Orden', 'nombre', 'Lat', 'Lon']].dropna(subset=['Lat', 'Lon']),
    }

ROUTES_BY_MODE = preparar_rutas_por_modo()

def tool_buscar_rutas_eco(origen_coords, destino_coords, radio_km=1.5, max_rutas=10):
    """Tool local: busca rutas viables y calcula la exposición media a NO2 de cada tramo."""
    candidatas = []
    o_lat, o_lon = origen_coords
    d_lat, d_lon = destino_coords

    for modo, df_modo in ROUTES_BY_MODE.items():
        for linea, ruta in df_modo.groupby('Linea'):
            ruta = ruta.sort_values('Orden').reset_index(drop=True)
            dist_origen = distancia_haversine_km(o_lat, o_lon, ruta['Lat'].values, ruta['Lon'].values)
            dist_destino = distancia_haversine_km(d_lat, d_lon, ruta['Lat'].values, ruta['Lon'].values)
            idx_origen = np.where(dist_origen <= radio_km)[0]
            idx_destino = np.where(dist_destino <= radio_km)[0]
            if len(idx_origen) == 0 or len(idx_destino) == 0:
                continue

            pares = []
            for i in idx_origen:
                for j in idx_destino:
                    if i == j:
                        continue
                    accesos = float(dist_origen[i] + dist_destino[j])
                    saltos = abs(int(j) - int(i))
                    pares.append((saltos + accesos, int(i), int(j), accesos))
            if not pares:
                continue

            _, i, j, accesos = min(pares, key=lambda x: x[0])
            ini, fin = sorted([i, j])
            tramo = ruta.iloc[ini:fin + 1].copy()
            coords_tramo = tramo[['Lat', 'Lon']].to_numpy(dtype=float)
            if len(coords_tramo) < 2:
                continue

            no2_tramo = estimar_no2_en_coords(coords_tramo)
            distancia_tramo = distancia_haversine_km(
                coords_tramo[:-1, 0], coords_tramo[:-1, 1], coords_tramo[1:, 0], coords_tramo[1:, 1]
            ).sum()
            candidatas.append({
                'modo': modo,
                'linea': str(linea),
                'parada_origen': ruta.loc[i, 'nombre'],
                'parada_destino': ruta.loc[j, 'nombre'],
                'n_paradas': int(len(tramo)),
                'distancia_km': float(distancia_tramo),
                'acceso_km': accesos,
                'no2_medio': float(np.mean(no2_tramo)),
                'no2_max': float(np.max(no2_tramo)),
                'geometry': [(float(lat), float(lon)) for lat, lon in coords_tramo],
            })

    if not candidatas:
        return pd.DataFrame()
    rutas = pd.DataFrame(candidatas).sort_values(['no2_medio', 'acceso_km', 'distancia_km']).head(max_rutas)
    return rutas.reset_index(drop=True)

def crear_mapa_ruta_eco(origen_info, destino_info, rutas, filename=f'{DASH_DIR}/maps/mapa_agente_eco.html'):
    if rutas.empty:
        return None

    centro = [
        (origen_info['coords'][0] + destino_info['coords'][0]) / 2,
        (origen_info['coords'][1] + destino_info['coords'][1]) / 2,
    ]
    mapa = folium.Map(location=centro, zoom_start=12, tiles='cartodbpositron')
    folium.Marker(origen_info['coords'], tooltip='Origen', popup=f"Origen: {origen_info['nombre_match']}").add_to(mapa)
    folium.Marker(destino_info['coords'], tooltip='Destino', popup=f"Destino: {destino_info['nombre_match']}").add_to(mapa)

    for idx, row in rutas.iterrows():
        es_eco = idx == 0
        color = '#16a34a' if es_eco else '#64748b'
        peso = 6 if es_eco else 3
        opacidad = 0.92 if es_eco else 0.55
        folium.PolyLine(
            row['geometry'],
            color=color,
            weight=peso,
            opacity=opacidad,
            tooltip=(
                f"{'Ruta ECO' if es_eco else 'Ruta viable'} | {row['modo']} {row['linea']} | "
                f"NO2 medio {row['no2_medio']:.1f} ug/m3"
            ),
        ).add_to(mapa)

    mapa.save(filename)
    return mapa

def agente_eco_rutas(consulta, radio_km=1.5, api_key=None):
    """Agente ECO: consulta en lenguaje natural -> respuesta textual + tabla + mapa."""
    origen_txt, destino_txt = extraer_origen_destino_groq(consulta, api_key=api_key)
    origen_info = localizar_lugar_en_rutas(origen_txt)
    destino_info = localizar_lugar_en_rutas(destino_txt)
    rutas = tool_buscar_rutas_eco(origen_info['coords'], destino_info['coords'], radio_km=radio_km)

    if rutas.empty:
        respuesta = (
            'No encuentro una ruta ECO viable en transporte público con los datos disponibles.\n\n'
            f'- Origen interpretado: {origen_txt} -> {origen_info["nombre_match"]}.\n'
            f'- Destino interpretado: {destino_txt} -> {destino_info["nombre_match"]}.\n'
            f'- Criterio usado: líneas que pasen a menos de {radio_km:.1f} km del origen y del destino.\n\n'
            'Conclusión: para este trayecto, según este dataset, no hay una alternativa clara de transporte público; '
            'el coche es la opción recomendada si necesitas hacer el desplazamiento.'
        )
        return respuesta, rutas, None

    ruta_eco = rutas.iloc[0]
    mapa = crear_mapa_ruta_eco(origen_info, destino_info, rutas)
    tabla = rutas.drop(columns=['geometry']).copy()
    respuesta = (
        'Ruta ECO recomendada en transporte público.\n\n'
        f'- Súbete en: {ruta_eco["parada_origen"]}.\n'
        f'- Línea: {ruta_eco["modo"].upper()} {ruta_eco["linea"]}.\n'
        f'- Bájate en: {ruta_eco["parada_destino"]}.\n'
        f'- Paradas aproximadas del tramo: {int(ruta_eco["n_paradas"])}.\n'
        f'- Distancia estimada del tramo: {ruta_eco["distancia_km"]:.2f} km.\n'
        f'- NO2 medio estimado atravesado: {ruta_eco["no2_medio"]:.1f} ug/m3 '
        f'(máximo: {ruta_eco["no2_max"]:.1f} ug/m3).\n\n'
        f'He interpretado el origen como "{origen_info["nombre_match"]}" '
        f'y el destino como "{destino_info["nombre_match"]}". '
        'Entre las rutas viables encontradas, esta es la que atraviesa menor contaminación media estimada.'
    )
    return respuesta, tabla, mapa


# --- CELL ---
casos_prueba_agente = {
    'transporte_publico_eco': 'Quiero ir de Royal Free Hospital a Aldwych',
    'coche_recomendado': 'Quiero ir de Heathrow Central Bus Station a Epping Forest College',
}

for nombre_caso, consulta in casos_prueba_agente.items():
    print('=' * 80)
    print(f'CASO: {nombre_caso.upper()}')
    print(f'Consulta del usuario: {consulta}')

    respuesta_agente, rutas_resultado, mapa_resultado = agente_eco_rutas(consulta, radio_km=1.5)

    print()
    print('RESPUESTA DEL AGENTE')
    print('-' * 80)
    print(respuesta_agente)

    if not rutas_resultado.empty:
        print()
        print('Rutas candidatas ordenadas por menor contaminación media estimada:')
        display(rutas_resultado.head(3))
        display(mapa_resultado)


# --- CELL ---
ruta = render_dashboard()
print(f'Dashboard final escrito en: {os.path.abspath(ruta)}')
print(f'\nBloques activos:')
for k, v in DASH_BLOCKS.items():
    estado = 'OK' if v else 'pendiente'
    print(f'  {k:8s} → {estado}')

# --- CELL ---

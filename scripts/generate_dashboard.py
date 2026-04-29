"""
Genera dashboard/index.html con los resultados del análisis de Londres.
Se llama desde el notebook con: exec(open('scripts/generate_dashboard.py').read())
Requiere que las variables globales del notebook estén definidas.
"""

import os, re
import pandas as pd
import numpy as np

# ── Tabla de estaciones ──────────────────────────────────────────────────────
tabla_rows = []
for _s, _info in STATION_INFO.items():
    _dists = haversine(_info['lat'], _info['lon'],
                       stops['stop_lat'].values, stops['stop_lon'].values)
    tabla_rows.append({
        'Estación':            _s,
        'Nombre / Ubicación':  _info['name'],
        'Tipo':                _info['type'],
        'NO2 medio (μg/m³)':  round(float(no2_filled[_s].mean()), 2),
        'Excede OMS (40)':     'Sí' if no2_filled[_s].mean() > 40 else 'No',
        'Paradas TfL ≤500m':   int((_dists <= 500).sum()),
        'Dist. parada más cercana (m)': int(_dists.min()),
    })

df_tabla = (pd.DataFrame(tabla_rows)
            .sort_values('NO2 medio (μg/m³)', ascending=False))
display(df_tabla)

tabla_html = df_tabla.to_html(
    index=False, classes='dataframe data-table', border=0)

# ── KPIs ─────────────────────────────────────────────────────────────────────
avg_no2_val = round(float(no2_filled.mean().mean()), 1)
n_tfl_val   = len(stops)
gp_r2_str   = f'{r2_gp:.3f}'
ic_str      = f'{ic_pct:.1f}%'
xgb_mae_str = f'{xgb_mae:.3f}'
xgb_r2_str  = f'{xgb_r2:.4f}'

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = (
    ':root{--p-dark:#0b3b17;--p-green:#1a823b;--l-green:#8cc63f;--a-org:#f58f2a;'
    '--a-teal:#1eae98;--bg:#f8faf5;--card:#fff;--t-dark:#2e211a;--t-mut:#6b5c52;--border:#d6d1c4}'
    '*{box-sizing:border-box;margin:0;padding:0}'
    'body{font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:linear-gradient(rgba(248,250,245,0.35),rgba(248,250,245,0.35)),url("img/London.jpg") no-repeat center center fixed;background-size:cover;color:var(--t-dark);line-height:1.6}'
    'header{background: url("img/Cabecera.jpg") no-repeat center center / cover, linear-gradient(rgba(30,174,152,0.35), rgba(30,174,152,0.35));color:#fff;padding:2.5rem 3rem;'
    'box-shadow:0 4px 12px rgba(11,59,23,.2);position:relative;overflow:hidden}'
    'header::after{content:"";position:absolute;top:0;right:0;bottom:0;width:40%;'
    'background:linear-gradient(to left,rgba(245,143,42,.1),transparent);pointer-events:none}'
    'header h1{font-size:2rem;margin-bottom:.5rem;font-weight:700;letter-spacing:-.5px}'
    'header p{opacity:.9;font-size:1rem;color:#eaf0e6}'
    '.tab-bar{display:flex;background:var(--card);border-bottom:1px solid var(--border);'
    'padding:0 2.5rem;box-shadow:0 2px 10px rgba(0,0,0,.04);position:sticky;top:0;z-index:100}'
    '.tab-btn{padding:1.2rem 1.5rem;border:none;background:none;cursor:pointer;font-size:1rem;'
    'color:var(--t-mut);border-bottom:3px solid transparent;transition:all .3s ease;font-weight:500;position:relative}'
    '.tab-btn:hover{color:var(--p-green);background:rgba(140,198,63,.1)}'
    '.tab-btn.active{color:var(--p-dark);border-bottom-color:var(--p-green);font-weight:600}'
    '@keyframes slideUp{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}'
    '.tab-content{display:none;padding:2.5rem 3rem;animation:slideUp .4s ease-out forwards}'
    '.tab-content.active{display:block}'
    '.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1.5rem;margin-bottom:2.5rem}'
    '.kpi{background:var(--card);border-radius:12px;padding:1.8rem 1.5rem;text-align:center;'
    'box-shadow:0 4px 15px rgba(0,0,0,.04);border-top:4px solid var(--p-green);'
    'transition:transform .3s ease,box-shadow .3s ease;position:relative;overflow:hidden}'
    '.kpi::before{content:"";position:absolute;top:0;left:0;width:100%;height:100%;'
    'background:linear-gradient(180deg,rgba(140,198,63,.05) 0%,transparent 50%);opacity:0;transition:opacity .3s}'
    '.kpi:hover{transform:translateY(-5px);box-shadow:0 8px 25px rgba(11,59,23,.1)}'
    '.kpi:hover::before{opacity:1}'
    '.kpi .valor{font-size:2.2rem;font-weight:700;color:var(--p-dark);line-height:1.2}'
    '.kpi .label{font-size:.85rem;color:var(--t-mut);margin-top:.6rem;text-transform:uppercase;letter-spacing:.5px;font-weight:600}'
    '.img-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(450px,1fr));gap:2rem;margin-top:1.5rem}'
    '.img-card{background:var(--card);border-radius:12px;padding:1.2rem;box-shadow:0 4px 15px rgba(0,0,0,.04);transition:transform .3s ease}'
    '.img-card:hover{transform:scale(1.01)}'
    '.img-card img{width:100%;border-radius:8px;display:block}'
    '.img-card p{font-size:.9rem;color:var(--t-mut);margin-top:.8rem;text-align:center;font-weight:500}'
    '.map-selector{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1.5rem}'
    '.map-btn{padding:.6rem 1.2rem;border:2px solid var(--p-green);border-radius:30px;background:var(--card);'
    'cursor:pointer;font-size:.9rem;color:var(--p-green);font-weight:600;transition:all .3s ease;box-shadow:0 2px 5px rgba(0,0,0,.05)}'
    '.map-btn:hover{background:rgba(26,130,59,.1);transform:translateY(-2px)}'
    '.map-btn.active{background:var(--p-green);color:#fff;box-shadow:0 4px 10px rgba(26,130,59,.3)}'
    '@keyframes fadeIn{from{opacity:0}to{opacity:1}}'
    '.map-frame{display:none;border-radius:12px;overflow:hidden;box-shadow:0 6px 20px rgba(0,0,0,.08);background:#fff;border:1px solid #eee}'
    '.map-frame.active{display:block;animation:fadeIn .5s ease-in}'
    '.map-frame iframe{width:100%;height:600px;border:none;display:block}'
    '.data-table{width:100%;border-collapse:separate;border-spacing:0;background:var(--card);border-radius:12px;'
    'overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,.04);margin-top:1rem}'
    '.data-table th{background:var(--p-dark);color:#fff;padding:1rem 1.2rem;text-align:left;font-size:.9rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px}'
    '.data-table td{padding:.8rem 1.2rem;border-bottom:1px solid var(--border);font-size:.95rem;color:var(--t-dark)}'
    '.data-table tr:last-child td{border-bottom:none}'
    '.data-table tr{transition:background .2s}'
    '.data-table tr:hover td{background:rgba(140,198,63,.08)}'
    '#filtro{padding:.8rem 1.2rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;font-size:1rem;width:100%;max-width:400px;transition:all .3s;outline:none;background:var(--card)}'
    '#filtro:focus{border-color:var(--p-green);box-shadow:0 0 0 3px rgba(26,130,59,.2)}'
    '.section-title{font-size:1.3rem;font-weight:700;color:var(--p-dark);margin-bottom:1.5rem;display:flex;align-items:center;gap:10px}'
    '.section-title::before{content:"";display:inline-block;width:6px;height:24px;background:var(--a-org);border-radius:3px}'
)

JS = (
    '<script>'
    "function showTab(n,b){"
    "document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));"
    "document.querySelectorAll('.tab-btn').forEach(b2=>b2.classList.remove('active'));"
    "document.getElementById('tab-'+n).classList.add('active');"
    "b.classList.add('active');}"
    "function showMap(n,b){"
    "document.querySelectorAll('.map-frame').forEach(f=>f.classList.remove('active'));"
    "document.querySelectorAll('.map-btn').forEach(b2=>b2.classList.remove('active'));"
    "document.getElementById('map-'+n).classList.add('active');"
    "b.classList.add('active');}"
    "function filtrarTabla(){"
    "var inp=document.getElementById('filtro').value.toLowerCase();"
    "document.querySelectorAll('.data-table tbody tr').forEach(function(r){"
    "r.style.display=r.textContent.toLowerCase().includes(inp)?'':'none';});}"
    '</script>'
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def kpi(valor, label):
    return ('<div class="kpi">'
            + '<div class="valor">' + str(valor) + '</div>'
            + '<div class="label">' + label + '</div>'
            + '</div>')

def img_card(src, caption):
    return ('<div class="img-card">'
            + '<img src="' + src + '"/>'
            + '<p>' + caption + '</p>'
            + '</div>')

def tab_btn(name, label, active=False):
    cls = 'tab-btn active' if active else 'tab-btn'
    return ('<button class="' + cls + '" '
            + "onclick=\"showTab('" + name + "',this)\">"
            + label + '</button>')

def map_btn(name, label, active=False):
    cls = 'map-btn active' if active else 'map-btn'
    return ('<button class="' + cls + '" '
            + "onclick=\"showMap('" + name + "',this)\">"
            + label + '</button>')

def map_frame(map_id, src_file, active=False):
    cls = 'map-frame active' if active else 'map-frame'
    return ('<div id="map-' + map_id + '" class="' + cls + '">'
            + '<iframe src="maps/' + src_file + '"></iframe>'
            + '</div>')

# ── Construir HTML ────────────────────────────────────────────────────────────
parts = []

# Head
parts.append('<!DOCTYPE html>')
parts.append('<html lang="es">')
parts.append('<head>')
parts.append('<meta charset="UTF-8"/>')
parts.append('<meta name="viewport" content="width=device-width,initial-scale=1.0"/>')
parts.append('<title>Movilidad y sostenibilidad ambiental en Londres</title>')
parts.append('<style>' + CSS + '</style>')
parts.append('</head>')
parts.append('<body>')

# Header
parts.append('<header>')
parts.append('<h1>Movilidad y sostenibilidad ambiental en Londres</h1>')
parts.append('<p>Trabajo final &middot; Ciudades Inteligentes &middot; UC3M &middot; Mayo 2026</p>')
parts.append('<p style="margin-top:.35rem;opacity:.95">'
             + 'Emilio Hermosa Schiantarelli (NIA 100451150) &middot; '
             + 'Carlos Sanchez Arroyo (NIA 100451282) &middot; '
             + 'Rodrigo Valderrey Tarrero (NIA 100451271)</p>')
parts.append('</header>')

# Tab bar
parts.append('<div class="tab-bar">'
             + tab_btn('resumen',    'Resumen',           active=True)
             + tab_btn('mapas',      'Mapas')
             + tab_btn('series',     'Series temporales')
             + tab_btn('modelos',    'Modelos predictivos')
             + tab_btn('estaciones', 'Estaciones LAQN')
             + '</div>')

# ── Tab Resumen ───────────────────────────────────────────────────────────────
kpis = (kpi('5',              'Estaciones LAQN')
      + kpi(str(avg_no2_val), 'NO&#x2082; medio (&#x3bc;g/m&#xB3;) 2019-2023')
      + kpi(str(n_tfl_val),   'Paradas TfL')
      + kpi('5',              'A&ntilde;os analizados (2019-2023)')
      + kpi(gp_r2_str,        'GP &mdash; R&#xB2; test (NO&#x2082;)')
      + kpi(ic_str,           '% puntos dentro IC &plusmn;1&sigma;'))

imgs_resumen = (img_card('img/fig_hora_no2.png',    'Perfil horario de NO&#x2082; por estaci&oacute;n')
              + img_card('img/fig_estacionalidad.png', 'Estacionalidad semanal y mensual')
              + img_card('img/fig_comparacion.png',  'Comparativa anual entre estaciones')
              + img_card('img/fig_correlacion.png',  'Correlaci&oacute;n movilidad &harr; contaminaci&oacute;n'))

parts.append('<div id="tab-resumen" class="tab-content active">'
             + '<p class="section-title">Indicadores clave &mdash; Red LAQN + TfL Londres 2019-2023</p>'
             + '<div class="kpi-grid">' + kpis + '</div>'
             + '<div class="img-grid">' + imgs_resumen + '</div>'
             + '</div>')

# ── Tab Mapas ─────────────────────────────────────────────────────────────────
map_btns = (map_btn('no2',      'NO&#x2082; por estaci&oacute;n', active=True)
          + map_btn('tfl',      'Densidad TfL')
          + map_btn('grafo',    'Red de transporte')
          + map_btn('conjunto', 'LAQN + TfL conjunto')
          + map_btn('clusters', 'Clusters LAQN')
          + map_btn('gp',       'NO&#x2082; 2022-2023'))

map_frames = (map_frame('no2',      'mapa_no2.html',      active=True)
            + map_frame('h3',       'mapa_h3_stops.html')
            + map_frame('tfl',      'mapa_tfl.html')
            + map_frame('grafo',    'mapa_grafo.html')
            + map_frame('conjunto', 'mapa_conjunto.html')
            + map_frame('clusters', 'mapa_clusters.html')
            + map_frame('gp',       'mapa_gp_pred.html'))

parts.append('<div id="tab-mapas" class="tab-content">'
             + '<p class="section-title">Representaci&oacute;n geogr&aacute;fica (RQ5)</p>'
             + '<div class="map-selector">' + map_btns + '</div>'
             + map_frames
             + '</div>')

# ── Tab Series temporales ─────────────────────────────────────────────────────
imgs_series = (img_card('img/fig_hora_no2.png',    'Perfil horario de NO&#x2082; (2019-2023)')
             + img_card('img/fig_tendencia.png',   'Tendencia interanual con media m&oacute;vil anual')
             + img_card('img/fig_decompose.png',   'Descomposici&oacute;n estacional STL &mdash; KC1')
             + img_card('img/fig_estacionalidad.png', 'Estacionalidad semanal y mensual NO&#x2082; + O&#x2083;'))

parts.append('<div id="tab-series" class="tab-content">'
             + '<p class="section-title">Series temporales (RQ4 &mdash; parte A)</p>'
             + '<div class="img-grid">' + imgs_series + '</div>'
             + '</div>')

# ── Tab Modelos ───────────────────────────────────────────────────────────────
kpis_mod = (kpi(xgb_mae_str, 'XGBoost &mdash; MAE test (&#x3bc;g/m&#xB3;)')
          + kpi(xgb_r2_str,  'XGBoost &mdash; R&#xB2; test')
          + kpi(gp_r2_str,   'Gaussian Process &mdash; R&#xB2; test')
          + kpi(ic_str,      '% puntos IC &plusmn;1&sigma;'))

imgs_mod = (img_card('img/fig_modelos.png', 'Comparativa de 6 modelos (MAE en test)')
          + img_card('img/fig_gp_no2.png',  'GP &mdash; predicci&oacute;n semanal NO&#x2082; con IC &plusmn;1&sigma;')
          + img_card('img/fig_xgb_no2.png', 'XGBoost &mdash; predicho vs real + importancia'))

parts.append('<div id="tab-modelos" class="tab-content">'
             + '<p class="section-title">Modelos predictivos</p>'
             + '<div class="kpi-grid">' + kpis_mod + '</div>'
             + '<div class="img-grid">' + imgs_mod + '</div>'
             + '</div>')

# ── Tab Estaciones LAQN ───────────────────────────────────────────────────────
parts.append('<div id="tab-estaciones" class="tab-content">'
             + '<p class="section-title">Estaciones LAQN &mdash; NO&#x2082; y cobertura TfL</p>'
             + '<input id="filtro" type="text" placeholder="Filtrar por estaci&oacute;n o tipo..." '
             + 'onkeyup="filtrarTabla()"/>'
             + tabla_html
             + '</div>')

parts.append(JS)
parts.append('</body></html>')

# ── Escribir fichero ───────────────────────────────────────────────────────────
html_out = '\n'.join(parts)
with open(os.path.join(DASH_DIR, 'index.html'), 'w', encoding='utf-8') as _f:
    _f.write(html_out)

print(f'Dashboard guardado: {DASH_DIR}/index.html ({len(html_out):,} bytes)')
print(f'KPIs: NO2={avg_no2_val} | TfL={n_tfl_val} | GP_R2={gp_r2_str} | IC={ic_str}')
print(f'      XGBoost MAE={xgb_mae_str} | XGBoost R2={xgb_r2_str}')

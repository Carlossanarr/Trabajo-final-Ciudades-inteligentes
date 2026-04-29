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
    '*{box-sizing:border-box;margin:0;padding:0}'
    'body{font-family:Segoe UI,Arial,sans-serif;background:#f5f6fa;color:#2c3e50}'
    'header{background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);'
    'color:#fff;padding:2rem 2.5rem;box-shadow:0 2px 8px rgba(0,0,0,.3)}'
    'header h1{font-size:1.6rem;margin-bottom:.3rem}'
    'header p{opacity:.8;font-size:.9rem}'
    '.tab-bar{display:flex;background:#fff;border-bottom:2px solid #e0e0e0;'
    'padding:0 2rem;box-shadow:0 1px 4px rgba(0,0,0,.06)}'
    '.tab-btn{padding:1rem 1.4rem;border:none;background:none;cursor:pointer;'
    'font-size:.95rem;color:#555;border-bottom:3px solid transparent;'
    'transition:all .2s;font-weight:500}'
    '.tab-btn:hover{color:#0f3460;background:#f0f4ff}'
    '.tab-btn.active{color:#0f3460;border-bottom-color:#0f3460;font-weight:700}'
    '.tab-content{display:none;padding:2rem 2.5rem}'
    '.tab-content.active{display:block}'
    '.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));'
    'gap:1.2rem;margin-bottom:2rem}'
    '.kpi{background:#fff;border-radius:12px;padding:1.4rem 1.2rem;text-align:center;'
    'box-shadow:0 2px 8px rgba(0,0,0,.07);border-top:4px solid #0f3460}'
    '.kpi .valor{font-size:2rem;font-weight:700;color:#0f3460}'
    '.kpi .label{font-size:.8rem;color:#777;margin-top:.3rem}'
    '.img-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));'
    'gap:1.5rem;margin-top:1.5rem}'
    '.img-card{background:#fff;border-radius:12px;padding:1rem;'
    'box-shadow:0 2px 8px rgba(0,0,0,.07)}'
    '.img-card img{width:100%;border-radius:8px}'
    '.img-card p{font-size:.82rem;color:#555;margin-top:.5rem;text-align:center}'
    '.map-selector{display:flex;gap:.8rem;flex-wrap:wrap;margin-bottom:1.2rem}'
    '.map-btn{padding:.55rem 1.1rem;border:2px solid #0f3460;border-radius:20px;'
    'background:#fff;cursor:pointer;font-size:.88rem;color:#0f3460;'
    'font-weight:500;transition:all .2s}'
    '.map-btn:hover,.map-btn.active{background:#0f3460;color:#fff}'
    '.map-frame{display:none;border-radius:12px;overflow:hidden;'
    'box-shadow:0 3px 12px rgba(0,0,0,.12)}'
    '.map-frame.active{display:block}'
    '.map-frame iframe{width:100%;height:580px;border:none}'
    '.data-table{width:100%;border-collapse:collapse;background:#fff;'
    'border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.07)}'
    '.data-table th{background:#0f3460;color:#fff;padding:.7rem 1rem;'
    'text-align:left;font-size:.85rem}'
    '.data-table td{padding:.6rem 1rem;border-bottom:1px solid #f0f0f0;font-size:.85rem}'
    '.data-table tr:last-child td{border-bottom:none}'
    '.data-table tr:hover td{background:#f0f4ff}'
    '#filtro{padding:.5rem 1rem;border:1px solid #ccc;border-radius:8px;'
    'margin-bottom:1rem;font-size:.9rem;width:100%;max-width:400px}'
    '.about-box{background:#fff;border-radius:12px;padding:1.8rem 2rem;'
    'box-shadow:0 2px 8px rgba(0,0,0,.07);line-height:1.7}'
    '.about-box h3{color:#0f3460;margin:1.2rem 0 .4rem}'
    '.about-box ul{padding-left:1.4rem;color:#444}'
    '.section-title{font-size:1.1rem;font-weight:700;color:#0f3460;margin-bottom:1rem}'
    '.badge{display:inline-block;background:#e8f0fe;color:#0f3460;border-radius:6px;'
    'padding:.2rem .6rem;font-size:.78rem;font-weight:600;margin:.1rem}'
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
parts.append('<p>Trabajo final &middot; Ciudades Inteligentes &middot; UC3M &middot; 2026</p>')
parts.append('<p style="margin-top:.35rem;opacity:.95">'
             + 'Emilio Hermosa Schiantarelli (NIA 100451150) &middot; '
             + 'Carlos Sanchez Arroyo (NIA 100451282) &middot; '
             + 'Rodrigo Valderrey Tarrero (NIA 100451271)</p>')
parts.append('<p style="margin-top:.5rem">'
             + '<span class="badge">RQ1 Ciudad real</span>'
             + '<span class="badge">RQ2 Movilidad + Sostenibilidad</span>'
             + '<span class="badge">RQ3 Dashboard</span>'
             + '<span class="badge">RQ4 Grafo + Series temporales</span>'
             + '<span class="badge">RQ5 Mapas geogr&aacute;ficos</span>'
             + '</p>')
parts.append('</header>')

# Tab bar
parts.append('<div class="tab-bar">'
             + tab_btn('resumen',    'Resumen',           active=True)
             + tab_btn('mapas',      'Mapas')
             + tab_btn('series',     'Series temporales')
             + tab_btn('modelos',    'Modelos predictivos')
             + tab_btn('estaciones', 'Estaciones LAQN')
             + tab_btn('acerca',     'Acerca de')
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

# ── Tab Acerca de ─────────────────────────────────────────────────────────────
parts.append('<div id="tab-acerca" class="tab-content">'
             + '<div class="about-box">'
             + '<h3>Pregunta de investigaci&oacute;n</h3>'
             + '<p>&iquest;Cu&aacute;l es la relaci&oacute;n entre la infraestructura de transporte p&uacute;blico '
             + 'y los niveles de contaminaci&oacute;n del aire en Londres? '
             + '&iquest;Qu&eacute; estaciones presentan mayor riesgo ambiental y menor cobertura?</p>'
             + '<h3>Metodolog&iacute;a</h3><ul>'
             + '<li>EDA estilo <em>lab_contaminacion_ambiental</em>: imputaci&oacute;n estacional, '
             + 'boxplots con percentil 95, media m&oacute;vil anual (365&times;24 h).</li>'
             + '<li>Movilidad: grafo TfL desde GTFS <code>pathways.txt</code>, centralidad de grado (RQ4-B).</li>'
             + '<li>Mapas Folium: <code>HeatMap</code>, <code>MarkerCluster</code>, K-means clustering (RQ5).</li>'
             + '<li>Descomposici&oacute;n STL aditiva con statsmodels (RQ4-A).</li>'
             + '<li>Comparativa de 6 modelos + XGBoost con variables temporales.</li>'
             + '<li>Proceso Gaussiano autoregresivo k=8 semanas, kernel RBF (GPyTorch).</li>'
             + '</ul>'
             + '<h3>Fuentes de datos</h3><ul>'
             + '<li>LAQN API &mdash; <code>londonair.org.uk</code></li>'
             + '<li>TfL Open Data GTFS &mdash; <code>tfl.gov.uk</code></li>'
             + '<li>Directiva UE 2008/50/CE (l&iacute;mite anual NO&#x2082;: 40 &micro;g/m&sup3;)</li>'
             + '<li>OMS Air Quality Guidelines 2021</li>'
             + '</ul>'
             + '<h3>Uso de IA generativa</h3>'
             + '<p>Se ha utilizado <strong>Claude (Anthropic)</strong> como apoyo para estructurar el '
             + 'notebook, depurar fragmentos de c&oacute;digo y revisar redacci&oacute;n. Todo el c&oacute;digo '
             + 'y las conclusiones han sido revisados, ejecutados y validados por los autores.</p>'
             + '<h3>Herramientas</h3><ul>'
             + '<li>Python 3 &middot; pandas &middot; numpy &middot; scikit-learn &middot; statsmodels</li>'
             + '<li>xgboost &middot; gpytorch &middot; torch</li>'
             + '<li>folium &middot; branca &middot; networkx &middot; seaborn &middot; matplotlib</li>'
             + '</ul>'
             + '</div></div>')

parts.append(JS)
parts.append('</body></html>')

# ── Escribir fichero ───────────────────────────────────────────────────────────
html_out = '\n'.join(parts)
with open(os.path.join(DASH_DIR, 'index.html'), 'w', encoding='utf-8') as _f:
    _f.write(html_out)

print(f'Dashboard guardado: {DASH_DIR}/index.html ({len(html_out):,} bytes)')
print(f'KPIs: NO2={avg_no2_val} | TfL={n_tfl_val} | GP_R2={gp_r2_str} | IC={ic_str}')
print(f'      XGBoost MAE={xgb_mae_str} | XGBoost R2={xgb_r2_str}')

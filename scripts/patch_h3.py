"""Patch notebook: add H3 hexagons, MarkerCluster inline maps, and display() calls."""
import json

NB = r'C:\Users\carlo\Desktop\CIUdades\Trabajo-final-Ciudades-inteligentes\Ciudades-TrabajoFinal.ipynb'
with open(NB, 'r', encoding='utf-8') as f:
    nb = json.load(f)

def get_idx(cell_id):
    for i, c in enumerate(nb['cells']):
        if c['id'] == cell_id:
            return i
    return None

def code_cell(cid, src):
    return {"cell_type":"code","execution_count":None,
            "id":cid,"metadata":{},"outputs":[],"source":src}

def md_cell(cid, src):
    return {"cell_type":"markdown","id":cid,"metadata":{},"source":src}

# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORTS: add h3pandas + h3
# ─────────────────────────────────────────────────────────────────────────────
i_imp = get_idx('c003')
old_imp = ''.join(nb['cells'][i_imp]['source'])
h3_import = (
    "\n# H3 hexagonal spatial indexing (estilo lab_movilidad)\n"
    "try:\n"
    "    import h3pandas\n"
    "    import h3\n"
    "except ImportError:\n"
    "    import subprocess; subprocess.run(['pip','install','h3pandas','-q'], check=False)\n"
    "    import h3pandas\n"
    "    import h3\n"
)
nb['cells'][i_imp]['source'] = old_imp.rstrip() + h3_import
nb['cells'][i_imp]['outputs'] = []
nb['cells'][i_imp]['execution_count'] = None
print(f'[1] Imports updated (cell {i_imp})')

# ─────────────────────────────────────────────────────────────────────────────
# 2. TfL EDA: add MarkerCluster inline map
# ─────────────────────────────────────────────────────────────────────────────
i_tfl = get_idx('c014')
old_tfl = ''.join(nb['cells'][i_tfl]['source'])
mc_addon = (
    "\n\n# ── Mapa interactivo — MarkerCluster de hubs TfL (estilo lab_movilidad) ──────\n"
    "map_tfl_mc = folium.Map(location=[51.505, -0.105], zoom_start=11,\n"
    "                        tiles='CartoDB positron')\n"
    "mc_tfl = MarkerCluster(name='Hubs TfL').add_to(map_tfl_mc)\n"
    "for _, row in gtfs_stations.head(300).iterrows():\n"
    "    if pd.notna(row['stop_lat']) and pd.notna(row['stop_lon']):\n"
    "        folium.Marker(\n"
    "            location=[row['stop_lat'], row['stop_lon']],\n"
    "            popup=str(row['stop_name'])[:50],\n"
    "            icon=folium.Icon(color='blue', icon='train', prefix='fa')\n"
    "        ).add_to(mc_tfl)\n"
    "for s, info in STATION_INFO.items():\n"
    "    folium.Marker(\n"
    "        location=[info['lat'], info['lon']],\n"
    "        popup=f'{s} - {info[\"name\"]}',\n"
    "        icon=folium.Icon(color='red', icon='tint', prefix='fa'),\n"
    "        tooltip=s\n"
    "    ).add_to(map_tfl_mc)\n"
    "map_tfl_mc\n"
)
nb['cells'][i_tfl]['source'] = old_tfl + mc_addon
nb['cells'][i_tfl]['outputs'] = []
nb['cells'][i_tfl]['execution_count'] = None
print(f'[2] TfL EDA MarkerCluster added (cell {i_tfl})')

# ─────────────────────────────────────────────────────────────────────────────
# 3. INSERT H3 hexagon section after stop density cell (c026)
# ─────────────────────────────────────────────────────────────────────────────
i_density = get_idx('c026')

md_h3 = md_cell('m_h3', (
    "### 4.3 Densidad de paradas en hexágonos H3\n\n"
    "Siguiendo la metodología del laboratorio de movilidad usamos la librería **H3** (Uber) "
    "para agregar las paradas TfL en una malla hexagonal de resolución 9 y visualizar la "
    "densidad espacial de transporte sobre Londres."
))

h3_src = (
    "# Agregación de paradas TfL por hexágono H3 — igual que en lab_movilidad con NYC taxi\n"
    "resolution = 9\n"
    "stops_h3_df = stops[['stop_lat','stop_lon']].copy()\n"
    "stops_h3_df['count'] = 1\n\n"
    "# geo_to_h3_aggregate: cuenta paradas por hexágono\n"
    "stops_h3 = stops_h3_df.h3.geo_to_h3_aggregate(\n"
    "    resolution, lat_col='stop_lat', lng_col='stop_lon'\n"
    ")\n"
    "print(f'Hexagonos H3 con paradas TfL: {len(stops_h3)}')\n"
    "print(f'Media de paradas por hexagono: {stops_h3[\"count\"].mean():.2f}')\n"
    "print(f'Maximo de paradas en un hexagono: {stops_h3[\"count\"].max()}')\n\n"
    "# Mapa cloropletico H3 con explore() — mismo patron que lab_movilidad\n"
    "map_h3 = folium.Map(location=[51.505, -0.105], zoom_start=11,\n"
    "                    tiles='CartoDB positron')\n\n"
    "stops_h3.h3.h3_to_geo_boundary().explore(\n"
    "    column='count',\n"
    "    cmap='YlOrRd',\n"
    "    tooltip=['count'],\n"
    "    popup=['count'],\n"
    "    legend=True,\n"
    "    style_kwds={'fillOpacity': 0.6, 'weight': 1},\n"
    "    m=map_h3\n"
    ")\n\n"
    "# Estaciones LAQN como marcadores rojos\n"
    "for s, info in STATION_INFO.items():\n"
    "    val = round(float(no2_filled[s].mean()), 1)\n"
    "    folium.Marker(\n"
    "        location=[info['lat'], info['lon']],\n"
    "        popup=f'<b>{s}</b><br>{info[\"name\"]}<br>NO2 medio: {val} ug/m3',\n"
    "        icon=folium.Icon(color='red', icon='tint', prefix='fa'),\n"
    "        tooltip=f'{s}: {val} ug/m3'\n"
    "    ).add_to(map_h3)\n\n"
    "map_h3.save(f'{DASH_DIR}/maps/mapa_h3_stops.html')\n"
    "print('Mapa H3 guardado.')\n"
    "map_h3\n"
)

nb['cells'].insert(i_density + 1, md_h3)
nb['cells'].insert(i_density + 2, code_cell('c_h3', h3_src))
print(f'[3] H3 section inserted after cell {i_density}')

# ─────────────────────────────────────────────────────────────────────────────
# 4. Maps cell: add display() inline after each save
# ─────────────────────────────────────────────────────────────────────────────
i_maps = get_idx('c038')
old_maps = ''.join(nb['cells'][i_maps]['source'])

# Replace save+print combos to also display inline
replacements = [
    ("mapa_no2.save(f'{DASH_DIR}/maps/mapa_no2.html')\nprint('mapa_no2.html OK')",
     "mapa_no2.save(f'{DASH_DIR}/maps/mapa_no2.html')\nprint('mapa_no2.html OK')\ndisplay(mapa_no2)"),
    ("mapa_tfl.save(f'{DASH_DIR}/maps/mapa_tfl.html')\nprint('mapa_tfl.html OK')",
     "mapa_tfl.save(f'{DASH_DIR}/maps/mapa_tfl.html')\nprint('mapa_tfl.html OK')\ndisplay(mapa_tfl)"),
    ("mapa_grafo.save(f'{DASH_DIR}/maps/mapa_grafo.html')\nprint('mapa_grafo.html OK')",
     "mapa_grafo.save(f'{DASH_DIR}/maps/mapa_grafo.html')\nprint('mapa_grafo.html OK')\ndisplay(mapa_grafo)"),
    ("mapa_conjunto.save(f'{DASH_DIR}/maps/mapa_conjunto.html')\nprint('mapa_conjunto.html OK')",
     "mapa_conjunto.save(f'{DASH_DIR}/maps/mapa_conjunto.html')\nprint('mapa_conjunto.html OK')\ndisplay(mapa_conjunto)"),
    ("mapa_clusters.save(f'{DASH_DIR}/maps/mapa_clusters.html')\nprint('mapa_clusters.html OK')",
     "mapa_clusters.save(f'{DASH_DIR}/maps/mapa_clusters.html')\nprint('mapa_clusters.html OK')\ndisplay(mapa_clusters)"),
    ("mapa_gp.save(f'{DASH_DIR}/maps/mapa_gp_pred.html')\nprint('mapa_gp_pred.html OK')",
     "mapa_gp.save(f'{DASH_DIR}/maps/mapa_gp_pred.html')\nprint('mapa_gp_pred.html OK')\ndisplay(mapa_gp)"),
]
for old, new in replacements:
    old_maps = old_maps.replace(old, new)

nb['cells'][i_maps]['source'] = old_maps
nb['cells'][i_maps]['outputs'] = []
nb['cells'][i_maps]['execution_count'] = None
print(f'[4] Maps cell updated with inline display (cell {i_maps})')

# ─────────────────────────────────────────────────────────────────────────────
# 5. Update generate_dashboard.py: add H3 map tab
# ─────────────────────────────────────────────────────────────────────────────
DASH_SCRIPT = r'C:\Users\carlo\Desktop\CIUdades\Trabajo-final-Ciudades-inteligentes\scripts\generate_dashboard.py'
with open(DASH_SCRIPT, 'r', encoding='utf-8') as f:
    ds = f.read()

ds = ds.replace(
    "map_btns = (map_btn('no2',      'NO&#x2082; por estaci&oacute;n', active=True)\n"
    "          + map_btn('tfl',      'Heatmap TfL')\n"
    "          + map_btn('grafo',    'Red de transporte')\n"
    "          + map_btn('conjunto', 'LAQN + TfL conjunto')\n"
    "          + map_btn('clusters', 'Clusters LAQN')\n"
    "          + map_btn('gp',       'NO&#x2082; 2022-2023'))",
    "map_btns = (map_btn('no2',      'NO&#x2082; por estaci&oacute;n', active=True)\n"
    "          + map_btn('h3',       'Hex&aacute;gonos H3 TfL')\n"
    "          + map_btn('tfl',      'Heatmap TfL')\n"
    "          + map_btn('grafo',    'Red de transporte')\n"
    "          + map_btn('conjunto', 'LAQN + TfL conjunto')\n"
    "          + map_btn('clusters', 'Clusters LAQN')\n"
    "          + map_btn('gp',       'NO&#x2082; 2022-2023'))"
)
ds = ds.replace(
    "map_frames = (map_frame('no2',      'mapa_no2.html',      active=True)\n"
    "            + map_frame('tfl',      'mapa_tfl.html')\n"
    "            + map_frame('grafo',    'mapa_grafo.html')\n"
    "            + map_frame('conjunto', 'mapa_conjunto.html')\n"
    "            + map_frame('clusters', 'mapa_clusters.html')\n"
    "            + map_frame('gp',       'mapa_gp_pred.html'))",
    "map_frames = (map_frame('no2',      'mapa_no2.html',      active=True)\n"
    "            + map_frame('h3',       'mapa_h3_stops.html')\n"
    "            + map_frame('tfl',      'mapa_tfl.html')\n"
    "            + map_frame('grafo',    'mapa_grafo.html')\n"
    "            + map_frame('conjunto', 'mapa_conjunto.html')\n"
    "            + map_frame('clusters', 'mapa_clusters.html')\n"
    "            + map_frame('gp',       'mapa_gp_pred.html'))"
)
with open(DASH_SCRIPT, 'w', encoding='utf-8') as f:
    f.write(ds)
print('[5] generate_dashboard.py updated with H3 map tab')

# ─────────────────────────────────────────────────────────────────────────────
# Verify all cells compile
# ─────────────────────────────────────────────────────────────────────────────
errors = []
for c in nb['cells']:
    if c['cell_type'] == 'code':
        src = ''.join(c['source'])
        try:
            compile(src, c['id'], 'exec')
        except SyntaxError as e:
            errors.append((c['id'], e))
if errors:
    for cid, e in errors:
        print(f'SYNTAX ERROR in {cid}: {e}')
else:
    print('All cells compile OK')

with open(NB, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f'Notebook saved: {len(nb["cells"])} cells')

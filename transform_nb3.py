"""Transform notebook: step 3 - Dashboard, marker colors, weekly heatmap"""
import json

NB_PATH = 'Ciudades-TrabajoFinal.ipynb'
nb = json.load(open(NB_PATH, encoding='utf-8'))

# --- Cell 19 (id=4b21b01b): Update dashboard - remove modelo tab, renumber ---
for i, c in enumerate(nb['cells']):
    if c.get('id') == '4b21b01b':
        src = ''.join(c['source'])
        # Remove 'modelo' from DASH_BLOCKS
        src = src.replace("DASH_BLOCKS = {'eda': '', 'no2': '', 'modelo': '', 'mapas': ''}", 
                         "DASH_BLOCKS = {'eda': '', 'no2': '', 'mapas': ''}")
        # Remove modelo tab button
        src = src.replace('  <button class="tab-btn" onclick="showTab(\'modelo\',this)">3. Modelo predictivo</button>\n', '')
        # Renumber mapas tab: 4 -> 3
        src = src.replace("showTab('mapas',this)\">4. Mapas</button>", "showTab('mapas',this)\">3. Mapas</button>")
        # Remove modelo tab content div
        modelo_start = src.find('<div id="tab-modelo"')
        modelo_end = src.find('</div>', modelo_start) + len('</div>')
        if modelo_start > 0:
            src = src[:modelo_start] + src[modelo_end+1:]
        # Remove modelo render line
        src = src.replace("    html = html.replace('__MODELO__', DASH_BLOCKS['modelo'] or PENDING)\n", "")
        c['source'] = [src]
        break

# --- Cell 34 (id=63c1649d): Add color to markers by station type ---
for i, c in enumerate(nb['cells']):
    if c.get('id') == '63c1649d':
        c['source'] = [
            "estaciones_disp = [s for s in STATION_INFO if s in no2_clip.columns]\n",
            "print(f'Estaciones en mapa: {len(estaciones_disp)}')\n",
            "\n",
            "# Mapeo de TYPE_COLORS a colores de icono Folium\n",
            "FOLIUM_ICON_COLORS = {\n",
            "    'Kerbside':         'red',\n",
            "    'Roadside':         'orange',\n",
            "    'Urban Background': 'blue',\n",
            "    'Suburban':         'green',\n",
            "    'Industrial':       'purple',\n",
            "}\n",
            "\n",
            "mapa_estaciones = folium.Map(location=[51.505, -0.09], zoom_start=11,\n",
            "                              tiles='cartodbpositron')\n",
            "\n",
            "for s in estaciones_disp:\n",
            "    info = STATION_INFO[s]\n",
            "    icon_color = FOLIUM_ICON_COLORS.get(info['type'], 'gray')\n",
            "    popup_html = (\n",
            "        f'<b>{s}</b> &mdash; {info[\"name\"]}<br>'\n",
            "        f'Tipo: {info[\"type\"]}<br>'\n",
            "        f'Municipio: {info.get(\"authority\", \"\")}'\n",
            "    )\n",
            "    folium.Marker(\n",
            "        location=[info['lat'], info['lon']],\n",
            "        popup=folium.Popup(popup_html, max_width=260),\n",
            "        tooltip=f'{s} \\u2014 {info[\"name\"]} ({info[\"type\"]})',\n",
            "        icon=folium.Icon(color=icon_color, icon='map-marker', prefix='fa'),\n",
            "    ).add_to(mapa_estaciones)\n",
            "\n",
            "# Leyenda HTML\n",
            "from branca.element import MacroElement, Template\n",
            "legend_html = '<div style=\"position:fixed;bottom:30px;left:30px;z-index:1000;background:white;padding:10px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.3);font-size:12px;\">'\n",
            "legend_html += '<b>Tipo de estaci\\u00f3n</b><br>'\n",
            "for tipo, color in FOLIUM_ICON_COLORS.items():\n",
            "    if any(STATION_INFO[s]['type'] == tipo for s in estaciones_disp):\n",
            "        legend_html += f'<i style=\"background:{TYPE_COLORS[tipo]};width:12px;height:12px;display:inline-block;border-radius:50%;margin-right:5px;\"></i> {tipo}<br>'\n",
            "legend_html += '</div>'\n",
            "mapa_estaciones.get_root().html.add_child(folium.Element(legend_html))\n",
            "\n",
            "mapa_estaciones.save(f'{DASH_DIR}/maps/mapa_estaciones.html')\n",
            "mapa_estaciones\n",
        ]
        break

# --- Cell 39 (id=cbdee420): Update 5.4 -> 4.4 markdown ---
for i, c in enumerate(nb['cells']):
    if c.get('id') == 'cbdee420':
        src = ''.join(c['source'])
        src = src.replace("5.4", "4.4")
        c['source'] = [src]
        break

# --- Cell 40 (id=23d41ea4): Rewrite weekly heatmap with interpolation ---
for i, c in enumerate(nb['cells']):
    if c.get('id') == '23d41ea4':
        c['source'] = [
"from sklearn.neighbors import BallTree\n",
"from scipy.interpolate import RBFInterpolator\n",
"\n",
"if 'stops_bus' not in dir() or 'stops_metro' not in dir():\n",
"    raise NameError('stops_bus / stops_metro no definidos: re-ejecuta la celda de carga de datos.')\n",
"\n",
"def haversine_km(lat1, lon1, lat2, lon2):\n",
"    R = 6371.0\n",
"    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])\n",
"    dlat, dlon = lat2 - lat1, lon2 - lon1\n",
"    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2\n",
"    return R * 2 * np.arcsin(np.sqrt(a))\n",
"\n",
"def build_knn_graph(df, k=3):\n",
"    df = df.reset_index(drop=True)\n",
"    coords = np.radians(df[['stop_lat', 'stop_lon']].values)\n",
"    tree = BallTree(coords, metric='haversine')\n",
"    dist, idx = tree.query(coords, k=min(k + 1, len(df)))\n",
"    G = nx.Graph()\n",
"    ids = df['parent_station'].values\n",
"    for i, row in df.iterrows():\n",
"        G.add_node(ids[i], lat=float(row['stop_lat']), lon=float(row['stop_lon']))\n",
"    for i in range(len(df)):\n",
"        for j, d in zip(idx[i, 1:], dist[i, 1:]):\n",
"            G.add_edge(ids[i], ids[int(j)], km=float(d) * 6371.0)\n",
"    return G\n",
"\n",
"G_bus   = build_knn_graph(stops_bus,   k=3)\n",
"G_metro = build_knn_graph(stops_metro, k=3)\n",
"print(f'Grafo BUS  : {G_bus.number_of_nodes():>4d} nodos | {G_bus.number_of_edges():>5d} aristas')\n",
"print(f'Grafo METRO: {G_metro.number_of_nodes():>4d} nodos | {G_metro.number_of_edges():>5d} aristas')\n",
"\n",
"# --- NO2 media semanal por estacion ---\n",
"cols_map = [s for s in STATION_INFO if s in no2_clip.columns]\n",
"weekly_no2 = no2_clip[cols_map].resample('W').mean()\n",
"print(f'Semanas: {len(weekly_no2)}, Estaciones: {len(cols_map)}')\n",
"\n",
"# Coordenadas de estaciones\n",
"st_lats = np.array([STATION_INFO[s]['lat'] for s in cols_map])\n",
"st_lons = np.array([STATION_INFO[s]['lon'] for s in cols_map])\n",
"st_coords = np.column_stack([st_lats, st_lons])\n",
"\n",
"# --- Interpolacion RBF para una semana ejemplo ---\n",
"example_week = weekly_no2.index[len(weekly_no2)//2]  # semana central\n",
"vals = weekly_no2.loc[example_week, cols_map].values\n",
"valid = ~np.isnan(vals)\n",
"rbf = RBFInterpolator(st_coords[valid], vals[valid], kernel='thin_plate_spline', smoothing=1.0)\n",
"\n",
"# Grilla de interpolacion\n",
"lat_min, lat_max = st_lats.min() - 0.05, st_lats.max() + 0.05\n",
"lon_min, lon_max = st_lons.min() - 0.05, st_lons.max() + 0.05\n",
"grid_lat = np.linspace(lat_min, lat_max, 60)\n",
"grid_lon = np.linspace(lon_min, lon_max, 60)\n",
"grid_pts = np.array([[la, lo] for la in grid_lat for lo in grid_lon])\n",
"z_interp = rbf(grid_pts).clip(0)\n",
"\n",
"# Heatmap data: list of [lat, lon, value]\n",
"heat_data = [[float(pt[0]), float(pt[1]), float(z)] for pt, z in zip(grid_pts, z_interp)]\n",
"\n",
"# --- Asignar contaminacion interpolada a paradas ---\n",
"combined = stops_pt.reset_index(drop=True)\n",
"stop_coords = combined[['stop_lat', 'stop_lon']].values\n",
"stop_no2 = rbf(stop_coords).clip(0)\n",
"combined['no2_interp'] = stop_no2\n",
"\n",
"# --- Render mapa ---\n",
"mapa_grafo = folium.Map(location=[51.51, -0.12], zoom_start=11, tiles='cartodbpositron')\n",
"\n",
"HeatMap(heat_data, radius=18, blur=22, min_opacity=0.35, max_zoom=13,\n",
"        gradient={0.2: '#3b82f6', 0.5: '#facc15', 0.8: '#f97316', 1.0: '#dc2626'},\n",
"        name=f'HeatMap NO\\u2082 (semana {example_week.strftime(\"%Y-%m-%d\")})'\n",
"       ).add_to(mapa_grafo)\n",
"\n",
"STYLES = {\n",
"    'bus':   {'edge': '#16a34a', 'fill': '#22c55e', 'border': '#15803d'},\n",
"    'metro': {'edge': '#1d4ed8', 'fill': '#3b82f6', 'border': '#1e3a8a'},\n",
"}\n",
"\n",
"def render_graph(G, tipo, mapa, stop_df):\n",
"    s = STYLES[tipo]\n",
"    fg = folium.FeatureGroup(name=f'Grafo {tipo}', show=True)\n",
"    for u, v, attrs in G.edges(data=True):\n",
"        a, b = G.nodes[u], G.nodes[v]\n",
"        folium.PolyLine(\n",
"            [(a['lat'], a['lon']), (b['lat'], b['lon'])],\n",
"            color=s['edge'], weight=1.3, opacity=0.55,\n",
"            tooltip=f'{tipo}: {attrs[\"km\"]:.2f} km',\n",
"        ).add_to(fg)\n",
"    # Nodos con popup de contaminacion interpolada\n",
"    tipo_stops = stop_df[stop_df['transport'] == tipo]\n",
"    stop_no2_map = dict(zip(tipo_stops['parent_station'], tipo_stops['no2_interp']))\n",
"    for n, attr in G.nodes(data=True):\n",
"        no2_val = stop_no2_map.get(n, float('nan'))\n",
"        popup_txt = (f'<b>{tipo.upper()} - {n}</b><br>'\n",
"                     f'Grado: {G.degree[n]}<br>'\n",
"                     f'NO\\u2082 interpolado: <b>{no2_val:.1f} \\u03bcg/m\\u00b3</b>')\n",
"        folium.CircleMarker(\n",
"            [attr['lat'], attr['lon']],\n",
"            radius=2.8, color=s['border'], weight=1,\n",
"            fill=True, fill_color=s['fill'], fill_opacity=0.75,\n",
"            popup=folium.Popup(popup_txt, max_width=220),\n",
"            tooltip=f'{tipo} | {n} | NO\\u2082: {no2_val:.1f}',\n",
"        ).add_to(fg)\n",
"    fg.add_to(mapa)\n",
"\n",
"render_graph(G_bus,   'bus',   mapa_grafo, combined)\n",
"render_graph(G_metro, 'metro', mapa_grafo, combined)\n",
"\n",
"# Marcadores de estaciones LAQN\n",
"for s in cols_map:\n",
"    info = STATION_INFO[s]\n",
"    val = weekly_no2.loc[example_week, s]\n",
"    folium.CircleMarker(\n",
"        [info['lat'], info['lon']],\n",
"        radius=10, color='#b91c1c', weight=2,\n",
"        fill=True, fill_color='#dc2626', fill_opacity=0.9,\n",
"        popup=f'<b>LAQN {s}</b><br>{info[\"name\"]}<br>NO\\u2082: {val:.1f} \\u03bcg/m\\u00b3',\n",
"        tooltip=f'LAQN {s}: {val:.1f} \\u03bcg/m\\u00b3',\n",
"    ).add_to(mapa_grafo)\n",
"\n",
"folium.LayerControl(collapsed=False).add_to(mapa_grafo)\n",
"mapa_grafo.save(f'{DASH_DIR}/maps/mapa_grafo.html')\n",
"\n",
"# --- Guardar datos semanales para dashboard con slider ---\n",
"import os\n",
"slider_dir = f'{DASH_DIR}/maps/weekly_data'\n",
"os.makedirs(slider_dir, exist_ok=True)\n",
"\n",
"for week_date in weekly_no2.index:\n",
"    vals_w = weekly_no2.loc[week_date, cols_map].values\n",
"    valid_w = ~np.isnan(vals_w)\n",
"    if valid_w.sum() < 3:\n",
"        continue\n",
"    rbf_w = RBFInterpolator(st_coords[valid_w], vals_w[valid_w], kernel='thin_plate_spline', smoothing=1.0)\n",
"    z_w = rbf_w(grid_pts).clip(0)\n",
"    week_data = [[float(pt[0]), float(pt[1]), float(z)] for pt, z in zip(grid_pts, z_w)]\n",
"    fname = f'{slider_dir}/{week_date.strftime(\"%Y-%m-%d\")}.json'\n",
"    with open(fname, 'w') as f:\n",
"        json.dump(week_data, f)\n",
"\n",
"print(f'Datos semanales guardados en {slider_dir}: {len(os.listdir(slider_dir))} archivos')\n",
"print(f'Mapa ejemplo: semana {example_week.strftime(\"%Y-%m-%d\")}')\n",
"mapa_grafo\n",
        ]
        break

# --- Cell 41 (id=2141c651): Update dashboard maps block - renumber ---
for i, c in enumerate(nb['cells']):
    if c.get('id') == '2141c651':
        src = ''.join(c['source'])
        src = src.replace("5.1 Estaciones LAQN", "4.1 Estaciones LAQN")
        src = src.replace("5.2 Cluster paradas", "4.2 Cluster paradas")
        src = src.replace("5.3 Hex", "4.3 Hex")
        src = src.replace("5.4 Grafo + HeatMap", "4.4 Grafo + HeatMap")
        c['source'] = [src]
        break

# --- Cell 42 (id=138f194f): Update dashboard section markdown ---
for i, c in enumerate(nb['cells']):
    if c.get('id') == '138f194f':
        src = ''.join(c['source'])
        # Remove modelo reference
        src = src.replace("3. **Modelo predictivo** \u2014 predicci\u00f3n GP a 30 d\u00edas con m\u00e9tricas R\u00b2/MAE/RMSE por split.\n", "")
        src = src.replace("4. **Mapas**", "3. **Mapas**")
        c['source'] = [src]
        break

# --- Cell 43 (id=8946b831): Update dashboard final render ---
for i, c in enumerate(nb['cells']):
    if c.get('id') == '8946b831':
        src = ''.join(c['source'])
        # Remove modelo check from the loop
        # No changes needed, the loop just checks DASH_BLOCKS keys dynamically
        c['source'] = [src]
        break

# Save
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("Step 3 done: dashboard updated, markers colored, weekly heatmap with interpolation")

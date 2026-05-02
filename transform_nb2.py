"""Transform notebook: step 2 - Add section 3.5, delete section 4, renumber"""
import json

NB_PATH = 'Ciudades-TrabajoFinal.ipynb'
nb = json.load(open(NB_PATH, encoding='utf-8'))

# --- INSERT section 3.5 after cell 28 (before cell 29 which is dashboard NO2 block) ---
md_35 = {
    "cell_type": "markdown", "id": "sec35_md", "metadata": {},
    "source": [
        "### 3.5 Estacionalidad por tipo de estaci\u00f3n\n",
        "\n",
        "Para cada tipo de estaci\u00f3n (Roadside, Urban Background, Kerbside, Suburban, Industrial) se calcula el **valor medio de NO\u2082 en cada hora** y se aplica una descomposici\u00f3n estacional (`seasonal_decompose`) para identificar componentes de **tendencia**, **estacionalidad** y **residuos**."
    ]
}

code_35 = {
    "cell_type": "code", "execution_count": None, "id": "sec35_code",
    "metadata": {}, "outputs": [],
    "source": [
        "from statsmodels.tsa.seasonal import seasonal_decompose\n",
        "\n",
        "cols_disp = [s for s in STATION_INFO if s in no2_clip.columns]\n",
        "\n",
        "# Calcular media horaria por tipo de estaci\u00f3n\n",
        "type_hourly = {}\n",
        "for tipo in TYPE_COLORS:\n",
        "    cols_t = [s for s in cols_disp if STATION_INFO[s]['type'] == tipo]\n",
        "    if not cols_t:\n",
        "        continue\n",
        "    # Media de todas las estaciones de ese tipo para cada timestamp\n",
        "    type_hourly[tipo] = no2_clip[cols_t].mean(axis=1)\n",
        "\n",
        "# Descomposici\u00f3n estacional para cada tipo\n",
        "n_tipos = len(type_hourly)\n",
        "fig, axes = plt.subplots(n_tipos, 4, figsize=(20, 4 * n_tipos))\n",
        "if n_tipos == 1:\n",
        "    axes = axes.reshape(1, -1)\n",
        "\n",
        "for i, (tipo, serie) in enumerate(type_hourly.items()):\n",
        "    # Resamplear a diario para seasonal_decompose\n",
        "    daily = serie.resample('D').mean().dropna()\n",
        "    if len(daily) < 365:\n",
        "        print(f'{tipo}: datos insuficientes para descomposici\u00f3n')\n",
        "        continue\n",
        "    result = seasonal_decompose(daily, model='additive', period=365)\n",
        "    color = TYPE_COLORS[tipo]\n",
        "    \n",
        "    titles = ['Observado', 'Tendencia', 'Estacionalidad', 'Residuos']\n",
        "    components = [result.observed, result.trend, result.seasonal, result.resid]\n",
        "    for j, (comp, title) in enumerate(zip(components, titles)):\n",
        "        axes[i, j].plot(comp, color=color, lw=0.6, alpha=0.8)\n",
        "        axes[i, j].set_title(f'{tipo} \\u2014 {title}', fontsize=9, fontweight='bold')\n",
        "        axes[i, j].grid(alpha=0.2)\n",
        "        if j == 0:\n",
        "            axes[i, j].set_ylabel('NO\\u2082 (\\u03bcg/m\\u00b3)', fontsize=8)\n",
        "\n",
        "plt.suptitle('Descomposici\u00f3n estacional de NO\\u2082 por tipo de estaci\u00f3n (periodo=365 d\\u00edas)',\n",
        "             fontsize=13, fontweight='bold')\n",
        "plt.tight_layout()\n",
        "plt.savefig(f'{DASH_DIR}/img/fig_estacionalidad.png', bbox_inches='tight', dpi=160)\n",
        "plt.show()\n",
        "\n",
        "# Resumen: media horaria por tipo\n",
        "fig, ax = plt.subplots(figsize=(12, 5))\n",
        "for tipo, serie in type_hourly.items():\n",
        "    hourly_mean = serie.groupby(serie.index.hour).mean()\n",
        "    cols_t = [s for s in cols_disp if STATION_INFO[s]['type'] == tipo]\n",
        "    ax.plot(hourly_mean.index, hourly_mean.values, lw=2.4,\n",
        "            color=TYPE_COLORS[tipo], marker='o', ms=5,\n",
        "            label=f'{tipo} (n={len(cols_t)})')\n",
        "ax.axhline(40, color='green', ls='--', lw=1.4, alpha=0.8, label='OMS 40 \\u03bcg/m\\u00b3')\n",
        "ax.set_title('Valor medio de NO\\u2082 por hora seg\\u00fan tipo de estaci\\u00f3n', fontweight='bold')\n",
        "ax.set_xlabel('Hora del d\\u00eda'); ax.set_ylabel('NO\\u2082 medio (\\u03bcg/m\\u00b3)')\n",
        "ax.set_xticks(range(0, 24, 2))\n",
        "ax.legend(loc='upper right', fontsize=8); ax.grid(alpha=0.25)\n",
        "plt.tight_layout()\n",
        "plt.savefig(f'{DASH_DIR}/img/fig_media_horaria_tipo.png', bbox_inches='tight', dpi=160)\n",
        "plt.show()\n"
    ]
}

# Insert after cell 28 (index 28), before cell 29
nb['cells'].insert(29, md_35)
nb['cells'].insert(30, code_35)

# Now cells shifted by 2. Old cells 30-33 are now 32-35. Delete them.
del nb['cells'][32:36]

# --- Update dashboard NO2 block (was cell 29, now cell 31 after insert+delete) ---
# Find cell with id=63adf863
for i, c in enumerate(nb['cells']):
    if c.get('id') == '63adf863':
        src = ''.join(c['source'])
        src = src.replace(
            '  <div class="img-card"><img src="img/fig_no2_anual.png"/><p>3.4 \u2014 NO\u2082 medio anual</p></div>\n</div>',
            '  <div class="img-card"><img src="img/fig_no2_anual.png"/><p>3.4 \u2014 NO\u2082 medio anual</p></div>\n'
            '  <div class="img-card"><img src="img/fig_estacionalidad.png"/><p>3.5 \u2014 Descomposici\u00f3n estacional por tipo</p></div>\n'
            '  <div class="img-card"><img src="img/fig_media_horaria_tipo.png"/><p>3.5 \u2014 Media horaria por tipo</p></div>\n</div>'
        )
        c['source'] = [src]
        break

# --- Renumber sections: 5->4, 6->5 in markdown cells ---
for c in nb['cells']:
    if c['cell_type'] == 'markdown':
        src = ''.join(c['source'])
        # Section 5 -> 4
        src = src.replace("## 5. Representaci\u00f3n geogr\u00e1fica", "## 4. Representaci\u00f3n geogr\u00e1fica")
        src = src.replace("<a id='5'>", "<a id='4'>")
        src = src.replace("### 5.1 ", "### 4.1 ")
        src = src.replace("### 5.2 ", "### 4.2 ")
        src = src.replace("### 5.3 ", "### 4.3 ")
        src = src.replace("### 5.4 ", "### 4.4 ")
        src = src.replace("- **5.1**", "- **4.1**")
        src = src.replace("- **5.2**", "- **4.2**")
        src = src.replace("- **5.3**", "- **4.3**")
        src = src.replace("- **5.4**", "- **4.4**")
        # Section 6 -> 5
        src = src.replace("## 6. Dashboard interactivo", "## 5. Dashboard interactivo")
        src = src.replace("<a id='6'>", "<a id='5'>")
        c['source'] = [src]

# --- Update index (cell 1) ---
cell1 = nb['cells'][1]
new_index = [
    "## \u00cdndice\n",
    "\n",
    "1. [Carga de datos](#1)\n",
    "2. [An\u00e1lisis Exploratorio (EDA)](#2)\n",
    "   - 2.1 Visi\u00f3n general de la calidad del aire\n",
    "   - 2.2 Valores nulos e imputaci\u00f3n (con eliminaci\u00f3n de 2023)\n",
    "   - 2.3 Distribuciones y outliers\n",
    "3. [An\u00e1lisis de contaminaci\u00f3n (NO\u2082)](#3)\n",
    "   - 3.1 Patr\u00f3n horario (diario)\n",
    "   - 3.2 Patr\u00f3n semanal\n",
    "   - 3.3 Patr\u00f3n mensual\n",
    "   - 3.4 Tendencia anual\n",
    "   - 3.5 Estacionalidad por tipo de estaci\u00f3n\n",
    "4. [Representaci\u00f3n geogr\u00e1fica](#4)\n",
    "   - 4.1 Mapa de las estaciones LAQN\n",
    "   - 4.2 MarkerCluster de paradas TfL\n",
    "   - 4.3 Cobertura por hex\u00e1gonos H3\n",
    "   - 4.4 Grafo de transporte sobre HeatMap de NO\u2082\n",
    "5. [Dashboard interactivo](#5)\n",
    "\n",
    "---\n",
    "\n",
    "## Pregunta de investigaci\u00f3n\n",
    "\n",
    "> **\u00bfCu\u00e1l es la relaci\u00f3n entre la infraestructura de transporte p\u00fablico y los niveles de contaminaci\u00f3n del aire (NO\u2082) en Londres?**\n",
    ">\n",
    "> Buscamos identificar qu\u00e9 estaciones presentan simult\u00e1neamente:\n",
    ">\n",
    "> - **mayor riesgo ambiental**, asociado a niveles elevados de NO\u2082;\n",
    "> - **menor cobertura de transporte p\u00fablico**, medida a partir de la proximidad y densidad de paradas TfL.\n",
    "\n",
    "La contaminaci\u00f3n por NO\u2082 afecta directamente a la salud y la sostenibilidad urbana, mientras que la cobertura del transporte p\u00fablico condiciona la dependencia del veh\u00edculo privado. Estudiar ambos factores en conjunto permite identificar zonas vulnerables donde la planificaci\u00f3n del transporte podr\u00eda tener mayor impacto ambiental.\n",
    "\n",
    "Este trabajo cumple los requisitos del curso:\n",
    "\n",
    "- Usa una ciudad real y datos abiertos de Londres (RQ1).\n",
    "- Integra movilidad y sostenibilidad ambiental (RQ2).\n",
    "- Trabaja con series temporales, redes de transporte y representaci\u00f3n geogr\u00e1fica (RQ4 y RQ5).\n",
    "- Sus resultados se resumen en un dashboard interactivo (RQ3).\n"
]
cell1['source'] = new_index

# Save
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("Step 2 done: section 3.5 added, section 4 deleted, renumbered")

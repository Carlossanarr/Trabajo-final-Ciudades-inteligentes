import json
import os

NOTEBOOK_PATH = 'Ciudades-TrabajoFinal.ipynb'

with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find the index of the "## 6. Dashboard interactivo" cell
insert_idx = -1
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'markdown':
        source = cell.get('source', [])
        if source:
            text = source[0] if isinstance(source, list) else source
            if text.startswith('## 6. Dashboard'):
                insert_idx = i
                break

if insert_idx == -1:
    print("Could not find section 6 to insert before it.")
    exit(1)

# Change "6. Dashboard interactivo" to "7. Dashboard interactivo"
dashboard_cell = nb['cells'][insert_idx]
new_source = []
for line in dashboard_cell['source']:
    if line.startswith('## 6. Dashboard'):
        new_source.append(line.replace('## 6.', '## 7.'))
    else:
        new_source.append(line)
nb['cells'][insert_idx]['source'] = new_source

cells_to_insert = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 5.5 Predicción de Serie Temporal de Contaminación (Estación MY1) <a id='5-5'></a>\n",
            "\n",
            "En este apartado implementaremos un modelo de clasificación para predecir si la contaminación por NO₂ va a subir, bajar o mantenerse estable en las próximas semanas. Nos centraremos en una estación concreta, **MY1** (Marylebone Road), al ser una estación *Kerbside* con altos niveles de contaminación donde la anticipación puede ser clave.\n",
            "\n",
            "Definiremos 3 clases basadas en la variación semanal:\n",
            "- **Estable**: Variación del $\\pm 5\\%$.\n",
            "- **Sube**: Incremento mayor al $5\\%$.\n",
            "- **Baja**: Decremento mayor al $5\\%$."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 1. Preparación de los datos y creación del Target\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "\n",
            "# Extraer serie temporal para la estación MY1\n",
            "if 'MY1' in no2_raw.columns:\n",
            "    my1_no2 = no2_raw[['MY1']].dropna()\n",
            "    \n",
            "    # Remuestrear a nivel semanal (media)\n",
            "    my1_weekly = my1_no2.resample('W').mean()\n",
            "    my1_weekly.columns = ['no2_mean']\n",
            "    \n",
            "    # Calcular el porcentaje de variación respecto a la semana anterior\n",
            "    my1_weekly['pct_change'] = my1_weekly['no2_mean'].pct_change() * 100\n",
            "    \n",
            "    # Definir la variable objetivo (Target)\n",
            "    # Sube (>5%), Baja (<-5%), Estable (entre -5% y +5%)\n",
            "    def classify_trend(pct):\n",
            "        if pd.isna(pct):\n",
            "            return np.nan\n",
            "        elif pct > 5.0:\n",
            "            return 2 # 'sube'\n",
            "        elif pct < -5.0:\n",
            "            return 0 # 'baja'\n",
            "        else:\n",
            "            return 1 # 'estable'\n",
            "            \n",
            "    my1_weekly['target'] = my1_weekly['pct_change'].apply(classify_trend)\n",
            "    \n",
            "    # Nombres de clases para reportes\n",
            "    class_names = ['Baja', 'Estable', 'Sube']\n",
            "    \n",
            "    print(\"Distribución de clases:\")\n",
            "    print(my1_weekly['target'].map({0:'Baja', 1:'Estable', 2:'Sube'}).value_counts())\n",
            "else:\n",
            "    print(\"La estación MY1 no se encuentra en el dataset no2_raw.\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Feature Engineering\n",
            "Creamos características (features) para ayudar al modelo a encontrar patrones temporales:\n",
            "1. **Lags (rezagos)**: Valores de las últimas 1 a 4 semanas.\n",
            "2. **Estacionalidad**: El mes del año.\n",
            "3. **Rolling means**: La media móvil de las últimas 4 semanas para suavizar la tendencia."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 2. Feature Engineering\n",
            "if 'MY1' in no2_raw.columns:\n",
            "    # Lags (1 a 4 semanas)\n",
            "    for i in range(1, 5):\n",
            "        my1_weekly[f'lag_{i}'] = my1_weekly['no2_mean'].shift(i)\n",
            "        \n",
            "    # Media móvil (últimas 4 semanas)\n",
            "    my1_weekly['rolling_mean_4w'] = my1_weekly['no2_mean'].rolling(window=4).mean()\n",
            "    \n",
            "    # Estacionalidad (mes)\n",
            "    my1_weekly['month'] = my1_weekly.index.month\n",
            "    \n",
            "    # Eliminar valores nulos generados por los lags y el rolling\n",
            "    df_model = my1_weekly.dropna().copy()\n",
            "    \n",
            "    print(f\"Dimensiones del dataset para el modelo: {df_model.shape}\")\n",
            "    display(df_model.head())"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Entrenamiento del Modelo (Random Forest)\n",
            "Utilizaremos un modelo **RandomForestClassifier** separando cronológicamente el dataset en Train, Validation y Test."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 3. Modelado y Entrenamiento\n",
            "from sklearn.ensemble import RandomForestClassifier\n",
            "from sklearn.metrics import accuracy_score, classification_report, confusion_matrix\n",
            "import seaborn as sns\n",
            "import matplotlib.pyplot as plt\n",
            "\n",
            "if 'MY1' in no2_raw.columns:\n",
            "    # Definir características predictoras (X) y objetivo (y)\n",
            "    features = ['no2_mean', 'lag_1', 'lag_2', 'lag_3', 'lag_4', 'rolling_mean_4w', 'month']\n",
            "    X = df_model[features]\n",
            "    y = df_model['target']\n",
            "    \n",
            "    # División Temporal: 70% Train, 15% Validation, 15% Test\n",
            "    n = len(df_model)\n",
            "    train_size = int(n * 0.70)\n",
            "    val_size = int(n * 0.15)\n",
            "    \n",
            "    X_train, y_train = X.iloc[:train_size], y.iloc[:train_size]\n",
            "    X_val, y_val = X.iloc[train_size:train_size+val_size], y.iloc[train_size:train_size+val_size]\n",
            "    X_test, y_test = X.iloc[train_size+val_size:], y.iloc[train_size+val_size:]\n",
            "    \n",
            "    print(f\"Train size: {len(X_train)} | Validation size: {len(X_val)} | Test size: {len(X_test)}\")\n",
            "    \n",
            "    # Instanciar y entrenar el modelo\n",
            "    rf_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')\n",
            "    rf_model.fit(X_train, y_train)\n",
            "    \n",
            "    # Evaluar Train y Validation\n",
            "    y_train_pred = rf_model.predict(X_train)\n",
            "    y_val_pred = rf_model.predict(X_val)\n",
            "    \n",
            "    acc_train = accuracy_score(y_train, y_train_pred)\n",
            "    acc_val = accuracy_score(y_val, y_val_pred)\n",
            "    \n",
            "    print(f\"\\nAccuracy Train: {acc_train:.4f}\")\n",
            "    print(f\"Accuracy Validation: {acc_val:.4f}\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Evaluación Final con Conjunto de Test"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 4. Evaluación en Test\n",
            "if 'MY1' in no2_raw.columns:\n",
            "    y_test_pred = rf_model.predict(X_test)\n",
            "    acc_test = accuracy_score(y_test, y_test_pred)\n",
            "    \n",
            "    print(f\"Accuracy Final de Test: {acc_test:.4f}\\n\")\n",
            "    print(\"Reporte de Clasificación (Test):\")\n",
            "    print(classification_report(y_test, y_test_pred, target_names=class_names, zero_division=0))\n",
            "    \n",
            "    # Matriz de confusión\n",
            "    cm = confusion_matrix(y_test, y_test_pred)\n",
            "    plt.figure(figsize=(6, 4))\n",
            "    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)\n",
            "    plt.title('Matriz de Confusión - Test Set')\n",
            "    plt.ylabel('Valor Real')\n",
            "    plt.xlabel('Predicción')\n",
            "    plt.show()\n",
            "    \n",
            "    # Importancia de las variables (Opcional)\n",
            "    importances = rf_model.feature_importances_\n",
            "    indices = np.argsort(importances)\n",
            "    \n",
            "    plt.figure(figsize=(8, 4))\n",
            "    plt.title(\"Importancia de Variables (Feature Importance)\")\n",
            "    plt.barh(range(len(indices)), importances[indices], color='cadetblue', align='center')\n",
            "    plt.yticks(range(len(indices)), [features[i] for i in indices])\n",
            "    plt.xlabel('Importancia Relativa')\n",
            "    plt.show()"
        ]
    }
]

# Insert the cells before the Dashboard section
for cell in reversed(cells_to_insert):
    nb['cells'].insert(insert_idx, cell)

with open(NOTEBOOK_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Insertion successful.")

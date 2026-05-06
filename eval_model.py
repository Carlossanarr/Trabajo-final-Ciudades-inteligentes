import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import json
import pathlib

DATA_DIR  = 'data_london'
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

def load_no2_station(station):
    path = f'{DATA_DIR}/raw/laqn/{station}/no2_pm25_o3_2019_2024.csv'
    df = pd.read_csv(path)
    df['ReadingDateTime'] = pd.to_datetime(df['ReadingDateTime'], dayfirst=True, format='mixed')
    no2 = df[df['Species'] == 'NO2'].set_index('ReadingDateTime')['Value']
    return no2[~no2.index.duplicated(keep='first')]

no2_raw = pd.DataFrame({s: load_no2_station(s) for s in STATION_INFO})
no2_raw = no2_raw.sort_index().asfreq('h')

my1_no2 = no2_raw[['MY1']].dropna()
my1_weekly = my1_no2.resample('W').mean()
my1_weekly.columns = ['no2_mean']
my1_weekly['pct_change'] = my1_weekly['no2_mean'].pct_change() * 100

def classify_trend(pct):
    if pd.isna(pct): return np.nan
    elif pct > 5.0: return 2
    elif pct < -5.0: return 0
    else: return 1

my1_weekly['target'] = my1_weekly['pct_change'].apply(classify_trend)

for i in range(1, 5):
    my1_weekly[f'lag_{i}'] = my1_weekly['no2_mean'].shift(i)
    
my1_weekly['rolling_mean_4w'] = my1_weekly['no2_mean'].rolling(window=4).mean()
my1_weekly['month'] = my1_weekly.index.month

df_model = my1_weekly.dropna().copy()
features = ['no2_mean', 'lag_1', 'lag_2', 'lag_3', 'lag_4', 'rolling_mean_4w', 'month']
X = df_model[features]
y = df_model['target']

n = len(df_model)
train_size = int(n * 0.70)
val_size = int(n * 0.15)

X_train, y_train = X.iloc[:train_size], y.iloc[:train_size]
X_val, y_val = X.iloc[train_size:train_size+val_size], y.iloc[train_size:train_size+val_size]
X_test, y_test = X.iloc[train_size+val_size:], y.iloc[train_size+val_size:]

rf_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
rf_model.fit(X_train, y_train)

y_train_pred = rf_model.predict(X_train)
y_val_pred = rf_model.predict(X_val)
y_test_pred = rf_model.predict(X_test)

print(f"Accuracy Train: {accuracy_score(y_train, y_train_pred):.4f}")
print(f"Accuracy Validation: {accuracy_score(y_val, y_val_pred):.4f}")
print(f"Accuracy Test: {accuracy_score(y_test, y_test_pred):.4f}")
print("\nClassification Report (Test):")
print(classification_report(y_test, y_test_pred, target_names=['Baja', 'Estable', 'Sube'], zero_division=0))

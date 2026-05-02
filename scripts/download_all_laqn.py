#!/usr/bin/env python3
"""
Descarga datos de NO2 (y PM2.5/O3 donde disponible) para las 61 estaciones LAQN
activas de Londres con datos desde 2019.
"""
from __future__ import annotations
import json, time, sys, io
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT     = Path(__file__).resolve().parents[1]
LAQN_DIR = ROOT / 'data_london' / 'raw' / 'laqn'
META_DIR = ROOT / 'data_london' / 'metadata'
LAQN_DIR.mkdir(parents=True, exist_ok=True)

# Cargar la lista de estaciones con NO2
with open(META_DIR / 'laqn_all_no2_stations.json', encoding='utf-8') as f:
    STATIONS = json.load(f)

print(f'Descargando {len(STATIONS)} estaciones LAQN...\n')

BASE_URL  = 'https://www.londonair.org.uk/london/asp/downloadsite.asp'
FILENAME  = 'no2_pm25_o3_2019_2024.csv'
PARAMS    = {
    'species1': 'NO2m',
    'species2': 'PM25m',
    'species3': 'O3m',
    'start':    '1-jan-2019',
    'end':      '1-jan-2024',
    'res':      '6',
    'period':   'hourly',
    'units':    'ugm3',
}

ok, skip, err = [], [], []
for s in STATIONS:
    code = s['code']
    dest = LAQN_DIR / code / FILENAME
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size > 5_000:
        print(f'  ↷ {code:6s}  ya existe ({dest.stat().st_size/1024:.0f} KB) — omitiendo')
        skip.append(code)
        continue

    url = BASE_URL + '?' + urlencode({'site': code, **PARAMS})
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=60) as r:
            data = r.read()
        dest.write_bytes(data)
        kb = len(data) / 1024
        print(f'  ✓ {code:6s}  {s["type"]:22s}  {kb:7.0f} KB  {s["name"]}')
        ok.append(code)
        time.sleep(0.4)
    except (HTTPError, URLError, TimeoutError) as e:
        print(f'  ✗ {code:6s}  ERROR: {e}')
        err.append(code)

print(f'\n── Resumen ───────────────────────────────')
print(f'  Descargadas :  {len(ok)}')
print(f'  Ya existían :  {len(skip)}')
print(f'  Errores     :  {len(err)}')
if err:
    print(f'  Fallidas    :  {err}')
print('Descarga completada.')

import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
nb = json.load(open('Ciudades-TrabajoFinal.ipynb', encoding='utf-8'))
for i, c in enumerate(nb['cells']):
    cid = c.get('id', '?')
    ct = c['cell_type']
    print(f"{i:2d} {ct:8s} {cid}")

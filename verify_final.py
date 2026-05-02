import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
nb = json.load(open('Ciudades-TrabajoFinal.ipynb', encoding='utf-8'))
print(f"Total cells: {len(nb['cells'])}")
print(f"JSON valid: OK")
print()
for i, c in enumerate(nb['cells']):
    ct = c['cell_type']
    cid = c.get('id', '?')
    src = ''.join(c['source'][:1])[:70].replace('\n', ' ')
    print(f"{i:2d} {ct:8s} {cid:14s} | {src}")

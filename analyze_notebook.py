import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

nb = json.load(open(r'Ciudades-TrabajoFinal.ipynb', encoding='utf-8'))

for i, cell in enumerate(nb['cells']):
    ct = cell['cell_type']
    cid = cell.get('id', '?')
    src = cell['source']
    nlines = len(src)
    preview = ''
    if src:
        preview = ''.join(src[:2])[:120].replace('\n', ' ')
    print(f"Cell {i:3d}  type={ct:8s}  id={cid:12s}  lines={nlines:4d}  | {preview}")

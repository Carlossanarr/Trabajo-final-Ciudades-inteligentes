"""Transform notebook: step 3 - Dashboard update, marker colors, weekly heatmap"""
import json

NB_PATH = 'Ciudades-TrabajoFinal.ipynb'
nb = json.load(open(NB_PATH, encoding='utf-8'))

# First, let's verify current cell structure
for i, c in enumerate(nb['cells']):
    cid = c.get('id', '?')
    ct = c['cell_type']
    preview = ''.join(c['source'][:1])[:60].replace('\n', ' ')
    print(f"Cell {i:2d} type={ct:8s} id={cid:12s} | {preview}")

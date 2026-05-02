import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

nb = json.load(open(r'Ciudades-TrabajoFinal.ipynb', encoding='utf-8'))

# Extract source of specific cells we need to modify
cells_to_read = [6, 11, 12, 16, 22, 24, 26, 28, 29, 30, 33, 34, 36, 41, 42, 43, 44, 45]
# Cell 6: data loading
# Cell 11-12: null analysis & filtering
# Cell 16: section 2.3 (boxplots)
# Cell 22,24,26,28: section 3 patterns
# Cell 29: dashboard NO2 block
# Cell 30,33: section 4 (model) - to delete
# Cell 34: section 5 markdown header
# Cell 36: section 5.1 map markers
# Cell 41: section 5.3 markdown
# Cell 42: section 5.4 heatmap
# Cell 43: dashboard maps block
# Cell 44-45: dashboard section

for i in cells_to_read:
    cell = nb['cells'][i]
    ct = cell['cell_type']
    cid = cell.get('id', '?')
    src = ''.join(cell['source'])
    print(f"{'='*80}")
    print(f"CELL {i} (type={ct}, id={cid})")
    print(f"{'='*80}")
    print(src)
    print()

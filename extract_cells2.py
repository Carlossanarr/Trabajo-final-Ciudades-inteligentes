import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
nb = json.load(open(r'Ciudades-TrabajoFinal.ipynb', encoding='utf-8'))
for i in [1, 19]:
    cell = nb['cells'][i]
    src = ''.join(cell['source'])
    print(f"{'='*80}")
    print(f"CELL {i} (type={cell['cell_type']}, id={cell.get('id','?')})")
    print(f"{'='*80}")
    print(src)
    print()

import json
import io

with open('Ciudades-TrabajoFinal.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

with io.open('headers.txt', 'w', encoding='utf-8') as f:
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] == 'markdown':
            source = c.get('source', [])
            if isinstance(source, list) and source:
                line = source[0].strip()
                if line.startswith('#'):
                    f.write(f"{i}: {line}\n")
            elif isinstance(source, str):
                line = source.split('\n')[0].strip()
                if line.startswith('#'):
                    f.write(f"{i}: {line}\n")

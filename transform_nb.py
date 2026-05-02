"""Transform notebook: step 1 - filtering criteria + WAB removal + remove right plot in 2.3"""
import json

NB_PATH = 'Ciudades-TrabajoFinal.ipynb'
nb = json.load(open(NB_PATH, encoding='utf-8'))

# --- Cell 12 (id=c010b): Change THRESH_YEAR from 60 to 50 ---
cell12 = nb['cells'][12]
src = ''.join(cell12['source'])
src = src.replace('THRESH_YEAR   = 60', 'THRESH_YEAR   = 50')
# Also exclude WAB from the second heatmap visualization
src = src.replace(
    "hm_data = yearly_null[null_pct.index]   # ordenado por nulo desc.",
    "hm_data = yearly_null[[c for c in null_pct.index if c != 'WAB']]   # ordenado por nulo desc., sin WAB"
)
cell12['source'] = [src]

# --- Cell 16 (id=c012): Remove right panel (KDE) from section 2.3 ---
cell16 = nb['cells'][16]
src16 = ''.join(cell16['source'])
# Replace 1,2 subplots with single plot
src16 = src16.replace("fig, axes = plt.subplots(1, 2, figsize=(18, 6))", "fig, ax_box = plt.subplots(figsize=(10, 6))")
# Replace axes[0] with ax_box
src16 = src16.replace("axes[0]", "ax_box")
# Remove Panel 2 block entirely
idx_panel2 = src16.find("# --- Panel 2: KDE por tipo ---")
idx_suptitle = src16.find("plt.suptitle(")
if idx_panel2 > 0 and idx_suptitle > 0:
    src16 = src16[:idx_panel2] + src16[idx_suptitle:]
cell16['source'] = [src16]

# Save
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("Step 1 done: filtering + WAB + right plot removed")

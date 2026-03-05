"""
fix_phase23.py — Apply Phase 2.3 targeted patches directly to notebook JSON.

Patches:
  1. Markdown cell #VSC-20e158b4 — update title + 102,505→134,042 + pipeline diagram
  2. Cell 3 #VSC-1577ce7c     — vectorized rarity lookups (pd.Series.map) +
                                  Geometric Stability Guard (np.clip -10..+10)
  3. Cell 5 #VSC-e2374cab     — update stale 351M / 102,505 medoid comments
"""

import json, re
from pathlib import Path

NB_PATH = Path(__file__).parent / 'main_folder' / 'Phase_2' / 'Phase_2_3_RAG_Inference_Bridge.ipynb'
assert NB_PATH.exists(), f'Notebook not found: {NB_PATH}'

nb = json.loads(NB_PATH.read_text(encoding='utf-8'))

def get_cell_source(cell):
    src = cell.get('source', [])
    return ''.join(src) if isinstance(src, list) else src

def set_cell_source(cell, text):
    cell['source'] = [line + ('\n' if not line.endswith('\n') else '')
                      for line in text.splitlines()]
    if cell['source']:
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

fixed = 0

for cell in nb['cells']:
    cell_id = cell.get('id', cell.get('metadata', {}).get('id', ''))
    src = get_cell_source(cell)

    # ── Patch 1: Markdown header ──────────────────────────────────────────────
    if cell_id == 'b1baa4c3':
        new_src = src.replace(
            '# Phase 2.3 — RAG Inference Bridge  `[v5.1]`',
            '# Phase 2.3 — RAG Inference Bridge  `[v5.1 — High-Speed Expert Retrieval]`'
        ).replace(
            'chromadb_store_v51/` — persistent HNSW store from Phase 2.2 (102,505 medoids)',
            'chromadb_store_v51/` — persistent HNSW store from Phase 2.2 (**134,042 medoids**)'
        ).replace(
            '[raw scale, up to 169.3 max]',
            '[clipped −10..+10, Geometric Stability Guard applied]'
        )
        if new_src != src:
            set_cell_source(cell, new_src)
            print('✅ Patch 1 applied: markdown header updated')
            fixed += 1
        else:
            print('⚠️  Patch 1: no changes detected (may already be patched)')

    # ── Patch 2: vectorize_v51 — rarity lookups + clip guard ─────────────────
    elif cell_id == '812de002':
        # 2a: vectorized rarity lookups (pd.Series.map instead of list comprehension)
        new_src = src.replace(
            '    sr = np.array([sport_rarity.get(p, DEFAULT_R) for p in sport_str], dtype=np.float64)\n'
            '    dr = np.array([dport_rarity.get(p, DEFAULT_R) for p in dport_str], dtype=np.float64)',
            '    # Optimized lookups\n'
            '    sr = pd.Series(sport_str).map(sport_rarity).fillna(DEFAULT_R).values.astype(np.float64)\n'
            '    dr = pd.Series(dport_str).map(dport_rarity).fillna(DEFAULT_R).values.astype(np.float64)'
        )
        # 2b: Geometric Stability Guard before nan_to_num
        new_src = new_src.replace(
            '    np.nan_to_num(X, nan=0., posinf=0., neginf=0., copy=False)\n    return X',
            '    # MANDATORY: Geometric Stability Guard\n'
            '    # Prevents outliers (like 69.0 max) from dominating similarity search\n'
            '    X = np.clip(X, -10.0, 10.0)\n'
            '\n'
            '    np.nan_to_num(X, nan=0., posinf=0., neginf=0., copy=False)\n'
            '    return X'
        )
        if new_src != src:
            set_cell_source(cell, new_src)
            print('✅ Patch 2 applied: vectorize_v51 rarity lookups vectorized + clip guard added')
            fixed += 1
        else:
            print('⚠️  Patch 2: no changes detected (may already be patched)')

    # ── Patch 3: Cell 5 — stale count comments ────────────────────────────────
    elif cell_id == '756ec5ff':
        new_src = src.replace(
            '#   - The 351M ocean was compressed to 102,505 medoids (3,427× ratio).',
            '#   - The 8.6M ocean was compressed to 134,042 medoids (~64× ratio).'
        )
        if new_src != src:
            set_cell_source(cell, new_src)
            print('✅ Patch 3 applied: Cell 5 stale counts updated')
            fixed += 1
        else:
            print('⚠️  Patch 3: no changes detected (may already be patched)')

print(f'\nTotal patches applied: {fixed}/3')

# Write back
NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'Notebook written: {NB_PATH}')

# ── Verification ──────────────────────────────────────────────────────────────
print('\n── Verification ─────────────────────────────────────────────────────')
text = NB_PATH.read_text(encoding='utf-8')
checks = [
    ('Title updated',          'High-Speed Expert Retrieval' in text),
    ('Medoid count 134,042',   '134,042 medoids' in text),
    ('Clip guard in pipeline',  'Geometric Stability Guard applied' in text),
    ('pd.Series.map rarity',   'pd.Series(sport_str).map(sport_rarity)' in text),
    ('np.clip guard added',    'np.clip(X, -10.0, 10.0)' in text),
    ('Stale 351M removed',     '351M' not in text),
]
for label, ok in checks:
    print(f'  {"✅" if ok else "❌"} {label}')

all_ok = all(ok for _, ok in checks)
print(f'\n{"All verifications passed ✅" if all_ok else "FAILED — check output above ❌"}')

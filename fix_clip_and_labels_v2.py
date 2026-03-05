"""
fix_clip_and_labels_v2.py
Applies two targeted fixes to Phase_2_1_Hybrid_Temporal_Curation.ipynb on disk:

  FIX 1 — Geometric Guard in vectorize_v51:
    Insert `np.clip(X, -10.0, 10.0, out=X)` immediately before the
    existing `np.nan_to_num(...)` line at the end of vectorize_v51.

  FIX 2 — Label Normalization in Step 3 Consolidation:
    After `meta['ubt_archetype'] = arch  # guarantee correct label`
    insert the label-lowercase line for univ_specific_attack.
"""

import json, pathlib, sys, re

NB_PATH = pathlib.Path(
    r"main_folder\Phase_2\Phase_2_1_Hybrid_Temporal_Curation.ipynb"
)

nb = json.loads(NB_PATH.read_text(encoding='utf-8'))

# ── helpers ───────────────────────────────────────────────────────────────────

def find_cell_by_id(cells, cell_id):
    for i, c in enumerate(cells):
        if c.get('id') == cell_id:
            return i, c
    return None, None

def source_lines(cell):
    """Return the cell's source as a Python list of strings (already has \n)."""
    s = cell.get('source', [])
    if isinstance(s, list):
        return list(s)
    return s.splitlines(keepends=True)

def set_source(cell, lines):
    cell['source'] = lines

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: Geometric Guard
#   Target cell: #VSC-1bfae4ad  (vectorize_v51)
#   Find the line:  np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0, copy=False)
#   Insert BEFORE it: np.clip(X, -10.0, 10.0, out=X)
# ─────────────────────────────────────────────────────────────────────────────

VECT_CELL_ID = '129d087f'

idx, vect_cell = find_cell_by_id(nb['cells'], VECT_CELL_ID)
assert vect_cell is not None, f'Could not find cell {VECT_CELL_ID}'

lines = source_lines(vect_cell)

# Check if already patched
already_clipped = any('np.clip(X, -10.0, 10.0' in ln for ln in lines)
if already_clipped:
    print('FIX 1 SKIP — np.clip(X, -10.0, 10.0) already present in vectorize_v51')
else:
    # Find the nan_to_num line
    nan_idx = next(
        (i for i, ln in enumerate(lines) if 'np.nan_to_num' in ln and 'copy=False' in ln),
        None
    )
    assert nan_idx is not None, 'Could not find np.nan_to_num line in vectorize_v51'

    # Determine indentation from nan_to_num line
    indent = re.match(r'^(\s*)', lines[nan_idx]).group(1)

    clip_comment = f'{indent}# GEOMETRIC GUARD: clip outliers to [-10, 10] to prevent dimension domination\n'
    clip_line    = f'{indent}np.clip(X, -10.0, 10.0, out=X)\n'

    lines.insert(nan_idx, clip_line)
    lines.insert(nan_idx, clip_comment)
    set_source(vect_cell, lines)
    print(f'FIX 1 APPLIED — inserted np.clip before line {nan_idx} in vectorize_v51')

# ─────────────────────────────────────────────────────────────────────────────
# FIX 2: Label Normalization
#   Target cell: #VSC-6e3a7f99  (Step 3 Consolidation)
#   Find the line:  meta['ubt_archetype'] = arch  # guarantee correct label
#   Insert AFTER it: meta['univ_specific_attack'] = meta['univ_specific_attack'].astype(str)...
# ─────────────────────────────────────────────────────────────────────────────

CONSOL_CELL_ID = '2ba79f8a'

idx2, consol_cell = find_cell_by_id(nb['cells'], CONSOL_CELL_ID)
assert consol_cell is not None, f'Could not find cell {CONSOL_CELL_ID}'

lines2 = source_lines(consol_cell)

already_lower = any('univ_specific_attack' in ln and '.str.lower()' in ln for ln in lines2)
if already_lower:
    print('FIX 2 SKIP — label normalization already present in consolidation cell')
else:
    # Find anchor line
    anchor_idx = next(
        (i for i, ln in enumerate(lines2)
         if "meta['ubt_archetype'] = arch" in ln and 'guarantee' in ln),
        None
    )
    assert anchor_idx is not None, "Could not find anchor 'meta['ubt_archetype'] = arch' line"

    indent2 = re.match(r'^(\s*)', lines2[anchor_idx]).group(1)

    norm_comment = f"{indent2}# Normalise label case: Benign / benign / BENIGN → benign\n"
    norm_line    = (
        f"{indent2}meta['univ_specific_attack'] = (\n"
        f"{indent2}    meta['univ_specific_attack'].astype(str).str.lower().str.strip()\n"
        f"{indent2})\n"
    )

    lines2.insert(anchor_idx + 1, norm_line)
    lines2.insert(anchor_idx + 1, norm_comment)
    set_source(consol_cell, lines2)
    print(f'FIX 2 APPLIED — inserted label normalization after line {anchor_idx} in consolidation')

# ── Write back ────────────────────────────────────────────────────────────────
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('\n✅ Notebook saved to disk with both fixes applied.')

# ── Verify ────────────────────────────────────────────────────────────────────
nb2 = json.loads(NB_PATH.read_text(encoding='utf-8'))
_, vc2 = find_cell_by_id(nb2['cells'], '129d087f')
_, cc2 = find_cell_by_id(nb2['cells'], '2ba79f8a')

src_v = ''.join(vc2['source'])
src_c = ''.join(cc2['source'])

ok1 = 'np.clip(X, -10.0, 10.0, out=X)' in src_v
ok2 = 'np.nan_to_num' in src_v
ok3 = 'univ_specific_attack' in src_c and '.str.lower()' in src_c

print(f'\nVerification:')
print(f'  np.clip(-10,10) in vectorize_v51     : {"✅" if ok1 else "❌ MISSING"}')
print(f'  np.nan_to_num still present          : {"✅" if ok2 else "❌ MISSING"}')
print(f'  label normalization in consolidation : {"✅" if ok3 else "❌ MISSING"}')

# Also confirm clip precedes nan_to_num
lines_v2 = source_lines(vc2)
clip_pos   = next((i for i, ln in enumerate(lines_v2) if 'np.clip(X, -10.0' in ln), -1)
nan_pos    = next((i for i, ln in enumerate(lines_v2) if 'np.nan_to_num' in ln), -1)
print(f'  clip line index: {clip_pos}, nan_to_num line index: {nan_pos}')
print(f'  clip before nan_to_num               : {"✅" if 0 <= clip_pos < nan_pos else "❌"}')

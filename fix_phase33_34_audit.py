# fix_phase33_34_audit.py
# Applies 4 targeted audit corrections:
#   1. Phase 3.3 Cell ef8f49f0: remove ** 2 from recurrence_score inside np.sqrt
#   2. Phase 3.4 cell 292e394d (markdown): Dempster+ -> Amplitude Superposition
#   3. Phase 3.4 cell fee4bee4: rename conflict_factor_K -> entropy_uncertainty
import json
from pathlib import Path

def patch(nb_path, replacements):
    path = Path(nb_path)
    nb = json.loads(path.read_text(encoding='utf-8'))
    cells = {c['id']: c for c in nb['cells']}
    applied = 0
    for cell_id, old, new in replacements:
        cell = cells.get(cell_id)
        if cell is None:
            print(f'  [!!] cell {cell_id} not found in {nb_path}')
            continue
        src = ''.join(cell['source'])
        if old not in src:
            print(f'  [!!] string not found in cell {cell_id}: {repr(old[:60])}')
            continue
        new_src = src.replace(old, new, 1)
        lines = new_src.splitlines(keepends=True)
        if lines and lines[-1].endswith('\n'):
            lines[-1] = lines[-1][:-1]
        cell['source'] = lines
        if cell.get('cell_type') == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
        print(f'  [OK] patched cell {cell_id}: {repr(old[:55])} -> {repr(new[:55])}')
        applied += 1
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'  Wrote {path}  ({applied}/{len(replacements)} patches)')
    return applied

# ── Phase 3.3 ─────────────────────────────────────────────────────────────────
patch(
    'main_folder/Phase_3/Phase_3_3_Quantum_Knowledge_Fusion.ipynb',
    [
        (
            'ef8f49f0',
            'evidence.count * evidence.avg_similarity * (evidence.recurrence_score ** 2)',
            'evidence.count * evidence.avg_similarity * evidence.recurrence_score',
        ),
    ]
)

# ── Phase 3.4 ─────────────────────────────────────────────────────────────────
patch(
    'main_folder/Phase_3/Phase_3_4_Explainability_Alert_Generation.ipynb',
    [
        (
            '292e394d',
            '\u2192 Dempster\u2295 accumulation        [Phase 3.2]',
            '\u2192 Amplitude Superposition    [Phase 3.2]',
        ),
        (
            'fee4bee4',
            "'conflict_factor_K'     : round(conflict_level, 6),",
            "'entropy_uncertainty'   : round(conflict_level, 6),",
        ),
    ]
)

# ── Verify ────────────────────────────────────────────────────────────────────
print('\n-- Verification --')
t33 = Path('main_folder/Phase_3/Phase_3_3_Quantum_Knowledge_Fusion.ipynb').read_text(encoding='utf-8')
t34 = Path('main_folder/Phase_3/Phase_3_4_Explainability_Alert_Generation.ipynb').read_text(encoding='utf-8')

checks = [
    ('3.3: recurrence_score ** 2 removed',   'recurrence_score ** 2' not in t33),
    ('3.3: recurrence_score still present',  'recurrence_score' in t33),
    ('3.4: Dempster removed',                'Dempster' not in t34),
    ('3.4: Amplitude Superposition added',   'Amplitude Superposition' in t34),
    ('3.4: conflict_factor_K removed',       'conflict_factor_K' not in t34),
    ('3.4: entropy_uncertainty added',       'entropy_uncertainty' in t34),
]
for label, ok in checks:
    print(f'  {"[OK]" if ok else "[!!]"} {label}')
all_ok = all(ok for _, ok in checks)
print(f'\n{"All checks passed" if all_ok else "FAILED"}')

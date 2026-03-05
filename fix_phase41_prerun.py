# fix_phase41_prerun.py
# Pre-run fixes for Phase_4_1_System_Evaluation.ipynb
#   1. Markdown: AdaptiveTimeWindow -> StaticTimeWindow
#   2. Markdown: Dempster-Shafer -> Evidence Accumulation
#   3. Cell 1: typo "Phase 4.2" -> "Phase 4.1"
#   4. Cell 4 quantum_fusion(): (recurrence ** 2) -> recurrence (Born rule fix)
import json
from pathlib import Path

NB = Path('main_folder/Phase_4/Phase_4_1_System_Evaluation.ipynb')
nb = json.loads(NB.read_text(encoding='utf-8'))

# build cell-id -> cell index map using JSON-native ids
id_to_cell = {}
for c in nb['cells']:
    cid = c.get('id', '')
    id_to_cell[cid] = c

def patch_cell(cell_id, old, new, label):
    c = id_to_cell.get(cell_id)
    if c is None:
        print(f'  [!!] cell {cell_id} not found')
        return False
    src = ''.join(c['source'])
    if old not in src:
        print(f'  [!!] string not found in {cell_id}: {repr(old[:55])}')
        return False
    new_src = src.replace(old, new, 1)
    lines = new_src.splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1][:-1]
    c['source'] = lines
    if c.get('cell_type') == 'code':
        c['outputs'] = []
        c['execution_count'] = None
    print(f'  [OK] {label}')
    return True

# ── 1. Markdown: pipeline stage labels ────────────────────────────────────────
MARKDOWN_ID = '15fb6eef'
patch_cell(MARKDOWN_ID,
    '\u2192 AdaptiveTimeWindow       [Phase 3.1 \u2014 deque buffer, linear \u00b1steps]',
    '\u2192 StaticTimeWindow         [Phase 3.1 \u2014 deque buffer, fixed 30s window]',
    'Markdown: AdaptiveTimeWindow -> StaticTimeWindow')
patch_cell(MARKDOWN_ID,
    '\u2192 accumulate_evidence      [Phase 3.2 \u2014 Dempster-Shafer sequential fusion]',
    '\u2192 accumulate_evidence      [Phase 3.2 \u2014 Evidence Accumulation]',
    'Markdown: Dempster-Shafer -> Evidence Accumulation')

# ── 2. Cell 1 typo ─────────────────────────────────────────────────────────────
CELL1_ID = 'c7e583ab'
patch_cell(CELL1_ID,
    'Phase 4.2 \u2014 System Hardening imports ready.',
    'Phase 4.1 \u2014 System Evaluation imports ready.',
    'Cell 1: Phase 4.2 -> Phase 4.1')

# ── 3. Cell 4: quantum_fusion recurrence ** 2 bug ──────────────────────────────
CELL4_ID = 'e863d6b6'
patch_cell(CELL4_ID,
    'amp = math.sqrt(max(count * avg_sim * (recurrence ** 2), 0.0))',
    'amp = math.sqrt(max(count * avg_sim * recurrence, 0.0))',
    'Cell 4 quantum_fusion: remove recurrence ** 2')

NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')

# ── Verify ────────────────────────────────────────────────────────────────────
t = NB.read_text(encoding='utf-8')
checks = [
    ('AdaptiveTimeWindow removed from markdown', 'AdaptiveTimeWindow' not in t),
    ('StaticTimeWindow in markdown',             'StaticTimeWindow' in t),
    ('Dempster-Shafer removed from markdown',    'Dempster-Shafer' not in t),
    ('Cell 1 typo fixed (4.2 removed)',          'Phase 4.2' not in t),
    ('recurrence ** 2 removed from Cell 4',      '(recurrence ** 2)' not in t),
    ('recurrence still in Cell 4',               'recurrence' in t),
]
print()
for label, ok in checks:
    print(f'  {"[OK]" if ok else "[!!]"} {label}')
print()
print('All passed' if all(ok for _,ok in checks) else 'SOME FAILED')

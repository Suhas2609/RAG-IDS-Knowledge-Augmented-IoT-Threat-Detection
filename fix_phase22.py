"""
fix_phase22.py
Applies all Phase 2.2 corrections to the notebook on disk via JSON parsing.

Changes:
  1. Markdown Cell (#VSC-cfc38387): update medoid counts 102505→134042 and table rationale
  2. Cell 3 (#VSC-7e8d64ee): add label lowercase guard, fix shape comments, update print header
  3. Cell 4 (#VSC-23e4cb2d): fix description string in HNSW metadata
  4. Cell 5 (#VSC-379f844d): fix batch ID prefix kb_→kb_v51_, doc separator |→space
"""

import json, pathlib, re

NB_PATH = pathlib.Path(
    r"main_folder\Phase_2\Phase_2_2_Vector_Store_Ingestion.ipynb"
)

nb = json.loads(NB_PATH.read_text(encoding='utf-8'))

def get_src(cell):
    s = cell.get('source', [])
    return ''.join(s) if isinstance(s, list) else s

def set_src(cell, text):
    cell['source'] = [line + ('\n' if not line.endswith('\n') else '')
                      for line in text.splitlines()]
    # Fix last line — no trailing newline
    if cell['source']:
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

fixed = {}

for cell in nb['cells']:
    cid = cell.get('id', '')
    src = get_src(cell)

    # ── FIX 1: Markdown ──────────────────────────────────────────────────────
    if cid == '#VSC-cfc38387' or (cell.get('cell_type') == 'markdown'
                                   and '102,505-row Knowledge Base' in src):
        src = src.replace('102,505-row Knowledge Base', '134,042-row Knowledge Base')
        src = src.replace('*(102505, 114)*', '*(134042, 114)*')
        # Update table rationale for L2 step
        old_l2 = ('| **1. L2 Normalisation** | Unit-normalise every 114-dim vector '
                  '| Neutralises the 169.3 Global Max outlier — prevents high-magnitude '
                  'features (e.g. packet bytes) from dominating cosine distance |')
        new_l2 = ('| **1. L2 Normalisation** | Unit-normalise every 114-dim vector '
                  '| Projects vectors onto the unit sphere — after the Phase 2.1 '
                  'Geometric Stability Guard $[-10, 10]$, remaining variance encodes '
                  'direction, not magnitude; L2 norm makes cosine ≡ dot-product for HNSW |')
        src = src.replace(old_l2, new_l2)
        # Update cosine row
        old_cos = ('| **2. Cosine HNSW** | `hnsw:space = \'cosine\'` | After L2 normalisation, '
                   'cosine ≡ dot-product — maximally captures *behavioural direction* rather than raw magnitude |')
        new_cos = ('| **2. Cosine HNSW** | `hnsw:space = \'cosine\'` | After L2 normalisation, '
                   'cosine similarity is bounded in $[0, 2]$ and equals the dot-product — '
                   'the fastest operation HNSW can evaluate at each graph edge |')
        src = src.replace(old_cos, new_cos)
        # Update HNSW row
        src = src.replace('sub-10 ms on 102K vectors', 'sub-10 ms on 134K vectors')
        src = src.replace('avoids the OOM crashes from Phase 2.1', 'avoids OOM during indexing')
        set_src(cell, src)
        fixed['markdown'] = True
        print('FIX 1 APPLIED — Markdown cell updated (102505 → 134042)')

    # ── FIX 2: Cell 3 (Data Loading & L2 Norm) ────────────────────────────────
    elif cid == '#VSC-7e8d64ee' or (cell.get('cell_type') == 'code'
                                      and 'Loading knowledge base' in src):
        # Update shape comments
        src = src.replace('# (102505, 114) float32', '# (134042, 114) float32')
        src = src.replace('# (102505, 3)', '# (134042, 3)')
        # Update print header to say "high-fidelity" and "clipped"
        src = src.replace("print('Loading knowledge base …')",
                          "print('Loading high-fidelity knowledge base …')")
        src = src.replace("  Global Min / Max (raw)", "  Global Min / Max (clipped)")
        # Update L2 norm subheader
        src = src.replace("print('\\nApplying L2 normalisation …')",
                          "print('\\nApplying L2 normalisation (Unit Sphere projection) …')")
        # Update norms comment
        src = src.replace('# (102505, 1)', '# (134042, 1)')
        # Update deviation print label
        src = src.replace("  Max deviation from |v|=1  : {_max_deviation:.2e}  (should be < 1e-6)",
                          "  Max unit-norm deviation: {_max_deviation:.2e}")
        src = src.replace("  Zero-norm vectors (raw)   :", "  Zero-norm vectors (raw):")

        # Add label guard after pd.read_parquet line (if not already present)
        if '.str.lower().str.strip()' not in src:
            old_line = "y_meta = pd.read_parquet(str(META_PATH))      # (134042, 3)"
            new_block = (
                "y_meta = pd.read_parquet(str(META_PATH))      # (134042, 3)\n\n"
                "# Final safety guard: normalise label case (Benign/benign/BENIGN → benign)\n"
                "y_meta['univ_specific_attack'] = y_meta['univ_specific_attack'].astype(str).str.lower().str.strip()"
            )
            src = src.replace(old_line, new_block)

        set_src(cell, src)
        fixed['cell3'] = True
        print('FIX 2 APPLIED — Cell 3: label guard + shape comments + print labels')

    # ── FIX 3: Cell 4 (ChromaDB Init) ─────────────────────────────────────────
    elif cid == '#VSC-23e4cb2d' or (cell.get('cell_type') == 'code'
                                      and 'RAG-IDS Knowledge Base v5.1' in src
                                      and '102505 medoids' in src):
        src = src.replace(
            "'RAG-IDS Knowledge Base v5.1 — 102505 medoids, 114-dim, L2-normalised'",
            "'RAG-IDS Knowledge Base v5.1 — 134042 medoids, 114-dim, L2-normalised, clipped[-10,10]'"
        )
        set_src(cell, src)
        fixed['cell4'] = True
        print('FIX 3 APPLIED — Cell 4: HNSW description string updated')

    # ── FIX 4: Cell 5 (Batch Ingestion) ───────────────────────────────────────
    elif cid == '#VSC-379f844d' or (cell.get('cell_type') == 'code'
                                     and "batch_ids = [f'kb_{i}'" in src):
        # Fix ID prefix
        src = src.replace("batch_ids = [f'kb_{i}' for i in range(lo, hi)]",
                          "batch_ids = [f'kb_v51_{i}' for i in range(lo, hi)]")
        # Fix document separator | → space
        src = src.replace(
            "f\"{row['ubt_archetype']}|{row['univ_specific_attack']}|{row['dataset_source']}\"",
            "f\"{row['ubt_archetype']} {row['univ_specific_attack']} {row['dataset_source']}\""
        )
        set_src(cell, src)
        fixed['cell5'] = True
        print('FIX 4 APPLIED — Cell 5: batch ID prefix kb_v51_, document separator space')

# ── Write back ────────────────────────────────────────────────────────────────
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('\n✅ Phase 2.2 notebook saved.')

# ── Verify on disk ─────────────────────────────────────────────────────────────
text = NB_PATH.read_text(encoding='utf-8')
checks = {
    '134,042-row Knowledge Base' : '134,042-row KB in markdown',
    '134042 medoids'              : '134042 in HNSW description',
    'kb_v51_'                     : 'kb_v51_ ID prefix in Cell 5',
    'str.lower().str.strip()'     : 'label guard in Cell 3',
    'clipped'                     : 'clipped mention',
    'Global Min / Max (clipped)'  : 'clipped range label',
}
print('\nVerification:')
all_ok = True
for needle, label in checks.items():
    ok = needle in text
    all_ok = all_ok and ok
    print(f'  {"✅" if ok else "❌"} {label}')

if not all_ok:
    print('\n⚠️  Some checks failed — review above.')
else:
    print('\nAll checks passed. ✅')

print(f'\nFixed cells: {list(fixed.keys())}')

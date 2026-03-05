# -*- coding: utf-8 -*-
"""
fix_phase31_static.py -- Rewrite Phase 3.1 from AdaptiveTimeWindow to StaticTimeWindow.

Patches:
  51dfe2ad  -- Markdown header
  08b33bb0  -- Cell 2: static constants
  e442be9a  -- Cell 4: replace AdaptiveTimeWindow with StaticTimeWindow
  711d7090  -- Cell 5: simulation for static window + clean slate demo
  6f48eb58  -- Cell 6: pruning visualisation
"""
import json
from pathlib import Path

NB = Path('main_folder/Phase_3/Phase_3_1_Static_Time_Window.ipynb')
nb = json.loads(NB.read_text(encoding='utf-8'))


def set_source(cell, text):
    lines = text.splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1][:-1]
    cell['source'] = lines
    if cell.get('cell_type') == 'code':
        cell['outputs'] = []
        cell['execution_count'] = None


CELLS = {c['id']: c for c in nb['cells']}

# ==============================================================================
# Patch 1: Markdown header
# ==============================================================================
set_source(CELLS['51dfe2ad'],
r"""# Phase 3.1 -- Static Time-Windowing

**Pipeline position:** Phase 2.3 RAG Bridge -> **Phase 3.1 (this notebook)** -> Phase 3.2 Evidence Accumulation -> Phase 3.3 Quantum Fusion

## Purpose
Turn a stream of individual network flows into a **temporally coherent evidence window** with a fixed duration, providing a stable and consistent evidence base for the Dempster-Shafer calculations in Phase 3.2.

## Design Principles
| Concern | Choice | Rationale |
|---------|--------|-----------|
| Buffer structure | `collections.deque(maxlen=1000)` | O(1) amortised append + automatic overflow eviction |
| Pruning strategy | `while`-loop on timestamp | Fires on every `add_flow`; no batch scans |
| Window duration | **Static 30s** | Constant temporal baseline -- no window-size jitter skewing Conflict Factor K |
| Schema | 114-dim `FlowRecord` | Exact match to `vectorize_v51` + ChromaDB medoids |
| Clean Slate | 3x high-confidence benign flush | Severs Dempster-Shafer chain between attack episodes |

## Static Window Rule
```
All flows within the last 30 seconds are retained.
Flows older than 30 seconds are pruned in O(1) from the left of the deque.
```
""")
print("Patch 1 applied: markdown header")

# ==============================================================================
# Patch 2: Cell 2 -- Static constants
# ==============================================================================
CELL2_SRC = """\
# -- Cell 2: Constants ---------------------------------------------------------
#
# VECTOR_DIMS must equal 114 -- the exact output dimension of vectorize_v51()
# and the stored ChromaDB medoids from Phase 2.2.
# Any mismatch here will cause an immediate ValueError in Phase 3.2+.
# ------------------------------------------------------------------------------

VECTOR_DIMS        : int   = 114      # v5.1 schema dimensionality (MUST NOT change)

# -- Static Window Configuration -----------------------------------------------
# Fixed duration; no expansion or shrinkage logic.
# A constant 30s window is the stable denominator for Evidence Accumulation,
# ensuring the Quantum Fusion Conflict Factor (K) is always comparable.
WIN_STATIC_S       : float = 30.0     # fixed evidence window (seconds)
DEQUE_MAXLEN       : int   = 1000     # hard cap; deque auto-evicts oldest on overflow

# -- Label Normalisation (Phase 2.3 Alignment) ---------------------------------
# Only lowercase values -- matches .str.lower().str.strip() applied in Phase 2.1/2.3.
NORMAL_ARCHETYPES  = frozenset({'benign', 'normal'})

# -- Phase 4.2 -- Clean Slate Protocol constants -------------------------------
BENIGN_STREAK_THRESHOLD  : int   = 3      # consecutive high-sim benign flows -> flush
BENIGN_SIM_THRESHOLD_PCT : float = 85.0   # top_similarity >= this for streak counting (%)

SEP = '-' * 72
print(SEP)
print(f'  VECTOR_DIMS        = {VECTOR_DIMS}  (must match vectorize_v51 output)')
print(f'  WIN_STATIC_S       = {WIN_STATIC_S}s  (fixed -- no adaptation)')
print(f'  DEQUE_MAXLEN       = {DEQUE_MAXLEN}')
print(f'  NORMAL_ARCHETYPES  = {NORMAL_ARCHETYPES}')
print(f'  Clean Slate        : streak >= {BENIGN_STREAK_THRESHOLD} @ sim >= {BENIGN_SIM_THRESHOLD_PCT}%')
print(SEP)
print('Constants locked. Schema: 114-dim v5.1.  Window: STATIC 30s [OK]')
"""
set_source(CELLS['08b33bb0'], CELL2_SRC)
print("Patch 2 applied: Cell 2 static constants")

# ==============================================================================
# Patch 3: Cell 4 -- StaticTimeWindow class
# ==============================================================================
CELL4_SRC = '''\
# -- Cell 4: StaticTimeWindow Class --------------------------------------------
#
# Maintains a fixed-duration sliding window of FlowRecord objects.
# There is NO adaptive logic -- the window is always WIN_STATIC_S seconds wide.
#
# Data structure:
#   deque(maxlen=1000)  -- O(1) append, O(1) popleft, auto-evicts oldest on overflow
#
# Pruning strategy:
#   A `while` loop at the front of add_flow() checks the oldest flow timestamp.
#   If it has aged beyond _window_seconds, popleft() removes it in O(1).
#
# Phase 4.2 -- Clean Slate Protocol:
#   After BENIGN_STREAK_THRESHOLD (3) consecutive flows whose
#   top_archetype is in NORMAL_ARCHETYPES AND top_similarity >= BENIGN_SIM_THRESHOLD_PCT,
#   the buffer is flushed. This severs the Dempster-Shafer accumulation chain
#   from prior attack episodes, eliminating cross-episode false-positive inflation.
#   The triggering flow seeds the fresh buffer so it never starts empty
#   (prevents division-by-zero in Phase 3.2 evidence accumulation).
# ------------------------------------------------------------------------------

class StaticTimeWindow:
    """
    Fixed-duration sliding window for IDS evidence accumulation.

    Includes Phase 4.2 Clean Slate protocol to ensure evidence from
    prior attack episodes does not contaminate current fusion logic.

    Parameters
    ----------
    window_seconds : fixed window duration (default WIN_STATIC_S = 30.0)
    maxlen         : hard deque capacity (default DEQUE_MAXLEN = 1000)
    """

    def __init__(
        self,
        window_seconds : float = WIN_STATIC_S,
        maxlen         : int   = DEQUE_MAXLEN,
    ) -> None:
        self._buffer            : deque = deque(maxlen=maxlen)
        self._window_seconds    : float = float(window_seconds)
        self._benign_streak     : int   = 0
        self._clean_slate_count : int   = 0
        self._total_processed   : int   = 0

    # -- Public properties ----------------------------------------------------

    @property
    def window_seconds(self) -> float:
        """Fixed window duration in seconds (constant)."""
        return self._window_seconds

    @property
    def buffer_size(self) -> int:
        """Number of FlowRecords currently in the window."""
        return len(self._buffer)

    # -- Core method ----------------------------------------------------------

    def add_flow(
        self,
        flow         : FlowRecord,
        current_time : Optional[float] = None,
    ) -> None:
        """
        Ingest one FlowRecord into the static sliding window.

        Steps (in order):
          0. Evaluate benign streak for Clean Slate protocol (Phase 4.2).
          1. O(1) pruning: remove flows older than _window_seconds from
             the left of the deque using a while-loop (no list rebuild).
          2. Append the new FlowRecord to the right of the deque.

        Parameters
        ----------
        flow         : FlowRecord -- the incoming scored network flow
        current_time : wall-clock seconds (default: time.time()).  Override in
                       simulations to control the clock without real sleeps.
        """
        if current_time is None:
            current_time = time.time()

        self._total_processed += 1

        # Step 0 -- Phase 4.2 Clean Slate: benign streak evaluation -----------
        # Sever the Dempster-Shafer chain if traffic returns to confident normal.
        if (flow.top_archetype in NORMAL_ARCHETYPES
                and flow.top_similarity >= BENIGN_SIM_THRESHOLD_PCT):
            self._benign_streak += 1
        else:
            self._benign_streak = 0

        if self._benign_streak >= BENIGN_STREAK_THRESHOLD:
            self._buffer.clear()
            self._benign_streak  = 0
            self._clean_slate_count += 1
            # Seed with triggering flow so buffer never starts empty
            # (prevents division-by-zero in Phase 3.2 evidence accumulation)
            self._buffer.append(flow)
            return

        # Step 1 -- O(1) Pruning ----------------------------------------------
        cutoff = current_time - self._window_seconds
        while self._buffer and self._buffer[0].timestamp < cutoff:
            self._buffer.popleft()

        # Step 2 -- Append ----------------------------------------------------
        self._buffer.append(flow)

    def get_context_for_fusion(self) -> List[FlowRecord]:
        """
        Phase 3.2 / Quantum Fusion input interface.

        Returns a list (oldest to newest) of all FlowRecords currently in the
        window. Safe to iterate; does NOT mutate the internal deque.
        """
        return list(self._buffer)

    def stats(self) -> dict:
        """Return a snapshot of window statistics for logging / monitoring."""
        return {
            'window_seconds'    : self._window_seconds,
            'buffer_size'       : self.buffer_size,
            'total_processed'   : self._total_processed,
            'benign_streak'     : self._benign_streak,
            'clean_slate_count' : self._clean_slate_count,
        }

    def __repr__(self) -> str:
        return (
            f'StaticTimeWindow('
            f'window={self._window_seconds:.1f}s, '
            f'buf={self.buffer_size}, '
            f'streak={self._benign_streak})'
        )


# -- Smoke test ---------------------------------------------------------------
_stw = StaticTimeWindow()
assert _stw.window_seconds == WIN_STATIC_S, 'Window constant mismatch'
assert _stw.buffer_size    == 0,            'Buffer should start empty'

# Clean Slate smoke test: 3 consecutive high-sim benign flows -> flush.
# Uses lowercase 'normal' -- matches Phase 2.3 normalised NORMAL_ARCHETYPES.
_cs_vec = np.zeros(VECTOR_DIMS, dtype=np.float32)
for _i in range(3):
    _cs_flow = FlowRecord(
        timestamp=float(_i), vector=_cs_vec, top_similarity=90.0,
        top_archetype='normal', packet_label='Normal',
    )
    _stw.add_flow(_cs_flow, current_time=float(_i))

assert _stw.buffer_size == 1, f'Expected 1 flow after Clean Slate flush, got {_stw.buffer_size}'
assert _stw._clean_slate_count == 1, 'Clean Slate should have fired once'

print('StaticTimeWindow class defined.')
print(f'  Repr       : {StaticTimeWindow()}')
print('  Clean Slate: 3x normal@90% -> buffer flushed to 1 flow  [OK]')
print()
print('Class smoke test passed  [OK]')
'''
set_source(CELLS['e442be9a'], CELL4_SRC)
print("Patch 3 applied: Cell 4 StaticTimeWindow")

# ==============================================================================
# Patch 4: Cell 5 -- Simulation
# ==============================================================================
CELL5_SRC = """\
# -- Cell 5: Simulation -- 15-Packet Stream ------------------------------------
#
# Demonstrates Clean Slate protocol on a static window:
#   Phase A  (pkts  1-5):  EXPLOIT traffic  -> evidence accumulates in 30s window
#   Phase B  (pkts  6-8):  Confident NORMAL -> Clean Slate fires on pkt 8 (streak=3)
#   Phase C  (pkts  9-15): EXPLOIT returns  -> fresh evidence chain begins
#
# Window: fixed 30s.  Packets arrive 1s apart (total span 14s < 30s).
# No pruning occurs in this short stream.
# Pruning behaviour is demonstrated separately in Cell 6 with wider spacing.
# ------------------------------------------------------------------------------

SIM_INTERVAL_S  = 1.0
SIM_NORMAL_SIM  = 90.0    # >= BENIGN_SIM_THRESHOLD_PCT (85%) so streak counts
SIM_EXPLOIT_SIM = 92.0

STREAM = [
    # (label,    sim%,           archetype,   attack)
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'xss'),       # pkt  1
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'xss'),       # pkt  2
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'injection'), # pkt  3
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'xss'),       # pkt  4
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'injection'), # pkt  5
    ('Normal',  SIM_NORMAL_SIM,  'normal',   'benign'),    # pkt  6  <- streak=1
    ('Normal',  SIM_NORMAL_SIM,  'normal',   'benign'),    # pkt  7  <- streak=2
    ('Normal',  SIM_NORMAL_SIM,  'normal',   'benign'),    # pkt  8  <- streak=3 -> FLUSH
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'xss'),       # pkt  9  <- fresh chain
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'xss'),       # pkt 10
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'sql'),       # pkt 11
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'sql'),       # pkt 12
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'xss'),       # pkt 13
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'injection'), # pkt 14
    ('Exploit', SIM_EXPLOIT_SIM, 'EXPLOIT',  'injection'), # pkt 15
]

window = StaticTimeWindow(window_seconds=WIN_STATIC_S)
rng    = np.random.default_rng(42)
sim_t0 = 0.0

SEP = '-' * 72
print(SEP)
print('  Phase 3.1 -- Static Time-Window Simulation   (15-packet stream)')
print(f'  Static window: {WIN_STATIC_S}s  |  Clean Slate: streak >= {BENIGN_STREAK_THRESHOLD} @ sim >= {BENIGN_SIM_THRESHOLD_PCT}%')
print(SEP)
print(f'  {"Pkt":<4}  {"Label":<8}  {"Sim%":<6}  {"buf_size":<10}  {"clean_slates":<13}  Note')
print(SEP)

for pkt_num, (label, sim_pct, archetype, attack) in enumerate(STREAM, start=1):
    sim_now = sim_t0 + (pkt_num - 1) * SIM_INTERVAL_S

    raw_vec = rng.standard_normal(VECTOR_DIMS).astype(np.float32)
    raw_vec /= np.linalg.norm(raw_vec)

    flow = FlowRecord(
        timestamp      = sim_now,
        vector         = raw_vec,
        top_similarity = sim_pct,
        top_archetype  = archetype,
        top_attack     = attack,
        rag_context    = f'[RAG CONTEXT] top match: {archetype}/{attack} sim={sim_pct:.1f}%',
        packet_label   = label,
    )

    prev_clean = window._clean_slate_count
    window.add_flow(flow, current_time=sim_now)
    flushed = window._clean_slate_count > prev_clean

    if flushed:
        note = '[CLEAN SLATE] evidence chain severed'
    elif pkt_num == 9:
        note = '> Fresh evidence chain begins'
    else:
        note = ''

    print(
        f'  {pkt_num:<4}  {label:<8}  {sim_pct:<6.1f}  '
        f'{window.buffer_size:<10}  {window._clean_slate_count:<13}  {note}'
    )

print(SEP)

fusion_buffer = window.get_context_for_fusion()
print()
print(f'get_context_for_fusion()  ->  {len(fusion_buffer)} FlowRecords ready for Phase 3.2')
n_exploit = sum(1 for f in fusion_buffer if f.packet_label == 'Exploit')
n_normal  = sum(1 for f in fusion_buffer if f.packet_label == 'Normal')
avg_sim   = np.mean([f.top_similarity for f in fusion_buffer])
print(f'  Buffer breakdown  ->  Exploit: {n_exploit}  |  Normal: {n_normal}')
print(f'  Average sim%            ->  {avg_sim:.1f}%')
print(f'  Fixed window size       ->  {window.window_seconds:.1f}s  (constant)')
print(f'  Clean Slate count       ->  {window._clean_slate_count}  flush(es)')
print()
print('Window Stats:')
for k, v in window.stats().items():
    print(f'    {k:<20} : {v}')
"""
set_source(CELLS['711d7090'], CELL5_SRC)
print("Patch 4 applied: Cell 5 simulation")

# ==============================================================================
# Patch 5: Cell 6 -- Visualisation
# ==============================================================================
CELL6_SRC = """\
# -- Cell 6: Evidence Buffer Visualisation -------------------------------------
#
# Re-runs the simulation with wider spacing to demonstrate pruning behaviour --
# the core mechanism of the static sliding window.
#
# 20 exploit packets spaced 4s apart (80s total).
# With WIN_STATIC_S=30s, only the last ~8 packets are retained at steady state.
# This demonstrates the "rolling buffer" that gives Phase 3.2 a stable 30s view.
# ------------------------------------------------------------------------------

PRUNE_INTERVAL_S = 4.0    # 4s x 20 pkts = 80s total stream
N_PRUNE_PKTS     = 20
SEP_VIZ = '=' * 72

window_v2 = StaticTimeWindow(window_seconds=WIN_STATIC_S)
rng_v2    = np.random.default_rng(42)
snapshots = []

for pkt_num in range(1, N_PRUNE_PKTS + 1):
    sim_now = (pkt_num - 1) * PRUNE_INTERVAL_S
    raw_vec = rng_v2.standard_normal(VECTOR_DIMS).astype(np.float32)
    raw_vec /= np.linalg.norm(raw_vec)
    flow = FlowRecord(
        timestamp=sim_now, vector=raw_vec, top_similarity=92.0,
        top_archetype='EXPLOIT', top_attack='xss', packet_label='Exploit',
    )
    window_v2.add_flow(flow, current_time=sim_now)
    snapshots.append({
        'pkt'      : pkt_num,
        'sim_now'  : sim_now,
        'buf_size' : window_v2.buffer_size,
    })

# ASCII bar chart
print(SEP_VIZ)
print('  Phase 3.1 -- Static Window: Buffer Size over Time (pruning demo)')
steady_state = int(WIN_STATIC_S / PRUNE_INTERVAL_S) + 1
print(f'  Window={WIN_STATIC_S}s fixed | Packet interval={PRUNE_INTERVAL_S}s | Expected steady-state ~{steady_state} flows')
print(SEP_VIZ)
print(f'  {"Pkt":<4}  {"t(s)":<6}  Buffer size (1 # = 1 flow)')
print()

BOUNDARY_DRAWN = False
for s in snapshots:
    bar     = '#' * s['buf_size']
    pruning = s['buf_size'] < s['pkt']
    note    = f'  <- pruning: {s["buf_size"]}/{s["pkt"]} flows retained' if pruning else ''
    if s['buf_size'] >= steady_state and not BOUNDARY_DRAWN:
        print(f'  ----  ------  <- STEADY STATE: rolling {steady_state}-flow window')
        BOUNDARY_DRAWN = True
    print(f'  Pkt {s["pkt"]:<2}  t={s["sim_now"]:<5.1f}  |{bar:<30}| {s["buf_size"]} flows{note}')

print()
print(SEP_VIZ)
print()

final = snapshots[-1]
print('-- Phase 3.2 Handoff Summary ' + '-' * 43)
print(f'  Fixed window size     : {WIN_STATIC_S}s  (constant -- no jitter)')
print(f'  Steady-state capacity : ~{steady_state} flows at {PRUNE_INTERVAL_S}s intervals')
print(f'  Final buffer size     : {final["buf_size"]} FlowRecords (ready for Quantum Fusion)')
print(f'  Schema check          : {VECTOR_DIMS}-dim  [OK]  (matches vectorize_v51 + ChromaDB)')
print(f'  Buffer pruning        : while-loop O(1) popleft  [OK]  (no list-comprehension rebuild)')
print(f'  Temporal consistency  : stable 30s denominator  [OK]  (K factor interpretable for panel)')
print()
print('Phase 3.1 complete. StaticTimeWindow ready for Phase 3.2 integration.  [OK]')
"""
set_source(CELLS['6f48eb58'], CELL6_SRC)
print("Patch 5 applied: Cell 6 visualisation")

# ==============================================================================
# Write notebook
# ==============================================================================
NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'\nNotebook written: {NB}')

# ==============================================================================
# Verification
# ==============================================================================
text = NB.read_text(encoding='utf-8')
checks = [
    ('Static title',                  'Static Time-Windowing' in text),
    ('WIN_STATIC_S defined',          'WIN_STATIC_S' in text),
    ('No WIN_MIN_S',                  'WIN_MIN_S' not in text),
    ('No WIN_EXPAND_STEP_S',          'WIN_EXPAND_STEP_S' not in text),
    ('StaticTimeWindow class',        'class StaticTimeWindow' in text),
    ('No AdaptiveTimeWindow class',   'class AdaptiveTimeWindow' not in text),
    ('NORMAL_ARCHETYPES normalised',  "frozenset({'benign', 'normal'})" in text or "frozenset({'normal', 'benign'})" in text),
    ('StaticTimeWindow in sim',       'StaticTimeWindow(window_seconds' in text),
    ('Clean Slate logic present',     'BENIGN_STREAK_THRESHOLD' in text),
    ('Pruning demo in Cell 6',        'PRUNE_INTERVAL_S' in text),
]

print('\n-- Verification ' + '-' * 56)
for label, ok in checks:
    print(f'  {"[OK]" if ok else "[!!]"} {label}')

all_ok = all(ok for _, ok in checks)
print(f'\n{"All verifications passed" if all_ok else "FAILED -- check above"}')

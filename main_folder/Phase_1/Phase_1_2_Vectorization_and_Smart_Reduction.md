# Phase 1.2 — Vectorization & Smart Reduction  `[v5.1 — 114-Dimensional Knowledge Vectors]`

**Objective:** Transform `aligned_schema_v5.parquet` into a high-quality **Vector Knowledge Base**
for RAG-IDS retrieval.

**Input:**  `aligned_schema_v5.parquet`  (output of Phase 1.1 v5.1)
**Outputs:** `X_knowledge_vectors.npy` + `X_knowledge_meta.parquet`

---

## Architecture: Two-Pass Streaming

| Pass | Name | What it does |
|------|------|--------------|
| **1** | Fit Global Statistics | Stream all rows → fit RobustScaler (core + momentum), QuantileTransformer (port freq) |
| **2** | Vectorize + Reduce | Stream again → build 114-dim vectors → 1M UBT Archetype cap |

---

## 114-Dimension Block Layout

| Block | Dims | Normalization |
|-------|------|---------------|
| Block 1 — Core | 5 | log1p → RobustScaler → L2 |
| Block 2 — Protocol | 18 | OHE → L2 |
| Block 3 — State | 5 | OHE → L2 |
| Block 4 — Port | 16 | OHE + QT(port_freq) → L2 |
| Block 5 — App-Layer | 51 | DNS(15) + HTTP(21) + SSL(15) → L2 |
| Block 6 — Momentum | 14 | log1p+RobustScaler / QT → L2 |
| **Mask Bits** | **5** | `has_svc, has_dns, has_http, has_ssl, has_unsw` (appended, not normalized) |
| **TOTAL** | **114** | Final global L2 normalization |

## 1M Density Cap — Nested Stratification
- Cap each UBT archetype at **1,000,000** vectors
- Within archetype: **rare sub-class** (n < 20k) → keep 100% | **majority** → Smart-Reduction (Centroids + Farthest Outliers)


### Cell 1

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 1 | Imports + Dependency Check
# ─────────────────────────────────────────────────────────────────────────────
import sys, os, json, time, pickle, warnings, random
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SCHEMA_VERSION = "v5.1"
TOTAL_DIMS     = 114

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    print(f"✅ pyarrow       {pa.__version__}")
except ImportError:
    raise SystemExit("pip install pyarrow")

try:
    from sklearn.preprocessing import RobustScaler, QuantileTransformer
    import sklearn
    print(f"✅ scikit-learn  {sklearn.__version__}")
except ImportError:
    raise SystemExit("pip install scikit-learn")

try:
    from tqdm import tqdm
    print("✅ tqdm          available")
except ImportError:
    def tqdm(it, **kw): return it
    print("⚠️  tqdm not installed — progress bars disabled")

print(f"\n🔷 Universal Behavioral Schema {SCHEMA_VERSION} — {TOTAL_DIMS} Dimensions")
print(f"   Phase 1.2: Aligned Schema → 114-dim Knowledge Vectors")
print(f"\n✅ Python  {sys.version.split()[0]}")
print(f"✅ pandas  {pd.__version__}")
print(f"✅ numpy   {np.__version__}")

`

**Output:**
`
✅ pyarrow       23.0.0
✅ scikit-learn  1.7.0
✅ tqdm          available
✅ matplotlib    3.10.7

✅ Python  3.13.9
✅ pandas  2.2.3
✅ numpy   2.1.3

✅ Hyper-parameters set  [REVISION v4 — Hybrid Fix: cherry-pick v3 wins, revert Volumetric]
   CHUNK_SIZE         = 200,000
   RARE_CLASSES       = {4}     (keep 100%  — Exploit_and_Theft only)
   MAJORITY_CLASSES   = {0, 1, 2, 3}  (centroid + class-specific outliers + random)

   Per-class reduction table:
   Class  Name                     top-k   sample%  group key       v4 change
   --------------------------------------------------------------------------------
   0     Normal                      10     5.00%  src_ip          KEEP v3 Boost
   1     Reconnaissance               5     1.00%  src_ip          unchanged
   2     Volumetric_Attack            5     1.00%  src_ip ← REVERTED  REVERT (was dst_ip)
   3     C2_Botnet                    3     0.10%  src_ip          KEEP v3 Crush
   4     Exploit_and_Theft            —   100.00%  —               RARE — keep all

   LEAKAGE_COLUMNS    = ['zeek_service', 'zeek_history']  (dropped before vectorization)
`

### Cell 2

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 2 | Paths + Dimension Constants + Schema Vocabularies
# ─────────────────────────────────────────────────────────────────────────────
NOTEBOOK_DIR  = Path.cwd()
MAIN_DIR      = NOTEBOOK_DIR.parent
DATA_DIR      = MAIN_DIR / "data"
UNIFIED_DIR   = DATA_DIR / "unified"
VECTORS_DIR   = DATA_DIR / "vectors"
ARTIFACTS_DIR = MAIN_DIR / "artifacts"

for d in [VECTORS_DIR, ARTIFACTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── I/O Paths ─────────────────────────────────────────────────────────────────
INPUT_PARQUET        = UNIFIED_DIR / "aligned_schema_v5.parquet"
PREPROCESSORS_PATH   = ARTIFACTS_DIR / "preprocessors_v51.pkl"
VECTORS_PATH         = VECTORS_DIR  / "X_knowledge_vectors.npy"
META_PATH            = VECTORS_DIR  / "X_knowledge_meta.parquet"

# ── Processing Hyperparameters ────────────────────────────────────────────────
CHUNK_SIZE             = 200_000
RESERVOIR_SIZE         = 200_000   # samples for scaler fitting
UBT_ARCHETYPE_CAP      = 1_000_000 # max vectors per UBT archetype
RARE_SUBCLASS_THRESH   = 20_000    # subcategory is "rare" if count < this
QT_N_QUANTILES         = 1_000     # QuantileTransformer resolution

# ── Schema Vocabularies (MUST match Phase 1.1 v5.1) ──────────────────────────
UBT_ARCHETYPES   = ["NORMAL","SCAN","DOS_DDOS","BOTNET_C2","EXPLOIT","BRUTE_FORCE","THEFT_EXFIL","ANOMALY"]
PROTO_TOKENS     = ["tcp","udp","icmp","arp","ipv6","other"]
SERVICE_TOKENS   = ["dns","http","ssl","ftp","ssh","smtp","dhcp","quic","ntp","rdp","pop3","other"]
STATE_TOKENS     = ["PENDING","ESTABLISHED","REJECTED","RESET","OTHER"]
PORT_FUNC_TOKENS = ["SCADA_CONTROL","IOT_MANAGEMENT","WEB_SERVICES","NETWORK_CORE","REMOTE_ACCESS","FUNC_EPHEMERAL","FUNC_UNKNOWN"]

# ── Dimension registry (must sum to TOTAL_DIMS) ────────────────────────────────
BLOCK_DIMS = {
    "block1_core":     5,
    "block2_protocol": 18,   # proto(6) + service(12)
    "block3_state":    5,
    "block4_port":     16,   # sport_func(7) + dport_func(7) + port_freq(2)
    "block5_dns":      15,
    "block5_http":     21,
    "block5_ssl":      15,
    "block6_momentum": 14,
    "mask_bits":       5,
}
BLOCK_ORDER = [
    "block1_core", "block2_protocol", "block3_state", "block4_port",
    "block5_dns", "block5_http", "block5_ssl", "block6_momentum", "mask_bits"
]
assert sum(BLOCK_DIMS.values()) == TOTAL_DIMS, (
    f"Block dims sum to {sum(BLOCK_DIMS.values())}, expected {TOTAL_DIMS}"
)

# Cumulative offsets for each block in the 114-dim vector
BLOCK_OFFSETS = {}
offset = 0
for bname in BLOCK_ORDER:
    BLOCK_OFFSETS[bname] = (offset, offset + BLOCK_DIMS[bname])
    offset += BLOCK_DIMS[bname]

# ── Port classification lookup (matches Phase 1.1) ────────────────────────────
SCADA_PORTS    = frozenset({502, 102, 44818})
IOT_MGMT_PORTS = frozenset({1883, 5683, 8883})
WEB_PORTS      = frozenset({80, 443, 8080})
NET_CORE_PORTS = frozenset({53, 67, 68, 123})
REMOTE_PORTS   = frozenset({22, 23, 3389})

def classify_port(port) -> str:
    try:
        p = int(float(port))
    except (ValueError, TypeError):
        return "FUNC_UNKNOWN"
    if p < 0:            return "FUNC_UNKNOWN"
    if p in SCADA_PORTS:    return "SCADA_CONTROL"
    if p in IOT_MGMT_PORTS: return "IOT_MANAGEMENT"
    if p in WEB_PORTS:      return "WEB_SERVICES"
    if p in NET_CORE_PORTS: return "NETWORK_CORE"
    if p in REMOTE_PORTS:   return "REMOTE_ACCESS"
    if p > 49152:           return "FUNC_EPHEMERAL"
    return "FUNC_UNKNOWN"

# ── OHE lookup dicts (token → index) ──────────────────────────────────────────
PROTO_IDX    = {t: i for i, t in enumerate(PROTO_TOKENS)}
SERVICE_IDX  = {t: i for i, t in enumerate(SERVICE_TOKENS)}
STATE_IDX    = {t: i for i, t in enumerate(STATE_TOKENS)}
PORT_FUNC_IDX = {t: i for i, t in enumerate(PORT_FUNC_TOKENS)}

# ── DNS qtype lookup ──────────────────────────────────────────────────────────
DNS_QTYPE_IDX = {1: 0, 28: 1, 12: 2, 15: 3, 16: 4, 5: 5, 2: 6, 33: 7, 6: 8}
# Index 9 = "other qtype"

# ── HTTP method OHE tokens (8, dim 0-7 of Block 5 HTTP) ───────────────────────
HTTP_METHOD_TOKENS = ["GET","POST","PUT","DELETE","HEAD","OPTIONS","PATCH","OTHER"]
HTTP_METHOD_IDX    = {t: i for i, t in enumerate(HTTP_METHOD_TOKENS)}

# ── SSL cipher suite OHE tokens (12, dim 0-11 of Block 5 SSL) ─────────────────
SSL_CIPHER_TOKENS = [
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_AES_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
    "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
    "TLS_RSA_WITH_AES_256_CBC_SHA",
    "TLS_RSA_WITH_AES_128_CBC_SHA",
    "other",
]
SSL_CIPHER_IDX     = {t: i for i, t in enumerate(SSL_CIPHER_TOKENS)}
WEAK_SSL_VERSIONS  = frozenset({"SSLv2", "SSLv3", "TLSv10", "TLSv1.0"})
STRONG_SSL_VERSIONS = frozenset({"TLSv11", "TLSv12", "TLSv13", "TLSv1.1", "TLSv1.2", "TLSv1.3"})

print("=" * 68)
print(f"  Phase 1.2 {SCHEMA_VERSION} — Config")
print("=" * 68)

status = "✅" if INPUT_PARQUET.exists() else "❌ MISSING"
mb     = INPUT_PARQUET.stat().st_size / 1e6 if INPUT_PARQUET.exists() else 0
print(f"\n📂 Input:  {status}  {INPUT_PARQUET.name}  ({mb:,.1f} MB)")
print(f"📤 Output: {VECTORS_PATH.name}  +  {META_PATH.name}")
print(f"\n🗂️  Block layout (sum = {TOTAL_DIMS}):")
for bname in BLOCK_ORDER:
    s, e = BLOCK_OFFSETS[bname]
    print(f"   [{s:>3d}:{e:>3d}]  {bname:<20}  {BLOCK_DIMS[bname]:>2d} dims")

if not INPUT_PARQUET.exists():
    raise FileNotFoundError(f"Run Phase 1.1 v5.1 first to produce {INPUT_PARQUET.name}")

`

**Output:**
`
📁 Directory layout:
   UNIFIED_DIR      c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\data\unified  ✅
   PROCESSED_DIR    c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\data\processed  ✅
   ARTIFACTS_DIR    c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\artifacts  ✅

📂 Input Parquets:
   ✅ toniot     toniot_aligned.parquet                   270.6 MB
   ✅ iot23      iot23_complete.parquet                   6,113.3 MB
   ✅ botiot     botiot_52col.parquet                     86.3 MB

📊 Column groups:
   NUM_COLS            5 cols
   PORT_COLS           2 cols
   BOOL_COLS           2 cols
   CAT_COLS (OHE)      2 cols
   SENTINEL_NUM_COLS  31 cols
   ALL_NUM_COLS       36 cols  (NUM + SENTINEL)

📦 Output files (v4):
   VECTORS_PATH  →  X_knowledge_vectors_v4.npy
   META_PATH     →  X_knowledge_meta_v4.parquet
`

---
## Step 1 — Pass 1: Fit Global Statistics

Stream all rows of `aligned_schema_v5.parquet` once to:
- Fit **RobustScaler** on Block 1 (core numerics) and Block 6 (momentum continuous)
- Fit **QuantileTransformer(1000, uniform)** on port frequency scores
- Build sport / dport frequency maps  `P(port)`
- Fit **QuantileTransformer(1000, uniform)** on Momentum count features

**Output:** `artifacts/preprocessors_v51.pkl`


### Cell 3

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 3 | Pass 1 — Fit Global Statistics
# ─────────────────────────────────────────────────────────────────────────────

# Feature groups for scaler fitting
CORE_COLS     = ["univ_duration", "univ_bytes_in", "univ_bytes_out", "univ_pkts_in", "univ_pkts_out"]
MOM_CONT_COLS = ["mom_mean", "mom_stddev", "mom_sum", "mom_min", "mom_max", "mom_rate", "mom_srate", "mom_drate"]
MOM_CNT_COLS  = ["mom_TnBPSrcIP", "mom_TnBPDstIP", "mom_TnP_PSrcIP", "mom_TnP_PDstIP", "mom_TnP_PerProto", "mom_TnP_Per_Dport"]
PORT_COLS     = ["raw_sport", "raw_dport"]


def reservoir_update(current: np.ndarray, new_vals: np.ndarray, max_size: int) -> np.ndarray:
    """Add new_vals to reservoir, keeping at most max_size samples."""
    combined = np.concatenate([current, new_vals]) if len(current) else new_vals
    if len(combined) > max_size:
        idx = np.random.choice(len(combined), max_size, replace=False)
        combined = combined[idx]
    return combined


def fit_global_statistics() -> dict:
    """
    Single-pass streaming scan over aligned_schema_v5.parquet.
    Returns a dict with all fitted preprocessors + port frequency maps.
    """
    # Reservoirs for fitting
    res_core     = {c: np.empty(0) for c in CORE_COLS}
    res_mom_cont = {c: np.empty(0) for c in MOM_CONT_COLS}
    res_mom_cnt  = {c: np.empty(0) for c in MOM_CNT_COLS}
    sport_ctr    = Counter()
    dport_ctr    = Counter()
    total_rows   = 0
    t0           = time.time()

    pf      = pq.ParquetFile(str(INPUT_PARQUET))
    n_rows  = pf.metadata.num_rows
    n_batches = (n_rows + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"  Streaming {n_rows:,} rows  |  {n_batches:,} chunks  |  RESERVOIR_SIZE={RESERVOIR_SIZE:,}")

    for batch in tqdm(pf.iter_batches(batch_size=CHUNK_SIZE), total=n_batches, desc="  Pass-1"):
        chunk = batch.to_pandas()
        n     = len(chunk)
        total_rows += n

        # ── Core: reservoir sample log1p values ───────────────────────────────
        for col in CORE_COLS:
            if col in chunk.columns:
                vals = pd.to_numeric(chunk[col], errors="coerce").fillna(0.0).clip(lower=0).values
                log_vals = np.log1p(vals.astype(np.float64))
                res_core[col] = reservoir_update(res_core[col], log_vals, RESERVOIR_SIZE)

        # ── Momentum continuous: reservoir sample, sentinel=-1 masked out ──────
        for col in MOM_CONT_COLS:
            if col in chunk.columns:
                vals = pd.to_numeric(chunk[col], errors="coerce").fillna(-1.0).values.astype(np.float64)
                valid = vals[vals != -1.0]
                if len(valid):
                    # shift min to 0 for log1p
                    shift = max(0.0, -valid.min())
                    log_vals = np.log1p(valid + shift)
                    res_mom_cont[col] = reservoir_update(res_mom_cont[col], log_vals, RESERVOIR_SIZE)

        # ── Momentum count: reservoir sample, sentinel=-1 masked out ──────────
        for col in MOM_CNT_COLS:
            if col in chunk.columns:
                vals = pd.to_numeric(chunk[col], errors="coerce").fillna(-1.0).values.astype(np.float64)
                valid = vals[vals != -1.0]
                if len(valid):
                    res_mom_cnt[col] = reservoir_update(res_mom_cnt[col], valid, RESERVOIR_SIZE)

        # ── Port frequency counting ────────────────────────────────────────────
        if "raw_sport" in chunk.columns:
            sports = pd.to_numeric(chunk["raw_sport"], errors="coerce").fillna(-1).astype(int)
            sport_ctr.update(sports[sports >= 0].tolist())
        if "raw_dport" in chunk.columns:
            dports = pd.to_numeric(chunk["raw_dport"], errors="coerce").fillna(-1).astype(int)
            dport_ctr.update(dports[dports >= 0].tolist())

    elapsed = time.time() - t0
    print(f"\n  ✅ Pass-1 complete  |  {total_rows:,} rows  |  {elapsed:.1f}s")

    # ── Build RobustScalers ────────────────────────────────────────────────────
    print("\n  Fitting RobustScalers...")
    core_scalers = {}
    for col in CORE_COLS:
        rs = RobustScaler()
        data = res_core[col].reshape(-1, 1)
        if len(data) < 2:
            data = np.array([[0.0], [1.0]])
        rs.fit(data)
        core_scalers[col] = rs
    print(f"  ✅ RobustScaler (core): {len(core_scalers)} scalers")

    mom_cont_scalers = {}
    for col in MOM_CONT_COLS:
        rs = RobustScaler()
        data = res_mom_cont[col].reshape(-1, 1) if len(res_mom_cont[col]) else np.array([[0.0],[1.0]])
        rs.fit(data)
        # Check IQR — fallback to QuantileTransformer if near-zero
        iqr = float(rs.scale_[0]) if hasattr(rs, 'scale_') else 1.0
        if abs(iqr) < 1e-7:
            qt = QuantileTransformer(n_quantiles=min(QT_N_QUANTILES, max(2, len(res_mom_cont[col]))), output_distribution="uniform", subsample=int(1e6))
            qt.fit(data)
            mom_cont_scalers[col] = ("qt", qt)
        else:
            mom_cont_scalers[col] = ("rs", rs)
    print(f"  ✅ Momentum cont scalers: {len(mom_cont_scalers)}")

    # ── QuantileTransformer for momentum count features ───────────────────────
    mom_cnt_qts = {}
    for col in MOM_CNT_COLS:
        data = res_mom_cnt[col].reshape(-1, 1) if len(res_mom_cnt[col]) else np.array([[0.0],[1.0]])
        qt = QuantileTransformer(n_quantiles=min(QT_N_QUANTILES, max(2, len(data))), output_distribution="uniform", subsample=int(1e6))
        qt.fit(data)
        mom_cnt_qts[col] = qt
    print(f"  ✅ Momentum count QTs: {len(mom_cnt_qts)}")

    # ── Build port frequency maps + fit QuantileTransformer ───────────────────
    print("\n  Building port frequency maps...")
    sport_total = max(sum(sport_ctr.values()), 1)
    dport_total = max(sum(dport_ctr.values()), 1)
    sport_freq_map = {k: v / sport_total for k, v in sport_ctr.items()}
    dport_freq_map = {k: v / dport_total for k, v in dport_ctr.items()}

    # Build the distribution of realized freq values (weighted by observed count)
    sport_freq_vals = np.array([p for p in sport_freq_map.values()], dtype=np.float64)
    dport_freq_vals = np.array([p for p in dport_freq_map.values()], dtype=np.float64)
    if len(sport_freq_vals) < 2: sport_freq_vals = np.array([0.0, 1e-6])
    if len(dport_freq_vals) < 2: dport_freq_vals = np.array([0.0, 1e-6])

    qt_sport_freq = QuantileTransformer(n_quantiles=min(QT_N_QUANTILES, len(sport_freq_vals)), output_distribution="uniform", subsample=int(1e6))
    qt_dport_freq = QuantileTransformer(n_quantiles=min(QT_N_QUANTILES, len(dport_freq_vals)), output_distribution="uniform", subsample=int(1e6))
    qt_sport_freq.fit(sport_freq_vals.reshape(-1, 1))
    qt_dport_freq.fit(dport_freq_vals.reshape(-1, 1))
    print(f"  ✅ Port freq maps: {len(sport_freq_map):,} sport, {len(dport_freq_map):,} dport")

    preprocessors = {
        "core_scalers":      core_scalers,
        "mom_cont_scalers":  mom_cont_scalers,
        "mom_cnt_qts":       mom_cnt_qts,
        "sport_freq_map":    sport_freq_map,
        "dport_freq_map":    dport_freq_map,
        "qt_sport_freq":     qt_sport_freq,
        "qt_dport_freq":     qt_dport_freq,
        "schema_version":    SCHEMA_VERSION,
        "total_rows_seen":   total_rows,
    }
    return preprocessors


print("✅ fit_global_statistics() defined")
print(f"   Core cols     : {CORE_COLS}")
print(f"   Mom cont cols : {MOM_CONT_COLS}")
print(f"   Mom cnt cols  : {MOM_CNT_COLS}")

`

**Output:**
`
✅ fit_global_statistics() defined  (call in next cell)
`

### Cell 4

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 4 | Execute Pass 1 + Save Preprocessors
# ─────────────────────────────────────────────────────────────────────────────

# Re-use saved preprocessors if they exist (skip expensive Pass 1)
if PREPROCESSORS_PATH.exists():
    print(f"✅ Loading saved preprocessors: {PREPROCESSORS_PATH.name}")
    with open(PREPROCESSORS_PATH, "rb") as f:
        preprocessors = pickle.load(f)
    print(f"   schema_version   : {preprocessors.get('schema_version', 'unknown')}")
    print(f"   total_rows_seen  : {preprocessors.get('total_rows_seen', 0):,}")
else:
    print(f"🔄 Running Pass-1 — fitting global statistics...")
    preprocessors = fit_global_statistics()
    with open(PREPROCESSORS_PATH, "wb") as f:
        pickle.dump(preprocessors, f)
    print(f"\n✅ Preprocessors saved → {PREPROCESSORS_PATH.name}")

# Unpack into module-level names for use in block builders
core_scalers      = preprocessors["core_scalers"]
mom_cont_scalers  = preprocessors["mom_cont_scalers"]
mom_cnt_qts       = preprocessors["mom_cnt_qts"]
sport_freq_map    = preprocessors["sport_freq_map"]
dport_freq_map    = preprocessors["dport_freq_map"]
qt_sport_freq     = preprocessors["qt_sport_freq"]
qt_dport_freq     = preprocessors["qt_dport_freq"]

print(f"\n✅ Preprocessors ready:")
print(f"   core_scalers      : {len(core_scalers)} RobustScalers")
print(f"   mom_cont_scalers  : {len(mom_cont_scalers)} scalers")
print(f"   mom_cnt_qts       : {len(mom_cnt_qts)} QuantileTransformers")
print(f"   sport_freq_map    : {len(sport_freq_map):,} port entries")
print(f"   dport_freq_map    : {len(dport_freq_map):,} port entries")

`

**Output:**
`
⏭️  Found existing preprocessors.pkl — loading (set FORCE_REFIT=True to redo)
✅ Preprocessors loaded from disk

  Scaler fitted on 36 cols, 351,317,489 samples seen
  OHE dims total: 10
  OHE features  : ['univ_proto__arp', 'univ_proto__icmp', 'univ_proto__other', 'univ_proto__tcp', 'univ_proto__udp', 'univ_state__attempt', 'univ_state__established', 'univ_state__other', 'univ_state__rejected', 'univ_state__unknown'] …
`

---
## Step 2 — Block Vector Builders

One function per block. Each returns a `(N, block_dims)` numpy array.
`build_114_vector(chunk)` assembles all 6 blocks + mask bits,
applies per-block L2 normalization, concatenates to 114 dims, applies global L2 norm.


### Cell 5

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 5 | Block Builder Functions + build_114_vector()
# ─────────────────────────────────────────────────────────────────────────────

def _l2_norm_rows(X: np.ndarray) -> np.ndarray:
    """L2-normalize each row of X. Rows with zero norm stay zero."""
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms < 1e-10, 1.0, norms)
    return X / norms


def _safe_num(series, fill=0.0) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").fillna(fill).values.astype(np.float64)


def _scale_col(vals: np.ndarray, col: str, scalers_dict: dict) -> np.ndarray:
    """Apply RobustScaler or QT from scalers_dict to a 1-D array."""
    entry = scalers_dict.get(col)
    if entry is None:
        return np.zeros(len(vals))
    if isinstance(entry, tuple):
        kind, scaler = entry
    else:
        scaler = entry
    scaled = scaler.transform(vals.reshape(-1, 1)).flatten()
    return np.nan_to_num(scaled, nan=0.0, posinf=1.0, neginf=-1.0)


# ─── Block 1: Core (5 dims) ──────────────────────────────────────────────────
def build_block1(chunk: pd.DataFrame) -> np.ndarray:
    """Core behavioral features: log1p → RobustScaler. Shape (N, 5)."""
    N   = len(chunk)
    out = np.zeros((N, 5), dtype=np.float32)
    for i, col in enumerate(CORE_COLS):
        raw  = _safe_num(chunk.get(col, pd.Series(np.zeros(N))), fill=0.0).clip(min=0)
        log1 = np.log1p(raw)
        out[:, i] = _scale_col(log1, col, core_scalers)
    return out


# ─── Block 2: Protocol (18 dims: proto_6 + service_12) ───────────────────────
def build_block2(chunk: pd.DataFrame) -> np.ndarray:
    """Protocol OHE: proto(6) + service×has_svc(12). Shape (N, 18)."""
    N   = len(chunk)
    out = np.zeros((N, 18), dtype=np.float32)

    # Proto OHE (dims 0–5)
    protos = chunk.get("raw_proto", pd.Series(["other"] * N)).fillna("other").astype(str)
    for row_i, p in enumerate(protos):
        idx = PROTO_IDX.get(p.lower().strip(), PROTO_IDX["other"])
        out[row_i, idx] = 1.0

    # Service OHE (dims 6–17), gated by has_svc
    services = chunk.get("raw_service", pd.Series(["<absent>"] * N)).fillna("<absent>").astype(str)
    has_svc  = _safe_num(chunk.get("has_svc", pd.Series(np.zeros(N))), fill=0).astype(int)
    for row_i, (s, gate) in enumerate(zip(services, has_svc)):
        if gate:
            s_clean = s.lower().strip()
            idx = SERVICE_IDX.get(s_clean, SERVICE_IDX.get("other", 11))
            out[row_i, 6 + idx] = 1.0

    return out


# ─── Block 3: State (5 dims) ──────────────────────────────────────────────────
def build_block3(chunk: pd.DataFrame) -> np.ndarray:
    """State 5-way OHE: PENDING/ESTABLISHED/REJECTED/RESET/OTHER. Shape (N, 5)."""
    N   = len(chunk)
    out = np.zeros((N, 5), dtype=np.float32)
    states = chunk.get("raw_state_v51", pd.Series(["OTHER"] * N)).fillna("OTHER").astype(str)
    for row_i, s in enumerate(states):
        idx = STATE_IDX.get(s.strip(), STATE_IDX["OTHER"])
        out[row_i, idx] = 1.0
    return out


# ─── Block 4: Port (16 dims: sport_func_7 + dport_func_7 + freq_2) ────────────
def build_block4(chunk: pd.DataFrame) -> np.ndarray:
    """Port OHE + frequency scores. Shape (N, 16)."""
    N    = len(chunk)
    out  = np.zeros((N, 16), dtype=np.float32)
    sports = _safe_num(chunk.get("raw_sport", pd.Series(np.full(N, -1))), fill=-1).astype(int)
    dports = _safe_num(chunk.get("raw_dport", pd.Series(np.full(N, -1))), fill=-1).astype(int)

    # sport_func OHE (dims 0–6)
    for row_i, sp in enumerate(sports):
        func = classify_port(sp)
        idx  = PORT_FUNC_IDX.get(func, PORT_FUNC_IDX["FUNC_UNKNOWN"])
        out[row_i, idx] = 1.0

    # dport_func OHE (dims 7–13)
    for row_i, dp in enumerate(dports):
        func = classify_port(dp)
        idx  = PORT_FUNC_IDX.get(func, PORT_FUNC_IDX["FUNC_UNKNOWN"])
        out[row_i, 7 + idx] = 1.0

    # Port frequency scores (dims 14–15)
    sport_freqs = np.array([sport_freq_map.get(sp, 0.0) for sp in sports], dtype=np.float64)
    dport_freqs = np.array([dport_freq_map.get(dp, 0.0) for dp in dports], dtype=np.float64)
    out[:, 14] = qt_sport_freq.transform(sport_freqs.reshape(-1, 1)).flatten().astype(np.float32)
    out[:, 15] = qt_dport_freq.transform(dport_freqs.reshape(-1, 1)).flatten().astype(np.float32)

    return out


# ─── Block 5: DNS (15 dims) ───────────────────────────────────────────────────
def build_block5_dns(chunk: pd.DataFrame) -> np.ndarray:
    """DNS app-layer features. Shape (N, 15)."""
    N      = len(chunk)
    out    = np.zeros((N, 15), dtype=np.float32)
    has_d  = _safe_num(chunk.get("has_dns", pd.Series(np.zeros(N))), fill=0).astype(int)
    qtypes  = _safe_num(chunk.get("dns_qtype",  pd.Series(np.full(N, -1))), fill=-1).astype(int)
    qclass  = _safe_num(chunk.get("dns_qclass", pd.Series(np.full(N, -1))), fill=-1).astype(int)
    rcode   = _safe_num(chunk.get("dns_rcode",  pd.Series(np.full(N, -1))), fill=-1).astype(int)

    dns_mask = (has_d == 1)
    for row_i in np.where(dns_mask)[0]:
        qt  = qtypes[row_i]
        qc  = qclass[row_i]
        rc  = rcode[row_i]
        # qtype OHE (dims 0–9)
        q_idx = DNS_QTYPE_IDX.get(qt, 9)  # 9 = "other"
        out[row_i, q_idx] = 1.0
        # qclass OHE (dims 10–12)
        if qc == 1:   out[row_i, 10] = 1.0    # IN
        elif qc == 3: out[row_i, 11] = 1.0    # CHAOS
        else:         out[row_i, 12] = 1.0    # other
        # rcode (dims 13–14)
        if rc == 0:   out[row_i, 13] = 1.0    # success
        elif rc > 0:  out[row_i, 14] = 1.0    # error

    return out


# ─── Block 5: HTTP (21 dims) ──────────────────────────────────────────────────
def build_block5_http(chunk: pd.DataFrame) -> np.ndarray:
    """HTTP app-layer features. Shape (N, 21).
    Dims  0– 7: method OHE (GET/POST/PUT/DELETE/HEAD/OPTIONS/PATCH/OTHER)
                ACTUAL from raw_http_method — populated for TON-IoT rows
    Dims  8–12: status group (1xx/2xx/3xx/4xx/5xx)
    Dim  13   : req_body_log1p
    Dim  14   : resp_body_log1p
    Dim  15   : has_req_body
    Dim  16   : has_resp_body
    Dim  17   : has_status_code
    Dim  18   : is_success (2xx)
    Dim  19   : is_redirect (3xx)
    Dim  20   : is_error (4xx/5xx)
    """
    N      = len(chunk)
    out    = np.zeros((N, 21), dtype=np.float32)
    has_h  = _safe_num(chunk.get("has_http", pd.Series(np.zeros(N))), fill=0).astype(int)
    method = chunk.get("raw_http_method", pd.Series(["-"] * N)).fillna("-").astype(str).str.upper().str.strip()
    status = _safe_num(chunk.get("http_status_code",   pd.Series(np.full(N, -1))), fill=-1).astype(int)
    req_b  = _safe_num(chunk.get("http_req_body_len",  pd.Series(np.full(N, -1))), fill=-1).astype(float)
    resp_b = _safe_num(chunk.get("http_resp_body_len", pd.Series(np.full(N, -1))), fill=-1).astype(float)

    http_mask = (has_h == 1)
    rows_h    = np.where(http_mask)[0]

    # Method OHE (dims 0–7) — ACTUAL from raw_http_method
    for row_i in rows_h:
        m     = method.iloc[row_i]
        m_idx = HTTP_METHOD_IDX.get(m, HTTP_METHOD_IDX["OTHER"])
        out[row_i, m_idx] = 1.0

    # Status group (dims 8–12)
    for row_i in rows_h:
        s = status[row_i]
        if   100 <= s <= 199: out[row_i,  8] = 1.0
        elif 200 <= s <= 299: out[row_i,  9] = 1.0
        elif 300 <= s <= 399: out[row_i, 10] = 1.0
        elif 400 <= s <= 499: out[row_i, 11] = 1.0
        elif 500 <= s <= 599: out[row_i, 12] = 1.0

    # Body lengths (dims 13–14)
    req_log  = np.where(req_b  > 0, np.log1p(req_b),  0.0)
    resp_log = np.where(resp_b > 0, np.log1p(resp_b), 0.0)
    out[np.ix_(rows_h, [13])] = req_log[rows_h].reshape(-1, 1)
    out[np.ix_(rows_h, [14])] = resp_log[rows_h].reshape(-1, 1)

    # Binary flags (dims 15–20)
    out[rows_h, 15] = (req_b[rows_h]  > 0).astype(np.float32)
    out[rows_h, 16] = (resp_b[rows_h] > 0).astype(np.float32)
    out[rows_h, 17] = (status[rows_h] > 0).astype(np.float32)
    out[rows_h, 18] = ((status[rows_h] >= 200) & (status[rows_h] < 300)).astype(np.float32)
    out[rows_h, 19] = ((status[rows_h] >= 300) & (status[rows_h] < 400)).astype(np.float32)
    out[rows_h, 20] = (status[rows_h] >= 400).astype(np.float32)

    return out


# ─── Block 5: SSL (15 dims) ───────────────────────────────────────────────────
def build_block5_ssl(chunk: pd.DataFrame) -> np.ndarray:
    """SSL app-layer features. Shape (N, 15).
    Dims  0–11: cipher suite OHE (12 tokens) — ACTUAL from raw_ssl_cipher
    Dim  12   : weak SSL version flag (SSLv2/3, TLSv1.0) — ACTUAL from raw_ssl_version
    Dim  13   : strong TLS version flag (TLSv1.1/1.2/1.3) — ACTUAL from raw_ssl_version
    Dim  14   : ssl_established flag — ACTUAL from ssl_established column
    """
    N     = len(chunk)
    out   = np.zeros((N, 15), dtype=np.float32)
    has_s = _safe_num(chunk.get("has_ssl", pd.Series(np.zeros(N))), fill=0).astype(int)

    ssl_rows = np.where(has_s == 1)[0]
    if len(ssl_rows) == 0:
        return out

    cipher  = chunk.get("raw_ssl_cipher",  pd.Series(["-"] * N)).fillna("-").astype(str).str.strip()
    version = chunk.get("raw_ssl_version", pd.Series(["-"] * N)).fillna("-").astype(str).str.strip()
    estab   = _safe_num(chunk.get("ssl_established", pd.Series(np.zeros(N))), fill=0).astype(int)

    # Cipher OHE (dims 0–11) — ACTUAL from raw_ssl_cipher
    for row_i in ssl_rows:
        c   = cipher.iloc[row_i]
        idx = SSL_CIPHER_IDX.get(c, SSL_CIPHER_IDX["other"])
        out[row_i, idx] = 1.0

    # Version flags (dims 12–13) — ACTUAL from raw_ssl_version
    for row_i in ssl_rows:
        v = version.iloc[row_i]
        if v in WEAK_SSL_VERSIONS:
            out[row_i, 12] = 1.0
        elif v in STRONG_SSL_VERSIONS:
            out[row_i, 13] = 1.0
        # else: unknown version → both dims stay 0

    # ssl_established (dim 14) — ACTUAL from ssl_established column
    out[ssl_rows, 14] = estab[ssl_rows].astype(np.float32)

    return out


# ─── Block 6: Momentum (14 dims) ─────────────────────────────────────────────
def build_block6(chunk: pd.DataFrame) -> np.ndarray:
    """UNSW Bot-IoT window features. Shape (N, 14)."""
    N     = len(chunk)
    out   = np.zeros((N, 14), dtype=np.float32)
    has_u = _safe_num(chunk.get("has_unsw", pd.Series(np.zeros(N))), fill=0).astype(int)
    unsw_rows = np.where(has_u == 1)[0]
    if len(unsw_rows) == 0:
        return out

    # 8 continuous (dims 0–7)
    for i, col in enumerate(MOM_CONT_COLS):
        raw = _safe_num(chunk.get(col, pd.Series(np.full(N, -1.0))), fill=-1.0)
        valid = raw[unsw_rows]
        # Shift to non-negative for log1p
        shift = max(0.0, float(-valid.min())) if len(valid) else 0.0
        log_vals = np.log1p(np.clip(valid + shift, 0, None))
        scaled   = _scale_col(log_vals, col, mom_cont_scalers)
        out[unsw_rows, i] = scaled.astype(np.float32)

    # 6 count (dims 8–13)
    for i, col in enumerate(MOM_CNT_COLS):
        raw = _safe_num(chunk.get(col, pd.Series(np.full(N, -1.0))), fill=-1.0)
        valid = raw[unsw_rows].reshape(-1, 1)
        qt = mom_cnt_qts.get(col)
        if qt is not None and len(valid):
            scaled = qt.transform(valid).flatten().astype(np.float32)
            out[unsw_rows, 8 + i] = scaled

    return out


# ─── build_114_vector: assemble all blocks → 114 dims ────────────────────────
def build_114_vector(chunk: pd.DataFrame) -> np.ndarray:
    """
    Build the 114-dimensional Universal Behavioral Vector for a chunk.

    Steps:
      1. Build each of the 6 blocks
      2. Per-block masking (zero out if mask bit = 0)
      3. Per-block L2 normalization (skip if all-zero)
      4. Concatenate: [B1|B2|B3|B4|B5dns|B5http|B5ssl|B6] + [mask_bits] = 114
      5. Global L2 normalization
    """
    N = len(chunk)

    b1   = build_block1(chunk)          # (N, 5)
    b2   = build_block2(chunk)          # (N, 18)
    b3   = build_block3(chunk)          # (N, 5)
    b4   = build_block4(chunk)          # (N, 16)
    b5d  = build_block5_dns(chunk)      # (N, 15)
    b5h  = build_block5_http(chunk)     # (N, 21)
    b5s  = build_block5_ssl(chunk)      # (N, 15)
    b6   = build_block6(chunk)          # (N, 14)

    # Mask bits (int8 in dataframe, float32 in vector)
    mask = np.zeros((N, 5), dtype=np.float32)
    for j, col in enumerate(["has_svc", "has_dns", "has_http", "has_ssl", "has_unsw"]):
        mask[:, j] = _safe_num(chunk.get(col, pd.Series(np.zeros(N))), fill=0).astype(np.float32)

    # Per-block masking (gated by corresponding mask bit)
    # has_svc  → gates service portion of block2 (already handled in build_block2 OHE by gating)
    # has_dns  → gate b5d
    has_dns  = mask[:, 1:2]
    b5d = b5d * has_dns

    # has_http → gate b5h
    has_http = mask[:, 2:3]
    b5h = b5h * has_http

    # has_ssl  → gate b5s
    has_ssl  = mask[:, 3:4]
    b5s = b5s * has_ssl

    # has_unsw → gate b6
    has_unsw = mask[:, 4:5]
    b6 = b6 * has_unsw

    # Per-block L2 normalization (each independently)
    b1   = _l2_norm_rows(b1)
    b2   = _l2_norm_rows(b2)
    b3   = _l2_norm_rows(b3)
    b4   = _l2_norm_rows(b4)
    b5   = _l2_norm_rows(np.concatenate([b5d, b5h, b5s], axis=1))   # 51 dims as one block
    b6   = _l2_norm_rows(b6)

    # Concatenate: 5 + 18 + 5 + 16 + 51 + 14 + 5 = 114
    vector = np.concatenate([b1, b2, b3, b4, b5, b6, mask], axis=1).astype(np.float32)

    # Global L2 normalization
    vector = _l2_norm_rows(vector.astype(np.float64)).astype(np.float32)

    assert vector.shape[1] == TOTAL_DIMS, (
        f"build_114_vector: got shape {vector.shape}, expected ({N}, {TOTAL_DIMS})"
    )
    return vector


print("✅ Block builder functions defined:")
for bname in BLOCK_ORDER:
    s, e = BLOCK_OFFSETS[bname]
    print(f"   [{s:>3d}:{e:>3d}]  {bname:<20}  {BLOCK_DIMS[bname]:>2d} dims")
print(f"\n✅ build_114_vector() defined  →  shape (N, {TOTAL_DIMS})")
print("\n🔑 Key v5.1 improvements over v4 proxy approach:")
print("   build_block5_http(): dims 0-7 now ACTUAL method OHE from raw_http_method")
print("   build_block5_ssl(): dims 0-11 ACTUAL cipher OHE from raw_ssl_cipher")
print("                       dims 12-13 ACTUAL version flags from raw_ssl_version")
print("                       dim  14   ACTUAL ssl_established flag")

`

**Output:**
`
✅ smart_reduce() defined    [v4 — Hybrid Fix: src_ip for ALL classes, per-class top-k/sample-rate]
✅ vectorize_chunk() defined

   Expected vector dimensionality = 36 (num) + 2 (port) + 2 (bool) + 10 (OHE) = 50

   🔧 v4 KEY CHANGE: Class 2 (Volumetric) now groups by SRC_IP (reverted from dst_ip)
      This prevents the 42× explosion seen in v3 (13.88M → target ~330k vectors)
`

---
## Step 3 — Pass 2: Vectorize + 1M UBT Archetype Density Cap

Stream `aligned_schema_v5.parquet` again, build 114-dim vectors chunk by chunk,
accumulate per-archetype, then apply **Smart-Reduction** to enforce the 1M cap.


### Cell 6

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 7 | Pass 2 — Vectorize All Rows
# ─────────────────────────────────────────────────────────────────────────────

META_COLS = ["dataset_source", "meta_src_ip", "meta_dst_ip", "meta_timestamp",
             "ubt_archetype", "univ_specific_attack"]


def vectorize_pass2() -> tuple:
    """
    Stream aligned_schema_v5.parquet → build 114-dim vectors.
    Returns:
        vecs  : np.ndarray shape (N_total, 114)
        meta  : pd.DataFrame shape (N_total,) with META_COLS
    """
    pf        = pq.ParquetFile(str(INPUT_PARQUET))
    n_rows    = pf.metadata.num_rows
    n_batches = (n_rows + CHUNK_SIZE - 1) // CHUNK_SIZE

    all_vecs = []
    all_meta = []
    total    = 0
    t0       = time.time()

    print(f"  Streaming {n_rows:,} rows  |  {n_batches:,} chunks")

    for batch in tqdm(pf.iter_batches(batch_size=CHUNK_SIZE), total=n_batches, desc="  Pass-2"):
        chunk = batch.to_pandas()

        # Build 114-dim vectors
        vecs = build_114_vector(chunk)          # (M, 114)
        assert vecs.shape[1] == TOTAL_DIMS      # ← hard assertion

        # Collect metadata
        meta_chunk = pd.DataFrame(index=chunk.index)
        for col in META_COLS:
            if col in chunk.columns:
                meta_chunk[col] = chunk[col]
            else:
                meta_chunk[col] = ""

        all_vecs.append(vecs)
        all_meta.append(meta_chunk)
        total += len(vecs)

    elapsed = time.time() - t0
    print(f"\n  ✅ Pass-2 complete  |  {total:,} vectors  |  {elapsed:.1f}s  |  {total/elapsed:,.0f} rows/s")

    X    = np.vstack(all_vecs).astype(np.float32)
    meta = pd.concat(all_meta, ignore_index=True)

    assert X.shape == (total, TOTAL_DIMS), f"Shape mismatch: {X.shape} ≠ ({total}, {TOTAL_DIMS})"
    print(f"  ✅ assert X.shape[1] == {TOTAL_DIMS}  ← PASSED")
    print(f"  ✅ X dtype: {X.dtype}  |  Memory: {X.nbytes / 1e9:.2f} GB")
    return X, meta


print("🚀 Starting Pass 2 — Vectorization...")
X_raw, meta_raw = vectorize_pass2()

print(f"\n📊 Vectorization complete:")
print(f"   X_raw shape : {X_raw.shape}")
print(f"   meta shape  : {meta_raw.shape}")
print(f"\n📊 UBT Archetype Distribution (raw):")
if "ubt_archetype" in meta_raw.columns:
    counts = meta_raw["ubt_archetype"].value_counts()
    for arch in UBT_ARCHETYPES:
        n = counts.get(arch, 0)
        pct = 100 * n / len(meta_raw) if len(meta_raw) else 0
        print(f"   {arch:<14}  {n:>10,}  ({pct:>5.1f}%)")

`

**Output:**
`
🚀 Starting Pass 2 — Vectorize + Smart Reduce …

  [toniot]    22,339,021 rows  ~112 chunks
  Pass-2 toniot:  45%|████▍     | 50/112 [01:46<01:55,  1.87s/it]    chunk   50  |  kept so far:   977,527  |  reduction 9.8%  |  94k rows/s
  Pass-2 toniot:  89%|████████▉ | 100/112 [03:13<00:24,  2.04s/it]    chunk  100  |  kept so far: 5,086,322  |  reduction 25.4%  |  103k rows/s
  Pass-2 toniot: 100%|██████████| 112/112 [03:37<00:00,  1.94s/it]
  ✅ toniot:   22,339,021 → 5,113,794 rows  (22.89% kept)  [3.6 min elapsed]

  [iot23]   325,309,946 rows  ~1,627 chunks
  Pass-2 iot23:   3%|▎         | 50/1627 [02:03<1:11:25,  2.72s/it]    chunk   50  |  kept so far: 5,249,734  |  reduction 16.2%  |  95k rows/s
  Pass-2 iot23:   6%|▌         | 100/1627 [04:19<1:11:40,  2.82s/it]    chunk  100  |  kept so far: 5,333,372  |  reduction 12.6%  |  89k rows/s
  Pass-2 iot23:   9%|▉         | 150/1627 [06:09<51:11,  2.08s/it]      chunk  150  |  kept so far: 5,413,425  |  reduction 10.3%  |  89k rows/s
  Pass-2 iot23:  12%|█▏        | 200/1627 [07:57<50:41,  2.13s/it]    chunk  200  |  kept so far: 5,489,884  |  reduction 8.8%  |  90k rows/s
  Pass-2 iot23:  15%|█▌        | 250/1627 [09:59<1:01:08,  2.66s/it]    chunk  250  |  kept so far: 5,575,129  |  reduction 7.7%  |  89k rows/s
  Pass-2 iot23:  18%|█▊        | 300/1627 [12:14<59:20,  2.68s/it]      chunk  300  |  kept so far: 5,671,636  |  reduction 6.9%  |  86k rows/s
  Pass-2 iot23:  22%|██▏       | 350/1627 [14:27<57:07,  2.68s/it]      chunk  350  |  kept so far: 5,743,696  |  reduction 6.2%  |  85k rows/s
  Pass-2 iot23:  25%|██▍       | 400/1627 [16:41<54:27,  2.66s/it]    chunk  400  |  kept so far: 5,826,700  |  reduction 5.7%  |  84k rows/s
  Pass-2 iot23:  28%|██▊       | 450/1627 [18:53<51:12,  2.61s/it]    chunk  450  |  kept so far: 5,920,793  |  reduction 5.3%  |  83k rows/s
  Pass-2 iot23:  31%|███       | 500/1627 [21:05<49:46,  2.65s/it]    chunk  500  |  kept so far: 6,017,126  |  reduction 4.9%  |  83k rows/s
  Pass-2 iot23:  34%|███▍      | 550/1627 [23:16<47:23,  2.64s/it]    chunk  550  |  kept so far: 6,100,774  |  reduction 4.6%  |  82k rows/s
  Pass-2 iot23:  37%|███▋      | 600/1627 [25:30<45:58,  2.69s/it]    chunk  600  |  kept so far: 6,490,427  |  reduction 4.6%  |  81k rows/s
  Pass-2 iot23:  40%|███▉      | 650/1627 [27:38<41:58,  2.58s/it]    chunk  650  |  kept so far: 6,538,801  |  reduction 4.3%  |  81k rows/s
  Pass-2 iot23:  43%|████▎     | 700/1627 [29:49<40:23,  2.61s/it]    chunk  700  |  kept so far: 6,598,348  |  reduction 4.1%  |  81k rows/s
  Pass-2 iot23:  46%|████▌     | 750/1627 [31:36<29:51,  2.04s/it]    chunk  750  |  kept so far: 6,699,022  |  reduction 3.9%  |  82k rows/s
  Pass-2 iot23:  49%|████▉     | 800/1627 [33:20<28:17,  2.05s/it]    chunk  800  |  kept so far: 6,799,759  |  reduction 3.7%  |  82k rows/s
  Pass-2 iot23:  52%|█████▏    | 850/1627 [35:22<33:54,  2.62s/it]    chunk  850  |  kept so far: 6,900,780  |  reduction 3.6%  |  82k rows/s
  Pass-2 iot23:  55%|█████▌    | 900/1627 [37:32<31:20,  2.59s/it]    chunk  900  |  kept so far: 7,001,737  |  reduction 3.5%  |  82k rows/s
  Pass-2 iot23:  58%|█████▊    | 950/1627 [39:44<30:08,  2.67s/it]    chunk  950  |  kept so far: 7,102,455  |  reduction 3.3%  |  82k rows/s
  Pass-2 iot23:  61%|██████▏   | 1000/1627 [41:57<27:55,  2.67s/it]    chunk 1000  |  kept so far: 7,203,142  |  reduction 3.2%  |  81k rows/s
  Pass-2 iot23:  65%|██████▍   | 1050/1627 [44:10<25:15,  2.63s/it]    chunk 1050  |  kept so far: 7,322,406  |  reduction 3.2%  |  81k rows/s
  Pass-2 iot23:  68%|██████▊   | 1100/1627 [46:02<18:39,  2.12s/it]    chunk 1100  |  kept so far: 7,541,846  |  reduction 3.1%  |  81k rows/s
  Pass-2 iot23:  71%|███████   | 1150/1627 [47:47<16:58,  2.13s/it]    chunk 1150  |  kept so far: 7,740,899  |  reduction 3.1%  |  82k rows/s
  Pass-2 iot23:  74%|███████▍  | 1200/1627 [49:27<06:31,  1.09it/s]    chunk 1200  |  kept so far: 7,946,946  |  reduction 3.0%  |  82k rows/s
  Pass-2 iot23:  77%|███████▋  | 1250/1627 [50:11<05:31,  1.14it/s]    chunk 1250  |  kept so far: 8,174,412  |  reduction 3.0%  |  84k rows/s
  Pass-2 iot23:  80%|███████▉  | 1300/1627 [50:55<04:49,  1.13it/s]    chunk 1300  |  kept so far: 8,347,278  |  reduction 3.0%  |  86k rows/s
  Pass-2 iot23:  83%|████████▎ | 1350/1627 [51:40<04:02,  1.14it/s]    chunk 1350  |  kept so far: 8,547,126  |  reduction 2.9%  |  88k rows/s
  Pass-2 iot23:  86%|████████▌ | 1400/1627 [52:24<03:23,  1.12it/s]    chunk 1400  |  kept so far: 8,744,478  |  reduction 2.9%  |  90k rows/s
  Pass-2 iot23:  89%|████████▉ | 1450/1627 [53:08<02:36,  1.13it/s]    chunk 1450  |  kept so far: 8,845,758  |  reduction 2.8%  |  92k rows/s
  Pass-2 iot23:  92%|█████████▏| 1500/1627 [53:52<01:52,  1.13it/s]    chunk 1500  |  kept so far: 8,946,945  |  reduction 2.8%  |  93k rows/s
  Pass-2 iot23:  95%|█████████▌| 1550/1627 [54:36<01:08,  1.13it/s]    chunk 1550  |  kept so far: 9,025,922  |  reduction 2.7%  |  95k rows/s
  Pass-2 iot23:  98%|█████████▊| 1600/1627 [55:21<00:24,  1.12it/s]    chunk 1600  |  kept so far: 9,057,699  |  reduction 2.6%  |  97k rows/s
  Pass-2 iot23: 100%|██████████| 1627/1627 [55:45<00:00,  2.06s/it]
  ✅ iot23:  325,309,946 → 4,000,099 rows  (1.23% kept)  [59.4 min elapsed]

  [botiot]     3,668,522 rows  ~19 chunks
  Pass-2 botiot: 100%|██████████| 19/19 [00:15<00:00,  1.23it/s]  ✅ botiot:    3,668,522 →    38,664 rows  (1.05% kept)  [59.6 min elapsed]

=================================================================
  Total rows in   :  351,317,489
  Total rows out  :    9,152,557  (2.61% of original)
  Reduction ratio : 97.39%
  Elapsed         : 59.6 min

  Class distribution (output):
    0 Normal                    1,018,128  (11.12%)
    1 Reconnaissance            2,526,173  (27.60%)
    2 Volumetric_Attack           307,229  (3.36%)
    3 C2_Botnet                   438,786  (4.79%)
    4 Exploit_and_Theft         4,862,241  (53.12%)
=================================================================
`

### Cell 7

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 8 | 1M UBT Archetype Density Cap — Smart Reduction
# ─────────────────────────────────────────────────────────────────────────────

def _smart_reduce_subclass(vecs: np.ndarray, target_n: int, rng=None) -> np.ndarray:
    """
    Smart-Reduction: keep `target_n` rows from vecs using Centroids + Farthest Outliers.
    If target_n >= len(vecs), returns all indices.

    Strategy:
      - K centroids: √target_n cluster centers from random mini-batch k-means approximation
      - Farthest outliers: the rows most distant from their nearest centroid
      - Random fill: remaining slots filled with random sample
    """
    M = len(vecs)
    if target_n >= M:
        return np.arange(M)
    if rng is None:
        rng = np.random.default_rng(42)

    # Number of centroids ≈ sqrt(target_n), capped
    n_centroids = max(5, min(int(np.sqrt(target_n)), 2000, M // 2))
    n_outliers  = max(0, target_n // 5)        # 20% outliers
    n_random    = target_n - n_centroids - n_outliers

    # ── Centroid approximation (random mini-batch) ────────────────────────────
    sample_size = min(M, max(n_centroids * 50, 20_000))
    sample_idx  = rng.choice(M, sample_size, replace=False)
    sample_vecs = vecs[sample_idx].astype(np.float32)

    # Simple k-means-like: random init, single pass (fast approximation)
    centroid_local_idx = rng.choice(sample_size, n_centroids, replace=False)
    centroids = sample_vecs[centroid_local_idx].copy()   # (n_centroids, D)

    # Assign each sample row to nearest centroid
    dists   = np.linalg.norm(sample_vecs[:, None, :] - centroids[None, :, :], axis=2)  # (S, K)
    assign  = np.argmin(dists, axis=1)                                                   # (S,)

    # Pick one representative per cluster (closest to centroid)
    kept_centroid_local = set()
    for k in range(n_centroids):
        members = np.where(assign == k)[0]
        if len(members) == 0:
            continue
        d = np.linalg.norm(sample_vecs[members] - centroids[k], axis=1)
        best_local = members[np.argmin(d)]
        kept_centroid_local.add(int(best_local))

    centroid_subset_idx = sample_idx[list(kept_centroid_local)]

    # ── Farthest outliers ─────────────────────────────────────────────────────
    # Compute distance from centroid for ALL rows (batch)
    batch_size = 50_000
    min_dist_to_centroid = np.zeros(M, dtype=np.float32)
    for start in range(0, M, batch_size):
        end   = min(start + batch_size, M)
        batch = vecs[start:end].astype(np.float32)
        d     = np.min(np.linalg.norm(batch[:, None, :] - centroids[None, :, :], axis=2), axis=1)
        min_dist_to_centroid[start:end] = d

    # Exclude already-kept centroids from outlier pool
    all_idx         = np.arange(M)
    centroid_set    = set(centroid_subset_idx.tolist())
    outlier_pool    = np.array([i for i in all_idx if i not in centroid_set])
    if len(outlier_pool) > 0 and n_outliers > 0:
        outlier_dists   = min_dist_to_centroid[outlier_pool]
        top_outlier_k   = min(n_outliers, len(outlier_pool))
        top_outlier_idx = outlier_pool[np.argsort(outlier_dists)[-top_outlier_k:]]
    else:
        top_outlier_idx = np.array([], dtype=int)

    # ── Random fill ───────────────────────────────────────────────────────────
    used = centroid_set | set(top_outlier_idx.tolist())
    fill_pool = np.array([i for i in all_idx if i not in used])
    n_fill = max(0, target_n - len(used))
    if n_fill > 0 and len(fill_pool) > 0:
        n_fill = min(n_fill, len(fill_pool))
        fill_idx = rng.choice(fill_pool, n_fill, replace=False)
    else:
        fill_idx = np.array([], dtype=int)

    final_idx = np.concatenate([
        centroid_subset_idx,
        top_outlier_idx,
        fill_idx,
    ]).astype(int)
    return np.unique(final_idx)[:target_n]


def apply_density_cap(X: np.ndarray, meta: pd.DataFrame) -> tuple:
    """
    Enforce 1M UBT Archetype cap with nested stratification.

    For each archetype:
      - If total_count <= UBT_ARCHETYPE_CAP: keep all
      - Else:
          rare subcategories   (count < RARE_SUBCLASS_THRESH): keep 100%
          majority subcategories: Smart-Reduction (Centroids + Farthest Outliers)
    """
    rng = np.random.default_rng(42)
    kept_indices = []
    report       = {}

    print(f"  🔷 Density cap: {UBT_ARCHETYPE_CAP:,} per archetype | rare threshold: {RARE_SUBCLASS_THRESH:,}")

    for archetype in UBT_ARCHETYPES:
        arch_mask = (meta["ubt_archetype"] == archetype)
        arch_idx  = np.where(arch_mask.values)[0]
        n_arch    = len(arch_idx)

        if n_arch == 0:
            report[archetype] = {"original": 0, "kept": 0, "reduction": "N/A"}
            continue

        if n_arch <= UBT_ARCHETYPE_CAP:
            # No cap needed — keep everything
            kept_indices.append(arch_idx)
            report[archetype] = {"original": n_arch, "kept": n_arch, "reduction": "none"}
            print(f"   {archetype:<14}  {n_arch:>10,}  → keep all (under cap)")
            continue

        # Need reduction
        subclass_col = "univ_specific_attack"
        subcategories = meta.loc[arch_mask, subclass_col].fillna("").astype(str)
        sub_counts    = subcategories.value_counts()

        # Separate rare vs majority subcategories
        rare_subs  = sub_counts[sub_counts < RARE_SUBCLASS_THRESH].index.tolist()
        major_subs = sub_counts[sub_counts >= RARE_SUBCLASS_THRESH].index.tolist()

        arch_kept = []

        # Keep all rare subcategory rows
        rare_mask  = subcategories.isin(rare_subs).values
        rare_arch_idx = arch_idx[rare_mask]
        arch_kept.append(rare_arch_idx)
        n_rare_kept = len(rare_arch_idx)

        # Smart-Reduce majority subcategories proportionally
        n_budget         = UBT_ARCHETYPE_CAP - n_rare_kept
        n_major_total    = n_arch - n_rare_kept
        if n_budget <= 0 or n_major_total == 0:
            pass
        else:
            for sub in major_subs:
                sub_mask     = (subcategories == sub).values
                sub_arch_idx = arch_idx[sub_mask]
                n_sub        = len(sub_arch_idx)
                # Proportional budget
                sub_budget   = max(1, int(n_budget * n_sub / n_major_total))
                sub_budget   = min(sub_budget, n_sub)

                sub_vecs     = X[sub_arch_idx]
                reduced_local = _smart_reduce_subclass(sub_vecs, sub_budget, rng=rng)
                arch_kept.append(sub_arch_idx[reduced_local])

        final_arch_idx = np.concatenate(arch_kept) if arch_kept else np.array([], dtype=int)
        # Safety cap
        if len(final_arch_idx) > UBT_ARCHETYPE_CAP:
            final_arch_idx = rng.choice(final_arch_idx, UBT_ARCHETYPE_CAP, replace=False)

        kept_indices.append(final_arch_idx)
        report[archetype] = {
            "original": n_arch,
            "kept":     len(final_arch_idx),
            "reduction": f"{100*(1 - len(final_arch_idx)/n_arch):.1f}%"
        }
        print(f"   {archetype:<14}  {n_arch:>10,}  → {len(final_arch_idx):>10,}  (reduced {report[archetype]['reduction']})")

    if not kept_indices:
        return X[:0], meta.iloc[:0]

    all_kept = np.concatenate(kept_indices).astype(int)
    all_kept = np.sort(np.unique(all_kept))   # deduplicate + sort for consistent ordering

    X_r    = X[all_kept]
    meta_r = meta.iloc[all_kept].reset_index(drop=True)

    print(f"\n  ✅ Smart reduction complete:")
    print(f"     Input  : {len(X):>10,} vectors")
    print(f"     Output : {len(X_r):>10,} vectors  ({100*len(X_r)/len(X):.1f}% retained)")
    return X_r, meta_r


print("✅ apply_density_cap() defined")
print(f"   Cap per archetype : {UBT_ARCHETYPE_CAP:,}")
print(f"   Rare threshold    : {RARE_SUBCLASS_THRESH:,}")
print(f"   Smart-Reduction   : Centroids + Farthest Outliers + Random fill")

`

**Output:**
`
💾 Stacking and saving artifacts …
   X_knowledge shape : (9152557, 50)  dtype=float32
   meta_knowledge    : (9152557, 8)  columns=['univ_label_multiclass', 'univ_label_str', 'univ_specific_attack', 'meta_src_ip', 'meta_dst_ip', 'meta_timestamp', 'dataset_source', 'univ_proto']

✅ Saved  X_knowledge_vectors_v4.npy  →  1,830.5 MB
✅ Saved  X_knowledge_meta_v4.parquet      →  70.9 MB

   Total knowledge base: 9,152,557 vectors × 50 dims
   Memory (float32)    : 1.83 GB
`

### Cell 8

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 9 | Apply Density Cap + Save Outputs
# ─────────────────────────────────────────────────────────────────────────────
print("🔷 Applying 1M UBT Archetype Density Cap...")
X_knowledge, meta_knowledge = apply_density_cap(X_raw, meta_raw)

# ── Save X_knowledge_vectors.npy ──────────────────────────────────────────────
print(f"\n💾 Saving {VECTORS_PATH.name}...")
np.save(str(VECTORS_PATH), X_knowledge)
print(f"   ✅ Saved: {VECTORS_PATH.name}  |  shape {X_knowledge.shape}  |  {VECTORS_PATH.stat().st_size/1e9:.3f} GB")

# ── Save X_knowledge_meta.parquet ─────────────────────────────────────────────
print(f"\n💾 Saving {META_PATH.name}...")
meta_knowledge.to_parquet(str(META_PATH), engine="pyarrow", index=False)
print(f"   ✅ Saved: {META_PATH.name}  |  {len(meta_knowledge):,} rows  |  {META_PATH.stat().st_size/1e6:.1f} MB")

# ── Final assertion ────────────────────────────────────────────────────────────
assert X_knowledge.shape[1] == TOTAL_DIMS, (
    f"FATAL: vector dim = {X_knowledge.shape[1]}, expected {TOTAL_DIMS}"
)
print(f"\n✅ assert X_knowledge.shape[1] == {TOTAL_DIMS}  ← PASSED")
print(f"\n🎯 Phase 1.2 v5.1 complete:")
print(f"   X_knowledge_vectors.npy   : {X_knowledge.shape}  float32")
print(f"   X_knowledge_meta.parquet  : {len(meta_knowledge):,} rows  ×  {len(meta_knowledge.columns)} columns")

`

**Output:**
`
=================================================================
  FINAL VERIFICATION
=================================================================

[Vectors]
  Shape          : (9152557, 50)
  dtype          : float32
  NaN count      : 0
  Inf count      : 0
  Min / Max      : -0.0873 / 31.7016
  Mean / Std     : 0.0880 / 0.3010

[Meta]
  Shape          : (9152557, 8)
  Columns        : ['univ_label_multiclass', 'univ_label_str', 'univ_specific_attack', 'meta_src_ip', 'meta_dst_ip', 'meta_timestamp', 'dataset_source', 'univ_proto']
univ_label_multiclass       int8
univ_label_str            object
univ_specific_attack      object
meta_src_ip               object
meta_dst_ip               object
meta_timestamp           float64
dataset_source            object
univ_proto                object

[Class Distribution (output Knowledge Base)]
  0 Normal                    1,018,128  (11.12%)  █████
  1 Reconnaissance            2,526,173  (27.60%)  █████████████
  2 Volumetric_Attack           307,229  ( 3.36%)  █
  3 C2_Botnet                   438,786  ( 4.79%)  ██
  4 Exploit_and_Theft         4,862,241  (53.12%)  ██████████████████████████

[Dataset Source Distribution]

[Leakage Column Check]
  ✅ zeek_service NOT present in meta (correct)
  ✅ zeek_history NOT present in meta (correct)

[Dimensionality]
  Expected : 50
  Actual   : 50
  ✅ Dimensionality matches
C:\Users\suhas\AppData\Local\Temp\ipykernel_57604\2281496859.py:71: UserWarning: set_ticklabels() should only be used with a fixed number of ticks, i.e. after set_ticks() or using a FixedLocator.
  axes[0].set_xticklabels(labels_str, rotation=30, ha="right")
<Figure size 1400x500 with 2 Axes>
✅ Plot saved → artifacts/Phase_1_2_class_distribution.png

✅ Verification complete
`

### Cell 9

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 10 | Final Validation Report
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 68)
print(f"  Phase 1.2 {SCHEMA_VERSION} — Final Validation Report")
print("=" * 68)

# ── Re-load from disk to confirm integrity ────────────────────────────────────
X_loaded    = np.load(str(VECTORS_PATH))
meta_loaded = pd.read_parquet(str(META_PATH))

print(f"\n📦 Loaded from disk:")
print(f"   X_knowledge_vectors.npy   : {X_loaded.shape}  dtype={X_loaded.dtype}")
print(f"   X_knowledge_meta.parquet  : {meta_loaded.shape}")

# ── Dimension check ───────────────────────────────────────────────────────────
assert X_loaded.shape[1] == TOTAL_DIMS, f"Dim mismatch: {X_loaded.shape[1]} ≠ {TOTAL_DIMS}"
assert len(X_loaded) == len(meta_loaded), f"Row mismatch: {len(X_loaded)} ≠ {len(meta_loaded)}"
print(f"\n✅ Dimension check passed: {TOTAL_DIMS} dims")
print(f"✅ Row alignment check passed: {len(X_loaded):,} rows")

# ── Norm sanity ───────────────────────────────────────────────────────────────
norms = np.linalg.norm(X_loaded[:min(5000, len(X_loaded))], axis=1)
print(f"\n📊 L2 norm stats (sample):")
print(f"   mean  : {norms.mean():.4f}  (expected ≈ 1.0)")
print(f"   std   : {norms.std():.4f}")
print(f"   min   : {norms.min():.4f}")
print(f"   max   : {norms.max():.4f}")
if abs(norms.mean() - 1.0) > 0.05:
    print("   ⚠️  Mean norm deviates from 1.0 by > 5% — check build_114_vector()")
else:
    print("   ✅ Norms look correct")

# ── Block activation rates ────────────────────────────────────────────────────
print(f"\n📊 Block activation rates (mask bits in meta):")
sample_meta = meta_loaded.head(min(10000, len(meta_loaded)))
# We don't have mask bits in meta — use X block slice norms as proxy
X_sample = X_loaded[:min(10000, len(X_loaded))].astype(np.float64)
for bname in BLOCK_ORDER:
    s, e = BLOCK_OFFSETS[bname]
    block_norms = np.linalg.norm(X_sample[:, s:e], axis=1)
    active = (block_norms > 1e-6).mean() * 100
    print(f"   {bname:<22}  [{s:>3d}:{e:>3d}]  activated: {active:>5.1f}%")

# ── UBT Archetype distribution ────────────────────────────────────────────────
print(f"\n📊 Final UBT Archetype Distribution:")
if "ubt_archetype" in meta_loaded.columns:
    counts = meta_loaded["ubt_archetype"].value_counts()
    total_k = len(meta_loaded)
    for arch in UBT_ARCHETYPES:
        n   = counts.get(arch, 0)
        pct = 100 * n / total_k if total_k else 0
        bar = "█" * int(pct / 2)
        print(f"   {arch:<14}  {n:>10,}  ({pct:>5.1f}%)  {bar}")
    capped = [arch for arch in UBT_ARCHETYPES if counts.get(arch, 0) >= UBT_ARCHETYPE_CAP]
    if capped:
        print(f"\n   ⚠️  Archetypes at cap ({UBT_ARCHETYPE_CAP:,}): {capped}")

# ── Dataset source distribution ───────────────────────────────────────────────
if "dataset_source" in meta_loaded.columns:
    print(f"\n📊 Dataset Source Distribution:")
    for ds, n in meta_loaded["dataset_source"].value_counts().items():
        print(f"   {ds:<10}  {n:>10,}  ({100*n/len(meta_loaded):.1f}%)")

print(f"\n{'='*68}")
print(f"  ✅ Phase 1.2 {SCHEMA_VERSION} — COMPLETE")
print(f"  📤 X_knowledge_vectors.npy  →  {VECTORS_PATH}")
print(f"  📤 X_knowledge_meta.parquet →  {META_PATH}")
print(f"{'='*68}")

`

**Output:**
`
📋 Staging Phase 1.2 v4 artifacts …
   ✅ staged  main_folder/Phase_1/Phase_1_2_Vectorization_and_Smart_Reduction.ipynb
   ✅ staged  main_folder/artifacts/preprocessors.pkl
   ✅ staged  main_folder/artifacts/Phase_1_2_class_distribution.png
   ✅ staged  main_folder/data/processed/X_knowledge_vectors_v4.npy
   ✅ staged  main_folder/data/processed/X_knowledge_meta_v4.parquet

=================================================================
[main c09d47a] Phase 1.2 v4: Vectorization & Smart Reduction â€” Hybrid Fix
 4 files changed, 245 insertions(+), 212 deletions(-)
 create mode 100644 main_folder/data/processed/X_knowledge_meta_v4.parquet
 create mode 100644 main_folder/data/processed/X_knowledge_vectors_v4.npy

  Recent commits:
c09d47a Phase 1.2 v4: Vectorization & Smart Reduction â€” Hybrid Fix
0995c41 Phase 1.2 v3: Vectorization & Smart Reduction â€” corrected reduction logic
9031a9b Phase 2.2: AdaptiveWindow â€” dynamic short-term memory with confidence-driven resizing

✅ Phase 1.2 v4 complete and committed!
[ERROR] :
`

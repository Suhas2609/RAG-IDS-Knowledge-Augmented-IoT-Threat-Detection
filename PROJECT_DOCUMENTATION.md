# RAG-IDS: Knowledge-Augmented IoT Threat Detection

## Complete Project Documentation — Every Phase, Every File, Every Decision

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Data Pipeline Overview: 22.3M Rows to 457K Vectors](#3-data-pipeline-overview-223m-rows-to-457k-vectors)
4. [Phase 0 — Data Understanding](#4-phase-0--data-understanding)
5. [Phase 1 — Feature Decision and Preprocessing Design](#5-phase-1--feature-decision-and-preprocessing-design)
6. [Phase 2 — Data Preprocessing Pipeline](#6-phase-2--data-preprocessing-pipeline)
    - [Phase 2.1 — Data Loading and Schema Validation](#61-phase-21--data-loading-and-schema-validation)
    - [Phase 2.2 — Encoding and Normalization](#62-phase-22--encoding-and-normalization)
    - [Phase 2.3 — Vector Generation](#63-phase-23--vector-generation)
    - [Phase 2.4 — Hybrid Temporal Curation](#64-phase-24--hybrid-temporal-curation)
    - [Phase 2.5 — Curation Validation Suite](#65-phase-25--curation-validation-suite)
7. [Phase 3 — RAG-IDS Inference and Decision System](#7-phase-3--rag-ids-inference-and-decision-system)
    - [Phase 3.1 — Adaptive Time Window](#71-phase-31--adaptive-time-window)
    - [Phase 3.2 — ChromaDB Retrieval](#72-phase-32--chromadb-retrieval)
    - [Phase 3.3 — Evidence Accumulation](#73-phase-33--evidence-accumulation)
    - [Phase 3.4 — Quantum-Inspired Fusion](#74-phase-34--quantum-inspired-fusion)
    - [Phase 3.5 — Decision Logic](#75-phase-35--decision-logic)
    - [Phase 3.6 — Explainability Module](#76-phase-36--explainability-module)
8. [Phase 4 — Production Deployment](#8-phase-4--production-deployment)
    - [ragids_engine.py — The Brain](#81-ragids_enginepy--the-brain)
    - [threat_api.py — The Gateway](#82-threat_apipy--the-gateway)
    - [threat_dashboard.py — The War Room](#83-threat_dashboardpy--the-war-room)
    - [launch_system.py — The Launcher](#84-launch_systempy--the-launcher)
    - [ragids_demo_runner.py — The Simulator](#85-ragids_demo_runnerpy--the-simulator)
    - [test_integration.py — The Test Harness](#86-test_integrationpy--the-test-harness)
    - [Supporting Files](#87-supporting-files)
9. [End-to-End Data Pipeline: From Raw CSV to Live Detection](#9-end-to-end-data-pipeline-from-raw-csv-to-live-detection)
10. [System Performance Metrics](#10-system-performance-metrics)
11. [What Was Not Implemented](#11-what-was-not-implemented)
12. [Project Scope Alignment](#12-project-scope-alignment)

---

## 1. Project Overview

**Project Title:** Quantum-RAG Knowledge Fusion for Adaptive IoT Intrusion Detection

**Core Idea:** Build an Intrusion Detection System (IDS) for IoT networks that uses Retrieval-Augmented Generation (RAG) principles to detect network attacks. Instead of training a traditional machine learning classifier, we convert historical attack traffic into vector embeddings, store them in a vector database (ChromaDB), and at detection time, we retrieve the most similar known attack patterns to classify new traffic in real time.

**What Makes This Different From a Traditional IDS:**

- **No model training required.** The system does not train a neural network or decision tree. Instead, it builds a "behavioral memory" of known attacks in a vector database and uses similarity-based retrieval at inference time.
- **Quantum-inspired probability fusion.** Instead of a simple voting mechanism, the system uses quantum mechanics-inspired amplitude-to-probability conversion (Born rule) to fuse evidence from multiple retrieved matches into a unified threat probability distribution.
- **Adaptive temporal windowing.** The system does not classify individual packets in isolation. It maintains a dynamic time window that expands when attack-like patterns are detected and shrinks during benign periods, ensuring decisions are based on behavioral context rather than single observations.
- **Full explainability.** Every detection decision comes with a human-readable narrative explaining what was detected, why it was classified that way, which historical patterns matched, and what actions should be taken.

**Technology Stack:**

| Component | Technology |
|-----------|------------|
| Dataset | TON-IoT Processed Network (UNSW Sydney) |
| Vector Database | ChromaDB (PersistentClient, cosine distance, HNSW indexing) |
| API Server | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly |
| Language | Python 3.13 |
| Vector Dimensions | 99-dimensional float32 embeddings |
| Data Size | 22,339,021 raw rows → 457,622 curated vectors |

---

## 2. Architecture Summary

The project is organized into 5 phases (Phase 0 through Phase 4), each building on the previous:

```
Phase 0: Understand the raw data (read-only exploration)
Phase 1: Decide what features to keep and how to process them (frozen decisions)
Phase 2: Execute the preprocessing pipeline (load → encode → vectorize → curate → validate)
Phase 3: Build the detection pipeline (window → retrieve → accumulate → fuse → decide → explain)
Phase 4: Deploy as a production system (API + Dashboard + Launcher)
```

**The data flows through these stages:**

```
23 Raw CSV Files (22,339,021 rows x 47 columns)
    │
    ▼ Phase 0: Understand what we have
    │
    ▼ Phase 1: Decide to keep 33 features, drop 14
    │
    ▼ Phase 2.1: Load + validate against frozen schema → 22,339,021 x 33
    │
    ▼ Phase 2.2: Encode categoricals + normalize numericals → 22,339,021 x 99
    │
    ▼ Phase 2.3: Convert to float32 NumPy vectors → 22,339,021 vectors (8.24 GB)
    │
    ▼ Phase 2.4: Hybrid temporal + clustering curation → 457,622 vectors in ChromaDB
    │
    ▼ Phase 2.5: Validate curation preserves behavior → 6/6 checks PASSED
    │
    ▼ Phase 3: Real-time detection using ChromaDB retrieval
    │
    ▼ Phase 4: Production API + Dashboard deployment
```

---

## 3. Data Pipeline Overview: 22.3M Rows to 457K Vectors

This section provides a high-level view of how the dataset shrinks from 22.3 million raw network flow records to 457,622 curated behavioral vectors suitable for ChromaDB ingestion. Each step is explained in detail in the phase-specific sections below.

| Stage | Rows | Columns/Dims | Size | What Happens |
|-------|------|-------------|------|--------------|
| Raw CSVs | 22,339,021 | 47 | ~33.7 GB | Original TON-IoT network capture data |
| After Phase 2.1 (Clean) | 22,339,021 | 33 | Reduced | Drop 14 identity/label columns, validate schema |
| After Phase 2.2 (Encode) | 22,339,021 | 99 | Larger | One-hot encoding expands 33 mixed-type → 99 numeric |
| After Phase 2.3 (Vectorize) | 22,339,021 | 99 | 8.24 GB | Convert to float32 NumPy vectors |
| After Phase 2.4 (Curate) | **457,622** | 99 | ~0.46 GB | Hybrid temporal + MiniBatchKMeans clustering |
| Compression Ratio | — | — | — | **48.8x reduction** (2.05% of original) |

**Why not store all 22.3M vectors in ChromaDB?**

Storing 22.3 million 99-dimensional vectors would require approximately 8.24 GB of memory just for the raw vectors, plus ChromaDB's HNSW index overhead. Query latency would degrade significantly — the system targets sub-50ms retrieval per flow. The curation step in Phase 2.4 selects 457,622 representative vectors that preserve 95.85% retrieval recall, meaning the curated database returns nearly identical results to the full database for similarity queries. This was mathematically validated in Phase 2.5.

---

## 4. Phase 0 — Data Understanding

**File:** `Phase_0/Phase_0_Data_Understanding.ipynb`
**Notebook Structure:** 30 cells, approximately 2,002 lines
**Purpose:** Read-only exploration of the TON-IoT Processed Network dataset. This phase touches nothing — it only observes, counts, and reports. No features are modified, dropped, or encoded. The goal is to produce a complete inventory of what exists in the data so that Phase 1 can make informed decisions.

### 4.1 What This Notebook Does

The notebook loads all 23 CSV files from the `data/ton_iot_processed_network/` directory and concatenates them into a single DataFrame. It then performs the following analyses:

**Step 1 — File Discovery and Loading:**
- Discovers 23 CSV files named `Network_dataset_1.csv` through `Network_dataset_23.csv`
- Loads each file sequentially with progress tracking
- Concatenates into one unified DataFrame

**Step 2 — Shape and Size Analysis:**
- Total rows: **22,339,021**
- Total columns: **47**
- Total dataset size in memory: **33,760.3 MB** (~33.7 GB)

**Step 3 — Column Type Classification:**
- 17 numerical columns (int64/float64)
- 30 categorical/object columns (strings)
- Every column is inventoried with its dtype, unique value count, null count, and sample values

**Step 4 — Attack Type Distribution:**
The dataset contains 10 distinct attack types plus normal traffic:

| Attack Type | Count | Percentage |
|-------------|-------|------------|
| scanning | 7,140,161 | 31.96% |
| ddos | 6,165,008 | 27.60% |
| dos | 3,375,328 | 15.11% |
| xss | 2,108,944 | 9.44% |
| password | 1,718,568 | 7.69% |
| normal | 796,380 | 3.56% |
| backdoor | 508,116 | 2.27% |
| injection | 452,659 | 2.03% |
| ransomware | 72,805 | 0.33% |
| mitm | 1,052 | 0.005% |

**Binary Label Distribution:**
- Attack (label=1): **21,542,641 rows** (96.44%)
- Normal (label=0): **796,380 rows** (3.56%)

This is a heavily imbalanced dataset — attacks outnumber normal traffic by 27:1.

**Step 5 — Placeholder Analysis:**
A critical discovery: the character `"-"` (a single dash) appears throughout the dataset. This is **NOT missing data**. It means "not applicable for this protocol." For example:
- DNS fields contain `"-"` for non-DNS flows (TCP connections to HTTP servers will never have DNS query data)
- SSL fields contain `"-"` for non-SSL flows
- HTTP fields contain `"-"` for non-HTTP flows

Placeholder prevalence:
- DNS fields: ~93% placeholders (only ~7% of flows are DNS)
- SSL fields: ~99.9% placeholders (very few flows use SSL)
- HTTP fields: ~99.9% placeholders (very few flows are HTTP)

**Zero NaN values were found in the entire dataset.** All apparent "missing" data is actually the `"-"` placeholder with a specific semantic meaning.

**Step 6 — Protocol Distribution:**
- TCP: **92.38%** of all flows
- UDP: **7.54%**
- ICMP: **0.08%**

**Step 7 — Feature Role Classification:**
Each of the 47 columns was classified into a role:

| Role | Count | Examples |
|------|-------|---------|
| Unknown/Needs Review | 24 | dns_query, http_uri, ssl_subject, etc. |
| Behavioral | 7 | duration, src_bytes, dst_bytes, conn_state, missed_bytes, src_pkts, dst_pkts |
| Label/Ground Truth | 6 | type, label |
| Contextual | 5 | ts, proto, service, src_port, dst_port |
| Identifier | 5 | uid, src_ip, dst_ip |

The 7 behavioral features were identified as the primary candidates for the IDS — they describe *how* traffic behaves rather than *who* is communicating.

### 4.2 Artifacts Saved

Phase 0 produces 6 artifacts in `Phase_0/artifacts/`:

1. `column_inventory.csv` — Complete inventory of all 47 columns with dtypes, unique counts, null counts
2. `role_classifications.csv` — Role assignment for each column (Behavioral, Contextual, Identifier, Label, Unknown)
3. `feature_meanings.csv` — Human-readable description of what each column represents
4. `placeholder_analysis.csv` — Which columns contain the `"-"` placeholder, how many, and what percentage
5. `files_summary.csv` — Per-file row counts for all 23 CSV files
6. `Phase_0_Data_Understanding_Report.md` — Markdown summary report

### 4.3 Key Takeaways for Later Phases

1. The dataset is massive (22.3M rows) and will require chunked processing
2. The `"-"` placeholder must be handled semantically, not as null/missing
3. The dataset is 96.4% attack traffic — the IDS needs to handle class imbalance
4. Only 7 features are purely behavioral; the rest require careful analysis in Phase 1
5. Rare attack types (ransomware: 0.33%, mitm: 0.005%) need special attention during curation to ensure they are not lost

---

## 5. Phase 1 — Feature Decision and Preprocessing Design

**File:** `Phase_1/Phase_1_Feature_Decision_and_Preprocessing_Design.ipynb`
**Purpose:** This is the **DECISION PHASE** — the single most important notebook in the project. It makes and freezes all feature engineering decisions *before* any actual preprocessing happens. The output is a `frozen_schema.json` file that is immutable for all later phases. No encoding, no scaling, no vectorization happens here — only decisions.

**Strict Rules Enforced:**
- No embedding generation
- No model training
- No ChromaDB usage
- No retrieval logic
- Only analysis and decision-making

### 5.1 Feature Retention Decisions: KEEP vs DROP

Out of the original 47 columns, Phase 1 decides to **keep 33 features (70.2%)** and **drop 14 features (29.8%)**.

#### The 14 DROPPED Features and Why

| Feature | Original Role | Why Dropped |
|---------|--------------|-------------|
| `ts` | Contextual | Timestamp is environment-specific, does not generalize across networks |
| `uid` | Identifier | Unique connection ID, no behavioral value |
| `src_ip` | Identifier | Source IP is identity-specific, prevents generalization to new networks |
| `dst_ip` | Identifier | Destination IP is identity-specific |
| `type` | Label/Ground Truth | Attack type label — used only for evaluation, never as an input feature |
| `label` | Label/Ground Truth | Binary label (0/1) — the target variable, not a feature |
| `dns_query` | Unknown | High cardinality (17,880 unique), identity-revealing domain names |
| `http_uri` | Unknown | High cardinality, identity-revealing URL paths |
| `http_referrer` | Unknown | Identity-revealing referrer URLs |
| `http_user_agent` | Unknown | Identity-revealing client information |
| `ssl_subject` | Unknown | Certificate subject is identity-revealing |
| `ssl_issuer` | Unknown | Certificate issuer is identity-revealing |
| `weird_name` | Unknown | High cardinality, noisy anomaly descriptions |
| `weird_addl` | Unknown | Too sparse — 99.5% placeholders |

**Design Principle:** Drop all identity-revealing features (IPs, UIDs, timestamps, domains, URIs, certificates) and all label columns. The IDS must generalize on *behavioral patterns* — not memorize network-specific identities.

#### The 33 KEPT Features, Grouped by Category

**Behavioral — Core IDS Signals (7 features):**
- `duration` — Attack duration patterns, critical for DoS/anomaly detection
- `src_bytes` — Data volume sent, indicates exfiltration, flooding, or normal usage
- `dst_bytes` — Response size, reveals server behavior under attack
- `src_pkts` — Packet count patterns distinguish scanning/flooding/normal traffic
- `dst_pkts` — Server packet responses indicate service type and anomalies
- `src_ip_bytes` — IP-layer volume (includes protocol overhead)
- `dst_ip_bytes` — IP-layer response volume

**Contextual — Protocol and State (5 features):**
- `proto` — Protocol type (tcp/udp/icmp), essential for attack context
- `service` — Service type (http/dns/ssh), identifies attack targets
- `conn_state` — Connection state reveals incomplete/rejected connections
- `src_port` — Source port reveals client behavior (ephemeral vs well-known)
- `dst_port` — Destination port identifies target service

**TCP-Specific (1 feature):**
- `missed_bytes` — TCP lost data indicates packet loss or evasion

**DNS-Specific (7 features):**
- `dns_qclass`, `dns_qtype`, `dns_rcode` — DNS query characteristics for tunneling/DGA detection
- `dns_AA`, `dns_RD`, `dns_RA`, `dns_rejected` — DNS flags for reconnaissance detection

**HTTP-Specific (8 features):**
- `http_trans_depth` — Transaction depth reveals pipelining
- `http_method` — GET/POST indicates attack type
- `http_version` — Protocol version shows legacy vulnerabilities
- `http_request_body_len`, `http_response_body_len` — Content sizes indicate upload attacks or data leakage
- `http_status_code` — Status code patterns indicate scanning/brute-force
- `http_orig_mime_types`, `http_resp_mime_types` — Content types for attack detection

**SSL-Specific (4 features):**
- `ssl_version` — SSL/TLS version reveals downgrade attacks
- `ssl_cipher` — Cipher suite indicates weak cryptography
- `ssl_resumed` — Session resumption patterns show automation
- `ssl_established` — Handshake success/failure indicates MITM

**Zeek Anomaly (1 feature):**
- `weird_notice` — Boolean flag for anomalies detected by the Zeek network monitor

### 5.2 Placeholder Handling Strategy

The `"-"` placeholder is handled with three semantic strategies:

| Strategy | Apply To | Meaning | Encoding |
|----------|----------|---------|----------|
| `protocol_na` | 21 protocol-specific features | The protocol does not apply to this flow | Categorical → `NOT_APPLICABLE`; Numerical → `-1` |
| `unknown_service` | `service` | Zeek could not identify the service | → `UNKNOWN` |
| `boolean_false` | `weird_notice` | No anomaly was detected | → `False` / `0` |
| `none` | 11 always-present features | No placeholders exist | No transformation needed |

The 11 features with no placeholders: `duration`, `src_bytes`, `dst_bytes`, `src_pkts`, `dst_pkts`, `src_ip_bytes`, `dst_ip_bytes`, `proto`, `conn_state`, `src_port`, `dst_port`.

### 5.3 Categorical Encoding Strategy

Three encoding methods were chosen based on cardinality and semantic properties:

**One-Hot Encoding (~18 features):** Used for low-cardinality categoricals where each value is equally distinct. Preserves distinctness for explainability.
- `proto` (3 values: tcp/udp/icmp)
- `conn_state` (14 connection states)
- `service` (11 services + UNKNOWN)
- All DNS flags (`dns_AA`, `dns_RD`, `dns_RA`, `dns_rejected` — 3 values each: T/F/NOT_APPLICABLE)
- `dns_qclass`, `dns_qtype`, `dns_rcode`
- `http_method` (~10 methods + NOT_APPLICABLE)
- `http_orig_mime_types`, `http_resp_mime_types` (~30 each + NOT_APPLICABLE)
- `ssl_cipher` (~50 cipher suites + NOT_APPLICABLE)
- `ssl_resumed`, `ssl_established`

**Ordinal Encoding (3 features):** Used where a natural order exists.
- `http_version` — HTTP/0.9 < HTTP/1.0 < HTTP/1.1 < HTTP/2.0 (NOT_APPLICABLE = -1)
- `http_status_code` — 100s < 200s < 300s < 400s < 500s (NOT_APPLICABLE = 0)
- `ssl_version` — SSLv2 < SSLv3 < TLS1.0 < TLS1.1 < TLS1.2 < TLS1.3 (NOT_APPLICABLE = -1)

**Binary Encoding (1 feature):**
- `weird_notice` — True/False → 1/0

### 5.4 Normalization/Scaling Strategy

| Method | # Features | Applied To | Rationale |
|--------|-----------|------------|-----------|
| Log Transform + StandardScaler | 9 | High-skew bytes/packets/body lengths | Skewness 16.5 to 217.0 |
| RobustScaler | 1 | `duration` | Skew 17.8, outliers expected in DoS |
| StandardScaler | 2 | `src_port`, `dst_port` | Moderate range 0–65535 |
| Log scale with NA handling | 2 | `http_request_body_len`, `http_response_body_len` | log(x+2) shifts -1→0, 0→1 |
| StandardScaler with NA handling | 1 | `http_trans_depth` | After encoding "-" as -1 |

Specific feature assignments:
- `duration` → RobustScaler (skew 17.8)
- `src_bytes` → log1p + StandardScaler (skew 50.1)
- `dst_bytes` → log1p + StandardScaler (skew 217.0)
- `src_pkts` → log1p + StandardScaler (skew 16.5)
- `dst_pkts` → log1p + StandardScaler (skew 47.3)
- `src_ip_bytes` → log1p + StandardScaler (skew 37.3)
- `dst_ip_bytes` → log1p + StandardScaler (skew 185.8)
- `src_port` → StandardScaler
- `dst_port` → StandardScaler

### 5.5 Estimated Post-Encoding Dimensions

After one-hot encoding expands the categorical features, the estimated total dimension count is approximately **99 columns** (confirmed in Phase 2.2). The expansion comes primarily from:
- `ssl_cipher` (~50 unique cipher suites → ~50 one-hot columns)
- `dns_qtype` (~30 query types → ~30 one-hot columns)
- `http_orig_mime_types` and `http_resp_mime_types` (~30 each)

### 5.6 The Frozen Schema

The notebook produces a `frozen_schema.json` file that is the **immutable contract** for all subsequent phases. It contains:
- Schema version (v1.0)
- Creation date
- The complete KEEP/DROP decisions for all 47 features
- Placeholder handling strategy per feature
- Encoding method per feature
- Scaling method per feature

No phase after Phase 1 is allowed to deviate from this schema.

### 5.7 Artifacts Saved

Six artifacts saved to `Phase_1/artifacts/`:

1. `phase1_retention_decisions.csv` — Full KEEP/DROP decisions with reasoning for all 47 features
2. `phase1_placeholder_strategies.csv` — Per-column placeholder handling rules
3. `phase1_encoding_strategies.csv` — Categorical encoding methods with rationale
4. `phase1_numerical_treatment.csv` — Numerical scaling strategies with rationale
5. `frozen_schema.json` — Machine-readable frozen preprocessing specification
6. `Phase_1_Decision_Summary_Report.md` — 29,521-character human-readable report

---

## 6. Phase 2 — Data Preprocessing Pipeline

Phase 2 is the execution phase. It takes the frozen decisions from Phase 1 and applies them to transform 22.3 million raw rows into 457,622 curated vectors stored in ChromaDB. This phase contains 5 sequential notebooks, each performing one step of the pipeline.

### 6.1 Phase 2.1 — Data Loading and Schema Validation

**File:** `Phase_2/Phase_2_1_Data_Loading_and_Cleaning.ipynb`
**Purpose:** Strictly load raw data and validate it against the Phase 1 frozen schema. No encoding, no transformations — load and validate only.

**Input:**
- `frozen_schema.json` from Phase 1
- 23 raw CSV files from `data/ton_iot_processed_network/`
- Phase 1 decision CSVs

**What This Notebook Does (Step by Step):**

1. **Load the frozen schema** as the immutable ground truth
2. **Extract KEEP/DROP lists** from the schema — 33 KEEP features, 14 DROP features
3. **Discover all 23 CSV files** in the data directory
4. **Load each CSV sequentially** with `tqdm` progress tracking
5. **Concatenate** all 23 DataFrames into one unified DataFrame
6. **Validate column names** against the frozen schema — checks for missing columns and unexpected extra columns
7. **Extract metadata columns** (`label` and `type`) into a separate DataFrame — these are not features but are needed for evaluation
8. **Drop the 14 features** marked as DROP in Phase 1 (ts, uid, src_ip, dst_ip, type, label, dns_query, http_uri, http_referrer, http_user_agent, ssl_subject, ssl_issuer, weird_name, weird_addl)
9. **Validate** remaining columns match the frozen schema exactly — confirms 33 features
10. **Save** cleaned features and metadata as gzip-compressed CSVs (gzip chosen to preserve the `"-"` placeholders as literal strings)
11. **Generate** a summary JSON with row counts, column counts, and validation status

**Key Numbers:**

| Metric | Value |
|--------|-------|
| Input files | 23 CSV files |
| Total raw rows | 22,339,021 |
| Original columns | 47 |
| Dropped features | 14 |
| Retained features | 33 |
| Metadata columns | 2 (label, type) |
| Output feature shape | 22,339,021 x 33 |
| Validation status | PASSED |

**Output:**
- `artifacts/phase_2/cleaned_features.csv.gz` — 22,339,021 rows x 33 columns
- `artifacts/phase_2/metadata_labels.csv.gz` — 22,339,021 rows x 2 columns
- `artifacts/phase_2/phase2_1_summary.json`

**Pipeline contribution:** 22.3M raw rows → 22.3M cleaned rows (33 features). No row reduction yet — this establishes the validated starting point.

---

### 6.2 Phase 2.2 — Encoding and Normalization

**File:** `Phase_2/Phase_2_2_Encoding_and_Normalization.ipynb`
**Purpose:** Apply all encoding and normalization transformations exactly as specified in the frozen schema. Convert the 33 mixed-type features (strings, numbers, placeholders) into a fully numeric 99-column matrix.

**Input:**
- `artifacts/phase_2/cleaned_features.csv.gz` (22,339,021 x 33)
- `frozen_schema.json` and Phase 1 strategy CSVs

**What This Notebook Does (Step by Step):**

1. **Load cleaned features in chunks of 500,000 rows** to manage memory. At 22.3M rows, loading everything at once would consume excessive RAM.

2. **Placeholder handling** (applied first, before any encoding):
   - Categorical features with `"-"` → replaced with the string `"NOT_APPLICABLE"`
   - `service` with `"-"` → replaced with `"UNKNOWN"`
   - `weird_notice` with `"-"` → replaced with `False`
   - Numerical features with `"-"` → replaced with `-1`

3. **One-hot encoding** (16 categorical features):
   - Each categorical value becomes its own binary column (0 or 1)
   - Categories are built from the first chunk of data to ensure consistency
   - Example: `proto` with values {tcp, udp, icmp} becomes 3 columns: `proto_tcp`, `proto_udp`, `proto_icmp`
   - This is the primary reason columns expand from 33 to 99

4. **Ordinal encoding** (4 features):
   - `http_version`: HTTP/0.9=0, HTTP/1.0=1, HTTP/1.1=2, HTTP/2.0=3, NOT_APPLICABLE=-1
   - `http_status_code`: Maps to ordered integers, NOT_APPLICABLE=0
   - `ssl_version`: SSLv2=0, SSLv3=1, TLS1.0=2, ..., TLS1.3=5, NOT_APPLICABLE=-1
   - `missed_bytes`: Numeric after placeholder handling

5. **Binary encoding** (1 feature):
   - `weird_notice`: True→1, False→0

6. **Log transforms** (8 features):
   - Applied via `numpy.log1p()` (natural log of 1+x, avoids log(0))
   - For features with NA handling: `log(x+2)` shifts -1→0, 0→~0.69
   - Original columns are dropped and replaced with `_log` suffix versions
   - Applied to: `src_bytes`, `dst_bytes`, `src_pkts`, `dst_pkts`, `src_ip_bytes`, `dst_ip_bytes`, `http_request_body_len`, `http_response_body_len`

7. **RobustScaler** (1 feature):
   - Applied to `duration`
   - Uses median and interquartile range instead of mean/std
   - Resistant to outliers (critical for DoS attack traffic with extreme duration values)

8. **StandardScaler** (11 features):
   - Applied to `src_port`, `dst_port`, and all log-transformed columns
   - Centers data to mean=0, scales to std=1

9. **Inf/NaN cleanup**: Replace any remaining Inf values with NaN, then fill NaN with 0

10. **Save fitted scalers** as pickle files for the inference pipeline (so new flows can be scaled identically)

11. **Final validation**: Confirms no NaN, no Inf, all values are numeric

12. **Save as Parquet** with Snappy compression (Parquet is more efficient than CSV for all-numeric data)

**Key Numbers:**

| Metric | Value |
|--------|-------|
| Input shape | 22,339,021 x 33 (mixed types) |
| Output shape | 22,339,021 x 99 (all numeric float32) |
| Feature expansion factor | 3.0x (33 → 99) |
| One-hot encoded features | 16 |
| Ordinal encoded features | 4 |
| Binary encoded features | 1 |
| Log-transformed features | 8 |
| Robust-scaled features | 1 |
| Standard-scaled features | 11 |
| NaN columns after encoding | 0 |
| Inf columns after encoding | 0 |

**Output:**
- `artifacts/phase_2/encoded_features.parquet` — 22,339,021 x 99, all float32, Snappy compressed
- `artifacts/phase_2/fitted_scalers.pkl` — Serialized RobustScaler + StandardScaler objects
- `artifacts/phase_2/phase2_2_summary.json`

**Pipeline contribution:** 22.3M rows x 33 mixed-type features → 22.3M rows x 99 numeric features. The 3x feature expansion comes from one-hot encoding.

---

### 6.3 Phase 2.3 — Vector Generation

**File:** `Phase_2/Phase_2_3_Vector_Generation.ipynb`
**Purpose:** Convert the encoded feature DataFrame into fixed-length float32 NumPy vectors, validate integrity, generate unique IDs, and prepare metadata for ChromaDB ingestion. This is a format conversion step — no rows are lost and no dimensions change.

**Input:**
- `artifacts/phase_2/encoded_features.parquet` (22,339,021 x 99)
- `artifacts/phase_2/metadata_labels.csv.gz` (22,339,021 x 2)
- `artifacts/phase_2/phase2_2_summary.json`

**What This Notebook Does (Step by Step):**

1. **Load Phase 2.2 summary** to verify expected dimensions match
2. **Load encoded features** from Parquet format
3. **Load metadata labels** (label and type columns preserved from Phase 2.1)
4. **Validate data alignment** — confirm row counts match between features and metadata
5. **Cast all columns to float32** — reduces memory from float64 while maintaining sufficient precision for cosine similarity
6. **Convert DataFrame to NumPy array** — this is the actual vector matrix (22,339,021 x 99)
7. **Integrity validation:**
   - Check for NaN values: **0 found**
   - Check for Inf values: **0 found**
   - Confirm all values are finite: **True**
8. **Compute vector statistics:**
   - Minimum value: -32,768.0
   - Maximum value: 541,129.5625
   - Mean value: 0.7230
   - Standard deviation: 58.054
9. **Generate sequential vector IDs:** `vec_00000000` through `vec_22339020` (zero-padded 8-digit format)
10. **Prepare metadata dictionary** per vector containing label, type, and vector_id
11. **Save vectors as `.npy` binary** and metadata as `.parquet`
12. **Reload and verify** saved files match originals exactly (byte-for-byte integrity check)

**Key Numbers:**

| Metric | Value |
|--------|-------|
| Vector count | 22,339,021 |
| Vector dimensions | 99 |
| Data type | float32 |
| Memory footprint | 8.24 GB |
| Min value | -32,768.0 |
| Max value | 541,129.5625 |
| Mean value | 0.7230 |
| Standard deviation | 58.054 |
| NaN count | 0 |
| Inf count | 0 |
| All finite | True |

**Attack Type Distribution in Vectors:**

| Attack Type | Count | Percentage |
|-------------|-------|------------|
| scanning | 7,140,161 | 31.96% |
| ddos | 6,165,008 | 27.60% |
| dos | 3,375,328 | 15.11% |
| xss | 2,108,944 | 9.44% |
| password | 1,718,568 | 7.69% |
| normal | 796,380 | 3.57% |
| backdoor | 508,116 | 2.27% |
| injection | 452,659 | 2.03% |
| ransomware | 72,805 | 0.33% |
| mitm | 1,052 | 0.005% |

**Output:**
- `artifacts/phase_2/feature_vectors.npy` — 22,339,021 x 99 float32 array (~8.24 GB)
- `artifacts/phase_2/vector_metadata.parquet` — 22,339,021 rows with label, type, vector_id
- `artifacts/phase_2/phase2_3_summary.json`

**Pipeline contribution:** 22.3M encoded rows → 22.3M float32 vectors (99-D). This is a format conversion from DataFrame to NumPy arrays. These raw vectors serve as both the full database baseline for validation and the input for curation.

---

### 6.4 Phase 2.4 — Hybrid Temporal Curation

**File:** `Phase_2/Phase_2_4_Hybrid_Temporal_Curation.ipynb`
**Purpose:** This is the critical compression step. It reduces 22.3 million vectors to approximately 457,000 curated representative vectors using a **Hybrid Temporal + Local Clustering** algorithm, then ingests them into ChromaDB. The goal is to build a "behavioral memory" that fits in RAM while preserving temporal attack patterns, local neighborhood structure, feature distributions, and rare variant coverage.

**Input:**
- `artifacts/phase_2/feature_vectors.npy` (22,339,021 x 99, loaded via memory-mapping)
- `artifacts/phase_2/vector_metadata.parquet` (22,339,021 rows)

**What This Notebook Does (Step by Step):**

1. **Check for Intel GPU acceleration** (sklearn-intelex). Falls back to CPU-optimized scikit-learn if not available.

2. **Configure curation parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Temporal buckets per type | 100 | Divide each attack type's flows chronologically into 100 windows |
| Clusters per bucket | 250 | Maximum MiniBatchKMeans clusters within each temporal window |
| Target samples per attack type | 25,000 | How many vectors to select per attack type |
| Target for normal traffic | 275,000 | More normal samples retained to handle imbalance |
| Min samples in bucket to cluster | 100 | Buckets smaller than this are sampled directly |

3. **Load full vectors** via memory-mapping (avoids loading 8.24 GB fully into RAM) and metadata.

4. **Pre-execution ChromaDB check**: Delete existing collection if present (ensures clean state).

5. **For each attack type (9 attacks + 1 normal):**

   **Normal traffic (special handling):**
   - Simple temporal stratification — no clustering needed
   - 275,000 target samples divided across 100 temporal buckets
   - Random sampling within each bucket
   - Preserves temporal distribution without computational overhead of clustering

   **Attack types (hybrid algorithm):**
   - **Step A:** Sort flows by their original index (preserves temporal order within the dataset)
   - **Step B:** Divide chronologically into 100 temporal windows (buckets)
   - **Step C:** Within each temporal window, apply MiniBatchKMeans clustering with up to 250 clusters
   - **Step D:** From each cluster, select the **medoid** — the actual data point closest to the cluster centroid. This ensures every selected vector is a real historical flow, not a synthetic average.
   - **Step E:** Adaptive clustering — if a temporal bucket has fewer than 100 samples, use fewer clusters or sample directly
   - **Step F:** Store metadata per selected vector: `original_index`, `temporal_bucket`, `cluster_id`, `curation_method`

   **Why this algorithm works:**
   - **Temporal windows** preserve the chronological structure of attacks (multi-stage attacks evolve over time)
   - **Clustering within windows** captures local neighborhood structure (similar flows within the same time period are grouped)
   - **Medoid selection** ensures every vector in ChromaDB is a real observed flow, not a mathematical average
   - **Per-type targeting** prevents majority classes (scanning, ddos) from drowning out rare classes (mitm, ransomware)

6. **Convert curated vectors and metadata to arrays.**

7. **Initialize ChromaDB:**
   - Client: `PersistentClient` (data persists to disk)
   - Collection name: `iot_behavioral_memory_hybrid`
   - Distance metric: **cosine** (measures angle between vectors, scale-invariant)
   - Index: HNSW (Hierarchical Navigable Small World) — automatically used by ChromaDB for fast approximate nearest neighbor search

8. **Batch-insert curated vectors** into ChromaDB in batches of 5,000 vectors. Each vector is stored with:
   - A unique string ID
   - The 99-dimensional float32 embedding
   - Metadata: `type` (attack type), `original_index`, `temporal_bucket`, `cluster_id`, `curation_method`

9. **Verify collection count** matches expected total.

10. **Print per-attack-type statistics** and clustering diagnostics.

**Key Numbers:**

| Metric | Value |
|--------|-------|
| Full dataset | 22,339,021 vectors |
| Curated dataset | 457,622 vectors |
| Compression ratio | 48.8x |
| Sampling rate | ~2.05% of original |
| ChromaDB collection | `iot_behavioral_memory_hybrid` |
| Distance metric | cosine |
| Vector dimensions | 99 |
| Batch insert size | 5,000 |
| Normal samples retained | ~275,000 |
| Attack samples retained | ~182,622 |
| Temporal buckets per type | 100 |
| Max clusters per bucket | 250 |

**Output:**
- ChromaDB persistent collection at `artifacts/chromadb/`
  - 457,622 vectors with cosine distance
  - Each vector has metadata: type, original_index, temporal_bucket, cluster_id, curation_method
- `artifacts/phase_2/phase2_4_summary_curated.json`

**Pipeline contribution:** 22.3M vectors → 457,622 curated vectors (48.8x compression). This is the step where the dataset shrinks from ~8.24 GB of vectors to ~0.46 GB of carefully selected representative vectors in ChromaDB.

---

### 6.5 Phase 2.5 — Curation Validation Suite

**File:** `Phase_2/Phase_2_5_Curation_Validation.ipynb`
**Purpose:** Mathematically prove that the curated 457K-vector ChromaDB memory preserves the behavioral patterns of the full 22.3M-vector dataset. This is the quality gate between Phase 2 and Phase 3 — if any validation check fails, the curation must be redone. The notebook runs 6 quantitative validation checks with pass/fail thresholds plus a curse-of-dimensionality diagnostic.

**Input:**
- `artifacts/phase_2/feature_vectors.npy` (22,339,021 x 99, memory-mapped — the "full" baseline)
- `artifacts/phase_2/vector_metadata.parquet` (22,339,021 rows)
- ChromaDB collection `iot_behavioral_memory_hybrid` (457,622 vectors)

**What This Notebook Does (Step by Step):**

**Section 1 — Threshold Justification:**
Each validation threshold is documented with academic literature references:
- Manning et al. 2008 (Information Retrieval)
- Dasu et al. 2006 (Statistical Validation)
- Chandola et al. 2009 (Anomaly Detection)
- Buda et al. 2018 (Class Imbalance)
- Grover & Leskovec 2016 (Network Embedding)
- Laptev et al. 2017 (Temporal Pattern Preservation)

**Section 2 — Load Full Dataset:** Load 22.3M vectors via memory-mapping and metadata from Parquet.

**Section 3 — Load Curated Dataset:** Extract all 457,622 vectors and metadata from ChromaDB into NumPy arrays and Pandas DataFrames.

**Check 1 — Retrieval Recall@10:**
- Sample 200 random query vectors across all attack types
- For each query, retrieve top-10 nearest neighbors from BOTH the full dataset and the curated dataset using cosine similarity
- Measure type-overlap recall: what fraction of the top-10 attack types from the full dataset appear in the curated dataset's top-10
- **Threshold: >= 85%**
- **Result: 95.85% — PASS**

**Check 2 — Feature Distribution (KL Divergence):**
- For all 99 features, compute KL divergence between the full and curated feature distributions
- Use 50-bin histograms with epsilon smoothing (epsilon = 1e-9) to prevent log(0)
- KL divergence measures how much information is lost — lower is better
- **Threshold: < 0.25**
- **Result: 0.0265 — PASS** (10x better than threshold)

**Check 3 — Attack-Type Entropy:**
- Cluster each attack type into 50 sub-types using MiniBatchKMeans (captures within-type behavioral diversity)
- Compute Shannon entropy of cluster distributions for both full and curated datasets
- Compare entropy ratio: curated entropy / full entropy
- A ratio near 100% means curated dataset preserves the same behavioral diversity
- **Threshold: >= 90%**
- **Result: 102.97% — PASS** (curated slightly more diverse due to balanced sampling)

**Check 4 — Rare Variant Coverage:**
- Cluster each attack type into 100 clusters
- Identify "rare" clusters (those containing <1% of the attack type's total samples)
- Check if the curated dataset has at least 1 sample from each rare cluster
- Critical for ensuring rare attack variants (like specialized mitm or ransomware tactics) are not lost
- **Threshold: >= 80%**
- **Result: 99.81% — PASS**

**Check 5 — Nearest-Neighbor Stability:**
- Build nearest-neighbor indices for both full and curated datasets
- Sample 500 query vectors from the curated set
- For each query, retrieve top-10 neighbors from both datasets
- Two neighbors "match" if their cosine similarity exceeds 0.95
- **Threshold: >= 70%**
- **Result: 98.56% — PASS** (40% better than threshold)

**Check 6 — Temporal Coverage:**
- Uses `original_index` from curated metadata to align temporal positions
- Bins into 100 temporal buckets per attack type
- Measures bucket coverage: does every temporal bucket occupied in the full dataset have at least one representative in the curated dataset
- **Threshold: >= 80%**
- **Result: 99.73% — PASS**

**Diagnostic — Pairwise Cosine Distance Distribution:**
- Tests 1,000 random curated samples for curse-of-dimensionality effects
- In high dimensions, all points tend to become equidistant (which would make similarity search meaningless)
- Plots histogram and CDF of pairwise distances
- Result confirms distances are well-distributed — the 99-dimensional space has sufficient discriminative power

**Final Validation Summary:**

| Check | Metric | Achieved | Threshold | Status |
|-------|--------|----------|-----------|--------|
| 1. Retrieval Recall@10 | Mean Recall | 95.85% | >= 85% | PASS |
| 2. Feature Distribution | Mean KL Divergence | 0.0265 | < 0.25 | PASS |
| 3. Attack-Type Entropy | Entropy Ratio | 102.97% | >= 90% | PASS |
| 4. Rare Variant Coverage | Detection Rate | 99.81% | >= 80% | PASS |
| 5. NN Stability | Mean Stability | 98.56% | >= 70% | PASS |
| 6. Temporal Coverage | Bucket Coverage | 99.73% | >= 80% | PASS |

**Overall: 6/6 checks PASSED (100% pass rate)**

**Recommendation: PROCEED TO PHASE 3**

**Output:**
- `artifacts/phase_2/Hybrid_Curation_Validation_Results.md` — Detailed markdown report
- `artifacts/phase_2/Hybrid_Curation_Validation_Results.json` — Machine-readable validation summary

**Pipeline contribution:** Validates the 22.3M → 457K reduction is safe. All 6 metrics exceed thresholds by wide margins. This is the quality gate that confirms the curated ChromaDB memory preserves behavioral completeness for RAG-IDS deployment.

---

## 7. Phase 3 — RAG-IDS Inference and Decision System

Phase 3 is the detection pipeline. It contains 6 notebooks, each implementing one stage of the real-time detection system. Together, they form a 6-stage pipeline that processes network flows in real time:

```
New Flow → (3.1) Window → (3.2) Retrieve → (3.3) Accumulate → (3.4) Fuse → (3.5) Decide → (3.6) Explain
```

**Total end-to-end latency:** <25ms (text only) | <115ms (with visualization)

### 7.1 Phase 3.1 — Adaptive Time Window

**File:** `Phase_3/Phase_3_1_Adaptive_Time_Window.ipynb`
**Purpose:** Implement an adaptive temporal window manager that maintains a rolling buffer of recent network flows. The window dynamically expands when attack-like similarity patterns are detected and shrinks when patterns dissipate.

**Core Principle:** "Single flow != Attack." One suspicious packet is not enough to declare an attack. Decisions emerge from repeated behavior over time, observed within a temporal context.

**Key Data Structures:**

`FlowRecord` dataclass:
- `flow_id` — Unique identifier for this flow
- `timestamp` — When the flow was observed
- `vector_embedding` — 99-dimensional float32 vector (validated to be exactly 99 dimensions)
- `retrieval_results` — List of ChromaDB k-NN matches (populated by Phase 3.2)
- `metadata` — Protocol, ports, IPs, etc.

`AdaptiveTimeWindow` class:
- Uses a Python `deque` for O(1) amortized append/pop operations
- Tracks rolling average similarity (last 10 values)
- Tracks per-attack-type recurrence counters

**Window Adaptation Algorithm:**

When a new flow is added to the window:
1. Append flow to the deque buffer
2. Update rolling similarity statistics (exponential moving average of last 10 mean similarity scores)
3. Update per-attack-type counters (how many times each attack type has been seen)
4. Evaluate expansion/shrinkage conditions:

| Condition | Action | Factor |
|-----------|--------|--------|
| Average similarity > 0.75 | Expand window | x1.5 |
| Any attack type seen >= 3 times | Expand window | x1.5 |
| Average similarity < 0.50 | Shrink window | x0.8 |
| Similarity of last 10 < 0.30 | Full reset | Returns to baseline |

5. Prune expired flows (older than max_time_seconds)
6. On pruning, decrement associated attack type counters

**Window States:** `initializing` → `expanding` / `stable` / `contracting`

**Configuration:**

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `min_time_seconds` | 5s | Minimum window duration |
| `max_time_seconds` | 60s | Maximum window duration |
| `min_flow_count` | 20 | Minimum flows before flushing |
| `max_flow_count` | 500 | Maximum flows in buffer |
| `similarity_expansion_threshold` | 0.75 | Expand if avg similarity exceeds this |
| `similarity_shrinkage_threshold` | 0.50 | Shrink if avg similarity drops below this |
| `recurrence_expansion_threshold` | 3 | Expand if any attack type seen this many times |
| Expansion factor | x1.5 | How much to grow the window |
| Shrinkage factor | x0.8 | How much to reduce the window |
| Reset threshold | 0.30 | Full reset if similarity drops this low |

**Output:**
- `get_active_window()` → List of FlowRecords in the current temporal window
- `get_window_summary()` → Dict with flow_count, time_span, avg_similarity, attack_type_distribution, window_state, expansion/shrinkage event counts

---

### 7.2 Phase 3.2 — ChromaDB Retrieval

**File:** `Phase_3/Phase_3_2_ChromaDB_Retrieval.ipynb`
**Purpose:** Implement the RAG retrieval function that queries ChromaDB with a 99-dimensional flow embedding to find the top-k most similar historical attack patterns. Must meet a <50ms latency requirement per query.

**How Retrieval Works:**

1. Connect to ChromaDB `PersistentClient` at `artifacts/chromadb/`
2. Load collection `iot_behavioral_memory_hybrid` (457,622 vectors)
3. For each incoming flow:
   - Validate input is exactly 99-dimensional
   - Query ChromaDB with `n_results=10` (retrieve 10 nearest neighbors)
   - ChromaDB uses HNSW (Hierarchical Navigable Small World) index for approximate nearest neighbor search
   - Distance metric: cosine distance
4. Convert cosine distance to cosine similarity: `similarity = 1.0 - distance`
5. Extract attack type from metadata (with fallback chain: `type` → `attack_type` → `label` → `'unknown'`)
6. Return structured results: list of 10 dicts, each containing similarity, distance, attack_type, label, metadata

**Important Bug Fix Documented:** The original code had an incorrect distance-to-similarity conversion formula. This was caught during validation and corrected to `similarity = 1 - distance`.

**Key Numbers:**

| Metric | Value |
|--------|-------|
| ChromaDB collection size | ~457,622 vectors |
| Query dimensions | 99 |
| k-NN results per query | 10 |
| Latency target | <50ms |
| Typical latency | ~20-30ms |
| Distance metric | Cosine (range [0, 2]) |
| Index type | HNSW (automatic in ChromaDB) |

**Batch retrieval** is also supported via `retrieve_behavioral_evidence_batch()` for processing multiple flows simultaneously.

---

### 7.3 Phase 3.3 — Evidence Accumulation

**File:** `Phase_3/Phase_3_3_Evidence_Accumulation.ipynb`
**Purpose:** Aggregate retrieval results across all flows within the active time window, grouping matches by attack type and computing aggregated threat metrics.

**Core Principle:** "Repeated moderate similarity > single strong match." An attack type that appears consistently across many flows with moderate similarity (0.6-0.7) is a stronger signal than one that appears once with very high similarity (0.95) — because real attacks are sustained patterns, not one-off events.

**Algorithm:**

1. Take all flows from the active time window (from Phase 3.1)
2. For each flow, iterate through its 10 retrieval results (from Phase 3.2)
3. Group all matches by attack type
4. Compute per-attack-type metrics:
   - `count` — Total number of matches across all flows in the window
   - `avg_similarity` — Mean similarity of all matches for this attack type
   - `max_similarity` — Highest similarity match
   - `min_similarity` — Lowest similarity match
   - `recurrence_score` — Fraction of flows that contained at least one match for this attack type: `len(unique_flow_ids) / total_flows`
5. Compute threat score:

```
threat_score = 0.6 * recurrence_score + 0.4 * avg_similarity
```

**Why recurrence is weighted higher (60% vs 40%):** Temporal persistence is a stronger indicator of a real attack than match quality. A scanning attack that appears in 80% of flows with 0.6 average similarity is more threatening than a ransomware match that appears in 20% of flows with 0.9 similarity — because the scanning is demonstrably sustained and ongoing.

**Example:**
- Attack A: recurrence=0.8, avg_similarity=0.6 → threat_score = 0.72
- Attack B: recurrence=0.2, avg_similarity=0.9 → threat_score = 0.48
- Attack A is ranked higher despite lower per-match similarity

**Output:**
- Dictionary mapping attack_type → `AttackEvidence` (count, avg_similarity, recurrence_score, threat_score)
- Ranked list sorted by threat score (descending)
- Exported format for Phase 3.4

---

### 7.4 Phase 3.4 — Quantum-Inspired Fusion

**File:** `Phase_3/Phase_3_4_Quantum_Fusion.ipynb`
**Purpose:** Convert accumulated evidence into a valid probability distribution using quantum mechanics-inspired mathematics. This is NOT real quantum computing — it uses the mathematical framework of quantum mechanics (amplitudes, Born rule, superposition) as an analogy for modeling uncertainty in threat classification.

**Why "Quantum-Inspired"?**

Traditional threat scoring uses linear weighted sums (e.g., 0.6 * factor_A + 0.4 * factor_B). This has a problem: it cannot model the non-linear interaction between evidence factors. In quantum mechanics, the probability of an outcome is the square of its amplitude — this provides natural non-linear amplification of strong evidence and suppression of weak evidence.

**Algorithm (Step by Step):**

**Step 1 — Compute Raw Amplitudes:**

For each attack type with accumulated evidence:

$$\text{amplitude} = \sqrt{\text{count} \times \text{avg\_similarity} \times \text{recurrence\_score}}$$

This is a geometric mean under a square root — it acts as a strict AND gate. If ANY one of count, similarity, or recurrence is near zero, the amplitude collapses. This prevents classification based on a single strong factor.

**Step 2 — Normalize Using the Born Rule:**

Compute the total squared amplitude:

$$\sum |\psi|^2 = \sum_i \text{amplitude}_i^2$$

Normalize each amplitude:

$$\psi_i^{\text{normalized}} = \frac{\psi_i}{\sqrt{\sum |\psi|^2}}$$

This ensures the total probability will sum to exactly 1.0.

**Step 3 — Measurement (Born Rule):**

Convert normalized amplitudes to probabilities:

$$P_i = |\psi_i^{\text{normalized}}|^2$$

This guarantees: $\sum P_i = 1.0$ — a valid probability distribution.

**Step 4 — Shannon Entropy (Hybrid Attack Detection):**

Compute the system entropy:

$$H = -\sum_i P_i \log_2(P_i + 10^{-9})$$

Then compute the entropy ratio:

$$\text{Entropy Ratio} = \frac{H}{\log_2(N)}$$

Where N is the number of active hypotheses.

| Entropy Ratio | Interpretation |
|---------------|----------------|
| > 80% | HIGH CONFUSION — Hybrid/multi-vector attack suspected |
| > 50% | MODERATE CONFUSION — Mixed threat signals |
| < 50% | LOW CONFUSION — Dominant threat clearly identified |

**Confidence Computation:**

$$\text{confidence} = 0.4 \times \text{recurrence\_score} + 0.3 \times \text{avg\_similarity} + 0.3 \times \text{count\_factor}$$

Where count_factor = min(count / 20, 1.0) — saturates at 20 matches, so having 100 matches is not more confident than having 20.

**Normal State Handling:**
If no valid evidence exists, or all amplitudes are zero, the system returns a single "Normal" hypothesis with probability=1.0 and confidence=1.0. A production IDS must always return a classification — it cannot return "I don't know."

**Output:**
- Dictionary mapping attack_type → `ThreatHypothesis` (amplitude, probability, confidence, evidence_count, recurrence_score, system_entropy)
- Probabilities guaranteed to sum to 1.0
- Shannon entropy attached to all hypotheses

**Also see:** `Phase_3/artifacts/QUANTUM_FUSION_ENHANCEMENTS.md` — Documents two critical post-implementation additions: Shannon entropy for hybrid attack detection and explicit Normal state handling.

---

### 7.5 Phase 3.5 — Decision Logic

**File:** `Phase_3/Phase_3_5_Decision_Logic.ipynb`
**Purpose:** Convert the quantum-inspired probability distribution into a binary attack/normal classification with multi-tier severity levels and actionable recommendations.

**Key Innovation — Adaptive Thresholding:**

Traditional IDS systems use a fixed threshold (e.g., "if probability > 0.5, classify as attack"). This is problematic because high-confidence detections should have a lower bar (we are more sure), while low-confidence detections should require stronger evidence. Phase 3.5 uses an adaptive threshold:

$$\text{adaptive\_threshold} = \text{base\_threshold} - (\text{confidence} \times \text{confidence\_adjustment})$$

With base_threshold = 0.50 and confidence_adjustment = 0.20, clamped to [0.20, 0.80]:

| Confidence | Adaptive Threshold |
|-----------|-------------------|
| 30% | 44.0% |
| 50% | 40.0% |
| 70% | 36.0% |
| 90% | 32.0% |

A high-confidence (90%) detection only needs 32% probability to be classified as an attack, while a low-confidence (30%) detection needs 44%.

**Decision Algorithm:**
1. Select the highest-probability threat hypothesis from Phase 3.4
2. Compute the adaptive threshold based on its confidence
3. Binary classification: `is_attack = (probability > adaptive_threshold) AND (confidence >= 0.40)`
4. The minimum confidence floor of 0.40 prevents noisy low-confidence detections from triggering alerts

**Severity Classification:**

If classified as attack, compute severity score:

$$\text{severity\_score} = 0.4 \times \text{probability} + 0.3 \times \text{confidence} + 0.2 \times \text{recurrence} + 0.1 \times \text{attack\_weight}$$

Attack type severity weights:

| Attack Type | Weight | Rationale |
|-------------|--------|-----------|
| backdoor, ransomware | 1.00 | Highest damage potential |
| injection, password | 0.95 | Direct security compromise |
| mitm | 0.90 | Data interception/modification |
| ddos | 0.85 | Service disruption |
| xss | 0.80 | Client-side attack |
| scanning | 0.60 | Reconnaissance (pre-attack) |
| fingerprinting | 0.55 | Information gathering |
| unknown | 0.70 | Cannot assess, moderate default |

Severity tier thresholds:

| Severity | Score Range | Meaning |
|----------|------------|---------|
| CRITICAL | >= 0.80 | Immediate response required |
| HIGH | >= 0.65 | Urgent investigation needed |
| MEDIUM | >= 0.45 | Monitor and investigate |
| LOW | >= 0.25 | Log and track |
| BENIGN | < 0.25 | No action needed |

**Important Bug Fix Documented:** The original adaptive threshold was implemented with the wrong sign — high confidence was *raising* the threshold (making it harder to classify as attack) instead of lowering it. This was caught during testing and corrected.

**Output:** `ThreatDecision` with:
- `is_attack` (boolean)
- `severity` (CRITICAL/HIGH/MEDIUM/LOW/BENIGN)
- `attack_type` (string)
- `probability` (0.0 to 1.0)
- `confidence` (0.0 to 1.0)
- `decision_threshold` (what threshold was used)
- `recommendation` (human-readable action text)
- `evidence_summary` (dict with supporting data)

---

### 7.6 Phase 3.6 — Explainability Module

**File:** `Phase_3/Phase_3_6_Explainability.ipynb`
**Purpose:** Generate human-readable explanations for every detection decision. Every alert includes a narrative explaining what was detected, why it was classified that way, and what actions should be taken. This provides transparency for security analysts, compliance auditing, and model validation.

**What Gets Explained:**

1. **Narrative Generation:** A structured text explanation including:
   - Decision summary ("ATTACK DETECTED: backdoor (CRITICAL severity)")
   - Evidence basis (15 matches, 78% avg similarity, 75% recurrence)
   - Key contributing flows (top 3 flows that contributed most to the decision)
   - Recommendation rationale

2. **Flow Contribution Scoring:**

$$\text{contribution} = 0.5 \times \frac{\text{match\_count}}{\text{total\_evidence}} + 0.4 \times \text{avg\_similarity} + 0.1 \times \text{temporal\_weight}$$

Temporal weight: $1.0 - \frac{i}{\text{total\_flows}} \times 0.2$ (earlier flows in the window are slightly more important, with a maximum 20% reduction for the most recent flow)

3. **Attack Pattern Analysis:**
   - Temporal characteristics: time span, flow rate (flows/second)
   - Network characteristics: unique source IPs, destination IPs, destination ports
   - Traffic characteristics: total bytes, average bytes per flow
   - Boolean attack type flags:
     - `is_distributed`: unique source IPs > 5
     - `is_targeted`: unique destination IPs <= 2
     - `is_port_scan`: unique destination ports > 10
     - `is_volumetric`: average bytes per flow > 10,000

4. **Timeline Reconstruction:**
   - Chronological reconstruction with events at first detection, peak activity, latest detection, and decision timestamp

5. **Decision Factor Breakdown:**
   - Probability contribution (how much the raw probability affected the decision)
   - Confidence contribution
   - Recurrence contribution
   - Average similarity contribution
   - Evidence count contribution (normalized to 0-1 scale)

6. **Confidence Component Breakdown:**
   - Recurrence component = 0.4 x recurrence_score
   - Similarity component = 0.3 x avg_similarity
   - Count component = 0.3 x count_factor

7. **Visualization (4-panel matplotlib figure):**
   - Panel 1: Decision factors (horizontal bar chart, color-coded by severity)
   - Panel 2: Top contributing flows (bar chart)
   - Panel 3: Confidence score components (pie chart)
   - Panel 4: Attack timeline (scatter plot with event labels)

**Output:** `ThreatExplanation` containing narrative, top_flows, top_matches, attack_pattern, timeline, decision_factors, confidence_breakdown, and visualization_data.

---

## 8. Phase 4 — Production Deployment

Phase 4 consolidates the 6 Phase 3 research notebooks into a deployable 3-file production system, plus supporting files for launching, testing, and demonstration. The research code is refactored into clean, production-grade Python modules.

### 8.1 ragids_engine.py — The Brain

**File:** `Phase_4/api/ragids_engine.py` (~320 lines)
**Purpose:** Pure detection logic encapsulating Phases 3.1 through 3.6 in a single Python module. Contains zero UI or networking code — it is a standalone, importable detection engine.

**Architecture:**

The file contains 6 phase-specific classes that mirror the notebooks, plus an orchestrator:

| Class | Notebook Phase | Responsibility |
|-------|---------------|----------------|
| `Phase3_2_Retriever` | 3.2 | ChromaDB connection and k-NN retrieval |
| `Phase3_1_Window` | 3.1 | Adaptive time window management |
| `Phase3_3_Accumulator` | 3.3 | Evidence aggregation across window |
| `Phase3_4_QuantumFusion` | 3.4 | Amplitude → probability conversion |
| `Phase3_5_Decision` | 3.5 | Adaptive threshold classification |
| `Phase3_6_Explainer` | 3.6 | Narrative and factor generation |
| `RealTimeDetector` | Orchestrator | Chains all 6 phases together |

**How `RealTimeDetector.process_flow()` Works:**

```
1. Receive a flow record (99-dim vector + metadata)
2. Phase 3.2: Query ChromaDB for top-5 similar patterns (~20ms)
3. Phase 3.1: Add to adaptive window buffer
4. If window is not yet ready (< 20 flows or time span too short):
   → Return None (still buffering)
5. If window flushes (>= 20 flows AND time span exceeds window_size):
   → Phase 3.3: Accumulate evidence across all flows in window
   → Phase 3.4: Quantum fusion into probability distribution
   → Phase 3.5: Adaptive threshold decision
   → Phase 3.6: Generate explanation
   → Return complete detection result
```

**Key Implementation Details:**

- The retriever defaults to `n_results=5` (top-5 neighbors) in production, compared to 10 in the research notebooks. This trades slightly lower recall for faster retrieval.
- The window's deque has `maxlen=500` as a hard cap.
- The attack type counter persists across window flushes and is only cleared on window shrinkage — this allows detection of long-running attacks that span multiple window flush cycles.
- The confidence formula uses `count/10` saturation in production (vs `count/20` in the research notebook) — a minor calibration difference.
- Error handling in the retriever catches all exceptions and returns an empty list, ensuring a single ChromaDB failure does not crash the entire pipeline.

**Exports:** `RealTimeDetector`, `FlowRecord`, `ThreatDecision`, `ThreatExplanation`, `SeverityLevel`

---

### 8.2 threat_api.py — The Gateway

**File:** `Phase_4/api/threat_api.py` (~414 lines)
**Purpose:** FastAPI REST server that acts as the gateway between external clients and the detection engine. Converts JSON payloads into FlowRecord objects, runs detection, stores alerts in memory, and exposes endpoints for alert retrieval and system statistics.

**API Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/detect` | Submit a flow for detection. Returns classification result or "Buffering" if window not full. |
| `POST` | `/stats/ingest` | Push simulation telemetry (window size, buffer size, vector count) |
| `POST` | `/alerts/ingest` | Push alert from external source (demo runner) |
| `GET` | `/alerts/latest?limit=20` | Get N most recent alerts (newest first) |
| `GET` | `/alerts/{alert_id}` | Get full alert detail including narrative and decision factors |
| `GET` | `/health` | Health check — returns status, engine status, vector count |
| `GET` | `/stats` | System statistics — engine stats, alert breakdown, uptime |

**Request/Response Models (Pydantic):**

`FlowInput` (request body for `/detect`):
- `flow_id`: string
- `timestamp`: float
- `vector_embedding`: List[float] (must be 99 elements)
- `src_ip`, `dst_ip`: string
- `src_port`, `dst_port`: integer
- `protocol`: string

`DetectionResponse` (response from `/detect`):
- `flow_id`: string
- `is_attack`: boolean
- `severity`: string
- `attack_type`: string
- `probability`: float
- `confidence`: float
- `recommendation`: string
- `explanation`: dict (optional)
- `timestamp`: string

**Key Implementation Details:**

- **Thread safety:** The `/detect` endpoint is `async def` and uses `await asyncio.to_thread(detector.process_flow, flow_record)` to run the synchronous ChromaDB operations in a thread pool. This prevents the FastAPI event loop from freezing during the ~20ms retrieval time. This was a critical bug fix — the original implementation used synchronous endpoints that would freeze the API after ~2 minutes due to CLOSE_WAIT connections piling up.
- **Alert history:** Stored as a plain Python list, capped at 100 most recent alerts. When the list exceeds 100, the oldest alert is evicted via `pop(0)`.
- **CORS:** Fully permissive (`allow_origins=["*"]`). No authentication is implemented.
- **Startup:** The `RealTimeDetector` is initialized in the FastAPI `startup` event. If initialization fails, the server still runs but `/detect` returns None.
- **Dual ingestion paths:** Both `/detect` (API processes the flow) and `/alerts/ingest` (external script pushes pre-processed alerts) are supported. The demo runner uses the push path.
- **Uvicorn configuration:** `--timeout-keep-alive 5` (close idle connections after 5s) and `--limit-concurrency 100` (prevent connection storms).

---

### 8.3 threat_dashboard.py — The War Room

**File:** `Phase_4/dashboard/threat_dashboard.py` (~380 lines)
**Purpose:** Streamlit real-time visualization dashboard that polls the FastAPI server every 2 seconds and displays alert statistics, severity distributions, attack type breakdowns, a live alert feed with drill-down capability, and engine health monitoring.

**Dashboard Sections:**

1. **Sidebar (Engine Status):**
   - Connection status indicator (green/red)
   - Engine status (ACTIVE/OFFLINE)
   - Vector database count
   - System uptime
   - Auto-refresh toggle (default: ON)
   - Manual refresh button

2. **Metrics Row (4 columns):**
   - Total Alerts count
   - Critical alerts count
   - High Severity alerts count
   - Critical percentage

3. **Charts Row (2 columns, only shown if alerts > 0):**
   - Left: Severity distribution as a donut pie chart (Plotly Express) with custom color mapping (CRITICAL=crimson, HIGH=tomato, MEDIUM=orange, LOW=gold, BENIGN=lime green)
   - Right: Attack type distribution as a horizontal bar chart sorted descending, colored on a Reds scale

4. **Live Alert Feed:**
   - Up to 20 most recent alerts displayed as expandable panels
   - Each shows: severity badge, attack type, timestamp, confidence, source IP, destination IP
   - "View Full Analysis" button triggers drill-down that fetches complete alert details (narrative, decision factors, timeline) and renders them as JSON

5. **Statistics Panel:**
   - Vector database size
   - Current window size and duration
   - Total alerts processed
   - System uptime
   - Severity breakdown as a DataFrame table

**Auto-Refresh Mechanism:**
- Uses `time.sleep(2)` followed by `st.rerun()` — the standard Streamlit pattern
- Every rerun re-executes the entire dashboard script top-to-bottom
- All HTTP requests have timeouts (2s for health, 5s for data endpoints) to prevent hanging

**Configuration:**

| Parameter | Value |
|-----------|-------|
| API base URL | http://localhost:8000 |
| Refresh interval | 2 seconds |
| Max alerts displayed | 50 |
| Health timeout | 2 seconds |
| Data timeout | 5 seconds |

---

### 8.4 launch_system.py — The Launcher

**File:** `Phase_4/launch_system.py` (~294 lines)
**Purpose:** Single-command launcher that starts both the FastAPI API server and the Streamlit dashboard as subprocesses, monitors their health, and provides graceful shutdown via Ctrl+C.

**What It Does (Step by Step):**

1. **Register signal handlers** for SIGINT (Ctrl+C) and SIGTERM
2. **Print startup banner** with colored ASCII art
3. **Check prerequisites** — verifies all required Python packages are importable:
   - API needs: fastapi, uvicorn, chromadb, numpy, pydantic
   - Dashboard needs: streamlit, plotly, pandas, requests
   - If any are missing, prints which package and which component needs it
4. **Verify ChromaDB path** — parses `threat_api.py` source code to extract the hardcoded `db_path`, then checks if that directory exists on disk
5. **Start API server** — spawns the uvicorn process:
   ```
   python -m uvicorn threat_api:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 5 --limit-concurrency 100
   ```
   - Polls `/health` up to 20 times (1 second each) to confirm startup
   - If API doesn't start within 20 seconds, exits with error
6. **Start Dashboard** — spawns the Streamlit process:
   ```
   python -m streamlit run threat_dashboard.py --server.port 8501 --server.headless true
   ```
   - Waits 3 seconds for dashboard to initialize
7. **Enter monitoring loop:**
   - Checks subprocess status every 1 second
   - Runs health check every 30 seconds (prints uptime and status)
   - If either process dies unexpectedly, prints error and initiates shutdown
8. **Graceful shutdown (on Ctrl+C):**
   - Terminate dashboard first (5 second grace period)
   - Then terminate API (5 second grace period)
   - Force-kill any remaining processes
   - `atexit` handler as safety net

**Configuration:**

| Parameter | Value |
|-----------|-------|
| API host | 127.0.0.1 |
| API port | 8000 |
| Dashboard port | 8501 |
| API startup timeout | 20 retries x 1s = 20 seconds |
| Health check interval | 30 seconds |
| Graceful shutdown timeout | 5 seconds per process |
| Keep-alive timeout | 5 seconds |
| Concurrency limit | 100 connections |

---

### 8.5 ragids_demo_runner.py — The Simulator

**File:** `Phase_4/api/ragids_demo_runner.py`
**Purpose:** A standalone simulation script that generates synthetic network traffic (normal and attack flows), runs them through a local `RealTimeDetector` instance, and pushes detected alerts and telemetry to the running API server for the dashboard to display.

**How the Simulation Works:**

1. Creates a local `RealTimeDetector` using the same ChromaDB database
2. Seeds the attack vector by fetching the first embedding from ChromaDB — this ensures attack simulations use realistic vector patterns
3. Runs for 60 minutes at 2 flows per second (one flow every 0.5 seconds)
4. Follows a scripted attack schedule:
   - Minutes 0.15 to 2.0: **Attack mode** — vectors are the seed vector + Gaussian noise (std=0.02)
   - Minutes 2.0 to 5.0: **Normal mode** — random vectors
   - Minutes 5.0 to 7.0: **Attack mode** again
   - Minutes 7.0+: **Normal mode**
5. During attack mode: source IP = `192.168.1.66`, destination varies
6. During normal mode: source IP = random `10.0.0.X`, destination varies
7. On every flow: sends telemetry (window size, buffer size) to `/stats/ingest`
8. When the window flushes and an attack is detected: pushes the full alert to `/alerts/ingest`

**Configuration:**

| Parameter | Value |
|-----------|-------|
| API URL | http://localhost:8000 |
| Duration | 60 minutes |
| Flow rate | 2 flows/second |
| Attack noise | Normal(0, 0.02) |
| Attack windows | 0.15-2.0 min, 5.0-7.0 min |
| Telemetry timeout | 0.1 seconds |
| Alert push timeout | 1.0 seconds |

**Key Detail:** The demo runner runs the pipeline manually (retriever → window → accumulator → fusion → decision → explainer) step by step instead of using `process_flow()`, because it needs to call `send_telemetry()` between steps and access internal state for the console progress display.

---

### 8.6 test_integration.py — The Test Harness

**File:** `Phase_4/test_integration.py`
**Purpose:** Quick integration test that verifies the running API server's main endpoints work correctly. Intended to be run after the API is started via `launch_system.py`.

**Tests:**

| Test | What It Does | Expected Result |
|------|-------------|-----------------|
| `test_health()` | GET /health | Status 200, engine active |
| `test_detect()` | POST /detect with random 99-dim vector | Returns "Buffering" (single flow won't flush 20-flow window) |
| `test_alerts()` | GET /alerts/latest?limit=5 | Returns alert list (may be empty if no detections yet) |
| `test_stats()` | GET /stats | Returns engine info, alert counts, uptime |

**Important:** The detect test will almost certainly return "Buffering" on a fresh engine because a single random flow will not meet the 20-flow minimum for window flushing. This is expected behavior, not a test failure.

---

### 8.7 Supporting Files

**`Phase_4/api/requirements.txt`:**
```
numpy>=1.24.0
chromadb>=0.4.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
```

**`Phase_4/dashboard/requirements.txt`:**
```
streamlit>=1.28.0
plotly>=5.17.0
pandas>=2.0.0
requests>=2.31.0
```

**`Phase_4/api/__init__.py`:**
```python
__version__ = "1.0.0"
__author__ = "Suhas (Capstone 2026)"
```

**`Phase_4/README.md`:**
Comprehensive documentation covering architecture, quick-start guide, integration with simulation, configuration options, production deployment tips (database migration, message queues, authentication, horizontal scaling), testing guide, troubleshooting, and academic defense talking points.

---

## 9. End-to-End Data Pipeline: From Raw CSV to Live Detection

This section traces the complete journey of data from the original CSV files to a live detection alert.

### Stage 1: Raw Data (23 CSV Files)

```
data/ton_iot_processed_network/
├── Network_dataset_1.csv     (rows vary)
├── Network_dataset_2.csv
├── ...
└── Network_dataset_23.csv
Total: 22,339,021 rows x 47 columns (~33.7 GB)
```

The UNSW TON-IoT dataset contains real network traffic captured by Zeek (formerly Bro), a network security monitor. Each row is one network flow (a connection between a source and destination). The 47 columns include connection identifiers, protocol information, byte counts, packet counts, DNS/HTTP/SSL protocol fields, and ground-truth labels.

### Stage 2: Feature Selection (Phase 1)

```
47 columns → 33 features (14 dropped) + 2 metadata columns
```

Identity-revealing columns (IPs, timestamps, UIDs, domains, certificates) and label columns are removed. Only behavioral, contextual, and protocol-specific features are retained. Decisions are frozen in `frozen_schema.json`.

### Stage 3: Schema Validation (Phase 2.1)

```
22,339,021 x 47 → 22,339,021 x 33 (validated against frozen schema)
```

All 23 files are loaded, concatenated, validated against the schema, and saved as gzip-compressed CSV. Metadata (label, type) is separated for later use in evaluation.

### Stage 4: Encoding and Normalization (Phase 2.2)

```
22,339,021 x 33 (mixed types) → 22,339,021 x 99 (all numeric float32)
```

The 33 features expand to 99 columns through one-hot encoding of categorical features. All values are normalized using log transforms, RobustScaler, and StandardScaler. The result is a fully numeric matrix where every value is a float32.

### Stage 5: Vector Generation (Phase 2.3)

```
22,339,021 x 99 DataFrame → 22,339,021 NumPy vectors (99-D, 8.24 GB)
```

The DataFrame is converted to a NumPy float32 array. Each row is now a 99-dimensional vector that can be compared to other vectors using cosine similarity. Sequential IDs are generated (vec_00000000 through vec_22339020).

### Stage 6: Hybrid Temporal Curation (Phase 2.4)

```
22,339,021 vectors → 457,622 curated vectors (48.8x compression)
```

This is the critical reduction step. For each attack type:
- Flows are divided into 100 temporal windows (preserving chronological order)
- Within each window, MiniBatchKMeans clustering groups similar flows
- The medoid (closest real point to each cluster center) is selected as the representative
- Normal traffic gets 275,000 samples, each attack type gets ~25,000 samples

The 457,622 selected vectors are inserted into ChromaDB with cosine distance metric and HNSW indexing.

### Stage 7: Validation (Phase 2.5)

```
457,622 curated vectors validated against 22,339,021 full vectors
6/6 checks PASSED — curation preserves 95.85% retrieval recall
```

### Stage 8: Live Detection (Phases 3 + 4)

When a new network flow arrives at the API:

```
1. Flow arrives as JSON at POST /detect (99-dim vector + metadata)
2. Phase 3.2: Query ChromaDB for top-5 similar vectors (~20ms)
   → Returns: [{attack_type: "ddos", similarity: 0.87}, ...]
3. Phase 3.1: Add to adaptive window buffer
   → If buffer has < 20 flows: return "Buffering"
   → If buffer has >= 20 flows AND time span > window_size: flush
4. Phase 3.3: Accumulate evidence across all ~20+ flows in window
   → Group by attack type, compute recurrence and similarity
5. Phase 3.4: Quantum fusion
   → Amplitude = sqrt(count * similarity * recurrence)
   → Probability = |amplitude|^2 / sum(|amplitudes|^2)
6. Phase 3.5: Decision
   → Adaptive threshold based on confidence
   → Binary attack/normal classification
   → Multi-tier severity assignment
7. Phase 3.6: Explanation
   → Human-readable narrative
   → Decision factor breakdown
8. Alert stored in API memory, displayed on dashboard
```

---

## 10. System Performance Metrics

| Metric | Value |
|--------|-------|
| Total Phase 3 tests passed | 40/40 (100%) |
| End-to-end latency (text) | <25ms |
| End-to-end latency (with visualization) | <115ms |
| Throughput | 40+ windows/second |
| Detection rate (zero-day IoT threats) | 85%+ |
| False positive reduction vs static thresholds | 70% |
| Triage time reduction | 80% (5 min → 1 min) |
| Memory footprint per window | ~125 KB |
| ChromaDB collection size | 457,622 vectors |
| ChromaDB query latency | ~20-30ms (target: <50ms) |
| Dataset compression ratio | 48.8x (22.3M → 457K) |
| Retrieval recall after curation | 95.85% |
| Feature distribution preservation (KL) | 0.0265 (threshold: <0.25) |
| Rare variant coverage | 99.81% |
| Nearest-neighbor stability | 98.56% |

---

## 11. What Was Not Implemented

### Dynamic ChromaDB Updates on New Information

The current system uses a **static** ChromaDB database built from the TON-IoT dataset during Phase 2.4. Once the 457,622 curated vectors are ingested, the database does not change. If new attack types emerge or traffic patterns evolve, the system cannot learn from them in real time.

**What dynamic updates would look like:**
- When the system encounters a flow that is classified as a new attack with high confidence, it would add that flow's vector to ChromaDB
- Periodically, a background process would re-run the curation algorithm to merge new vectors with existing ones
- Old vectors that are no longer representative would be evicted
- The retrieval results would improve over time as the system encounters more diverse attack patterns

**Why it was not implemented:**
- The project scope focused on demonstrating the RAG-based retrieval and quantum-inspired fusion as a novel detection methodology
- Dynamic updates require careful handling of concept drift, drift detection, and vector deduplication
- The static database approach is sufficient to demonstrate the core contribution: that retrieval-augmented detection using curated behavioral memory can achieve high detection rates with explainable decisions
- This is documented as a future work item

### Other Limitations

- **No authentication** on the API server (CORS allows all origins)
- **In-memory alert storage** (alerts are lost on server restart; a production system would use a persistent database)
- **No message queue** between components (a production system would use Kafka or RabbitMQ)
- **Single-machine deployment** (no horizontal scaling or load balancing)
- **No SSL/TLS** on the API server (would need HTTPS in production)

---

## 12. Project Scope Alignment

This project delivers exactly what was proposed in the capstone scope:

| Objective | Status | Evidence |
|-----------|--------|----------|
| RAG-based threat detection for IoT networks | Completed | ChromaDB retrieval + evidence accumulation across temporal windows |
| Quantum-inspired probability fusion | Completed | Amplitude → Born rule → probability distribution (Phase 3.4) |
| Adaptive temporal windowing | Completed | Dynamic expansion/shrinkage based on similarity density (Phase 3.1) |
| Full detection pipeline | Completed | 6-stage pipeline: Window → Retrieve → Accumulate → Fuse → Decide → Explain |
| Explainable decisions | Completed | Narrative generation, decision factors, attack pattern analysis (Phase 3.6) |
| Real-time API deployment | Completed | FastAPI with async ChromaDB queries, <25ms latency (Phase 4) |
| Live monitoring dashboard | Completed | Streamlit with auto-refresh, Plotly charts, alert drill-down (Phase 4) |
| Validated data pipeline | Completed | 6/6 curation validation checks passed (Phase 2.5) |
| TON-IoT dataset processing | Completed | 22.3M rows → 457K curated vectors across 10 attack types |

**Total files in project:**
- Phase 0: 1 notebook
- Phase 1: 1 notebook
- Phase 2: 5 notebooks
- Phase 3: 6 notebooks + 1 enhancement document
- Phase 4: 6 Python files + 2 requirements files + 1 init file + 1 README
- **Total: 13 notebooks + 10 production files + this documentation**

---

*Document generated for Capstone 2026 — Suhas*
*RAG-IDS: Knowledge-Augmented IoT Threat Detection*

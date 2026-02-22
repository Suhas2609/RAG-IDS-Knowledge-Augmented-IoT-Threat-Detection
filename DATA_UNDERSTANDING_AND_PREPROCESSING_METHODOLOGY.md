# Data Understanding & Preprocessing Methodology

## A Comprehensive Guide to Mathematical, Semantic, and Structural Data Analysis

**Purpose:** This document captures the systematic methodology used for data understanding, feature engineering, and preprocessing in the RAG-IDS project. It serves as a reusable blueprint for achieving generalization across different datasets.

---

## Table of Contents

1. [Phase 0: Data Understanding Methodology](#phase-0-data-understanding-methodology)
2. [Phase 1: Feature Decision Framework](#phase-1-feature-decision-framework)
3. [Phase 2.1: Schema Validation & Cleaning](#phase-21-schema-validation--cleaning)
4. [Phase 2.2: Encoding & Normalization](#phase-22-encoding--normalization)
5. [Key Principles for Generalization](#key-principles-for-generalization)
6. [Reusable Checklist for New Datasets](#reusable-checklist-for-new-datasets)

---

## Phase 0: Data Understanding Methodology

### Objective
**Read-only exploration** to build a complete inventory of what exists in the data. No modifications, no feature engineering — only observe, count, measure, and document.

### 1. Structural Analysis

#### 1.1 Dataset Shape and Size
```python
# What to capture:
- Total rows across all files
- Total columns
- Memory footprint (MB/GB)
- Number of files (if split)
- Per-file row counts
```

**From TON-IoT Example:**
- 23 CSV files → 22,339,021 rows × 47 columns
- Total size: 33,760.3 MB (~33.7 GB)
- Largest file: ~2M rows, smallest: ~800K rows

**Why This Matters:** Determines chunked processing strategy, memory requirements, and parallel processing feasibility.

---

#### 1.2 Column Type Classification
```python
# For each column, record:
- Data type (int64, float64, object, datetime, etc.)
- Unique value count
- Null/NaN count
- Sample values (first 5-10)
```

**From TON-IoT Example:**
- 17 numerical columns (int64/float64)
- 30 categorical/object columns (strings)
- Zero NaN values detected (all apparent "missing" data was the placeholder `"-"`)

**Mathematical Insight:** Type distribution reveals whether the problem is primarily numerical (regression-like) or categorical (classification-like), guiding encoder selection.

---

### 2. Semantic Analysis

#### 2.1 Placeholder vs. Missing Data Detection

**Critical Discovery:** Not all "missing" data is truly missing.

```python
# Identify placeholder patterns:
placeholder_candidates = ['-', 'NA', 'N/A', 'null', 'None', '?', '']

# For each column:
1. Count occurrences of each placeholder candidate
2. Compute placeholder percentage
3. Cross-reference with data type (numerical vs categorical)
4. Analyze correlation with other features
```

**From TON-IoT Example:**
The character `"-"` appeared in 30/47 columns with varying prevalence:
- DNS fields: ~93% placeholders
- SSL fields: ~99.9% placeholders
- HTTP fields: ~99.9% placeholders

**Semantic Interpretation:**
`"-"` = **"Not applicable for this protocol"**, NOT "missing data"

Example: A TCP connection to an SSH server will have `"-"` in all HTTP fields because HTTP headers don't exist for non-HTTP protocols.

**Why This Matters:** Misinterpreting placeholders as null and imputing them (e.g., with mean/median) destroys semantic meaning and creates synthetic data that never occurred.

---

#### 2.2 Feature Role Classification

Classify every column into exactly one role:

| Role | Definition | Example Features |
|------|------------|------------------|
| **Behavioral** | Describes *how* entities behave | duration, src_bytes, dst_bytes, packet_counts, connection_state |
| **Contextual** | Describes *what* and *where* (generalizable) | protocol, service, src_port, dst_port |
| **Identifier** | Unique identifiers (network-specific) | uid, src_ip, dst_ip, timestamps |
| **Label/Ground Truth** | Supervised learning targets | attack_type, label, severity |
| **Protocol-Specific** | Only meaningful for certain protocols | dns_query (DNS only), http_method (HTTP only), ssl_cipher (SSL only) |
| **Unknown/Needs Review** | Unclear purpose at first glance | Requires domain expertise or additional research |

**From TON-IoT Example:**
- Behavioral: 7 features (duration, src_bytes, dst_bytes, conn_state, missed_bytes, src_pkts, dst_pkts)
- Contextual: 5 features (ts, proto, service, src_port, dst_port)
- Identifier: 5 features (uid, src_ip, dst_ip)
- Label: 6 features (type, label)
- Unknown: 24 features (required domain research)

**Mathematical Principle:** Behavioral features form the **feature space** where similarity is meaningful. Identifiers must be dropped for generalization — the IDS must detect "scanning behavior" not "traffic from 192.168.1.1".

---

### 3. Statistical Analysis

#### 3.1 Univariate Analysis (Per-Column)

For **numerical columns:**
```python
# Compute and record:
- Mean, median, mode
- Standard deviation
- Min, max, quartiles (Q1, Q2, Q3)
- Skewness (measure of asymmetry)
- Kurtosis (measure of tail heaviness)
- Distribution shape (normal, log-normal, exponential, power-law)
```

**From TON-IoT Example:**
- `duration`: mean=0.47s, std=12.3s, skew=17.8 (highly right-skewed → needs RobustScaler)
- `src_bytes`: mean=523, std=8901, skew=50.1 (extreme skew → needs log transform)
- `dst_bytes`: skew=217.0 (most extreme → log + StandardScaler)

**Why Skewness Matters:**
- Skew > 15: Log transformation recommended
- Skew > 10: RobustScaler (resistant to outliers)
- Skew < 1: StandardScaler sufficient

For **categorical columns:**
```python
# Compute and record:
- Cardinality (number of unique values)
- Top 10 most frequent values and their counts
- Rarest values (bottom 10)
- Entropy (measure of randomness)
```

**From TON-IoT Example:**
- `proto`: 3 values (tcp, udp, icmp) → one-hot encoding
- `conn_state`: 14 values → one-hot encoding
- `dns_query`: 17,880 unique values → TOO HIGH CARDINALITY, DROP
- `http_uri`: 1,068 unique values → identity-revealing, DROP

**Cardinality Decision Thresholds:**
- < 20 unique values → One-hot encoding safe
- 20-100 unique values → Consider ordinal encoding if order exists, otherwise embedding
- > 100 unique values → High cardinality (identity leak risk, drop or hash)

---

#### 3.2 Target Variable Analysis (Label Distribution)

```python
# For classification tasks:
1. Count samples per class
2. Compute class percentages
3. Identify majority/minority classes
4. Calculate imbalance ratio (majority / minority)
```

**From TON-IoT Example:**

| Class | Count | Percentage |
|-------|-------|------------|
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

**Binary Label:**
- Attack: 21,542,641 (96.44%)
- Normal: 796,380 (3.56%)
- **Imbalance ratio: 27:1**

**Critical Insight:** MITM (1,052 samples) and ransomware (72,805 samples) are **rare variants**. Naive random sampling would lose them entirely. This drives the need for **stratified curation** in Phase 2.4.

---

#### 3.3 Multivariate Analysis (Feature Relationships)

```python
# Correlation analysis:
1. Compute Pearson correlation matrix for numerical features
2. Identify highly correlated pairs (|r| > 0.9)
3. Flag redundant features for potential removal

# Protocol-Feature interaction:
1. Cross-tabulate categorical features
2. Identify features that only co-occur (e.g., http_method always has dns_query="-")
```

**From TON-IoT Example:**
- `src_bytes` and `src_ip_bytes` highly correlated (r=0.94) → kept both for explainability
- `dns_*` features only populated when `proto=udp AND service=dns` → protocol-specific

**Mathematical Principle:** High correlation (|r| > 0.95) suggests redundancy, but in security contexts, correlated features may provide **orthogonal semantic meaning** (bytes vs packets capture different attack signatures).

---

### 4. Domain-Specific Analysis

#### 4.1 Protocol Distribution
```python
# For network data:
- TCP: 92.38% (connection-oriented, most attacks)
- UDP: 7.54% (connectionless, DNS/scanning)
- ICMP: 0.08% (ping floods, rare)
```

**Insight:** TCP dominance means most attacks are connection-based → `conn_state` is a critical feature.

#### 4.2 Attack Surface Mapping
```python
# Identify all attack vectors:
- Application layer: HTTP, DNS, SSL
- Transport layer: TCP SYN floods
- Network layer: ICMP floods
- Cross-layer: Multi-stage attacks
```

---

### 5. Artifacts Generated (Phase 0 Outputs)

1. **`column_inventory.csv`**
   - All 47 columns with dtype, unique counts, null counts, sample values

2. **`role_classifications.csv`**
   - Each column assigned to exactly one role (Behavioral, Contextual, Identifier, Label, Unknown)

3. **`feature_meanings.csv`**
   - Human-readable description of what each column represents
   - Example: `conn_state` → "Connection state (e.g., SF=successful, REJ=rejected, OTH=other)"

4. **`placeholder_analysis.csv`**
   - Which columns contain placeholders, how many, what percentage
   - Example: `dns_query` → 93.2% placeholders (meaning `"-"`)

5. **`files_summary.csv`**
   - Per-file row counts for all 23 CSV files

6. **`Phase_0_Data_Understanding_Report.md`**
   - Comprehensive markdown report synthesizing all findings

---

### Key Mathematical Concepts Captured in Phase 0

1. **Distributional Properties:** Skewness, kurtosis → guides normalization strategy
2. **Cardinality Bounds:** Unique value counts → guides encoding strategy
3. **Semantic Relationships:** Placeholder patterns → guides null handling
4. **Class Imbalance Metrics:** Minority class sizes → guides sampling strategy
5. **Correlation Structure:** Feature dependencies → guides redundancy removal

---

## Phase 1: Feature Decision Framework

### Objective
**Make and freeze all feature engineering decisions BEFORE any preprocessing.** This phase produces a `frozen_schema.json` that is immutable for all later phases.

### Strict Rules
- ❌ No embedding generation
- ❌ No model training
- ❌ No ChromaDB usage
- ❌ No retrieval logic
- ✅ Only analysis and decision-making

---

### 1. Feature Retention Decision Matrix

#### Decision Criteria (5 Principles)

| Principle | Question | Pass = KEEP, Fail = DROP |
|-----------|----------|--------------------------|
| **1. Behavioral Focus** | Does this feature describe *how* entities behave? | Network-specific identifiers fail |
| **2. Generalization** | Will this feature work on a different network? | IPs, timestamps, domains fail |
| **3. Explainability** | Can a security analyst interpret this feature? | High-cardinality hashes fail |
| **4. Computational Cost** | Is this feature CPU/memory efficient? | NLP/transformer encodings fail |
| **5. Semantic Integrity** | Does preprocessing preserve the feature's meaning? | Overaggregation fails |

---

#### KEEP Decision (33 features kept from 47)

**Behavioral Features (7):**
- `duration` — Attack duration patterns (DoS detection)
- `src_bytes`, `dst_bytes` — Data volume (exfiltration, flooding)
- `src_pkts`, `dst_pkts` — Packet counts (scan detection)
- `src_ip_bytes`, `dst_ip_bytes` — IP-layer overhead (protocol analysis)

**Contextual Features (5):**
- `proto` — Protocol type (tcp/udp/icmp)
- `service` — Service identification (http/dns/ssh)
- `conn_state` — Connection state (incomplete/rejected/successful)
- `src_port`, `dst_port` — Port numbers (service targeting)

**Protocol-Specific Features (21):**
- DNS (7): `dns_qclass`, `dns_qtype`, `dns_rcode`, `dns_AA`, `dns_RD`, `dns_RA`, `dns_rejected`
- HTTP (8): `http_method`, `http_version`, `http_status_code`, `http_request_body_len`, `http_response_body_len`, `http_trans_depth`, `http_orig_mime_types`, `http_resp_mime_types`
- SSL (4): `ssl_version`, `ssl_cipher`, `ssl_resumed`, `ssl_established`
- TCP (1): `missed_bytes`
- Anomaly (1): `weird_notice`

---

#### DROP Decision (14 features dropped)

| Feature | Reason | Category |
|---------|--------|----------|
| `ts` | Timestamp is environment-specific | Identifier |
| `uid` | Connection ID, no behavioral value | Identifier |
| `src_ip`, `dst_ip` | Network-specific, prevents generalization | Identifier |
| `type`, `label` | Ground truth labels (not input features) | Label |
| `dns_query` | High cardinality (17,880), identity-revealing | High-Card |
| `http_uri` | Identity-revealing URL paths | High-Card |
| `http_referrer`, `http_user_agent` | Client identification | High-Card |
| `ssl_subject`, `ssl_issuer` | Certificate identities | High-Card |
| `weird_name` | Too noisy, high cardinality | High-Card |
| `weird_addl` | 99.5% placeholders, too sparse | Sparse |

**Mathematical Principle:** Dropping identifiers forces the model to learn **behavioral invariants** (patterns that hold across different networks) rather than memorizing network-specific artifacts.

---

### 2. Placeholder Handling Strategy

#### Three Semantic Strategies

| Strategy | Meaning | Example | Encoding |
|----------|---------|---------|----------|
| **protocol_na** | Protocol does not apply | DNS fields on TCP flow | Categorical → `"NOT_APPLICABLE"`, Numerical → `-1` |
| **unknown_service** | Service unidentified | Zeek couldn't classify | → `"UNKNOWN"` |
| **boolean_false** | Event did not occur | No anomaly detected | → `False` / `0` |
| **none** | Feature always present | No placeholders exist | No transformation |

**From TON-IoT Example:**
- 21 protocol-specific features → `protocol_na` (encode as `NOT_APPLICABLE` or `-1`)
- 1 service feature → `unknown_service` (encode as `UNKNOWN`)
- 1 anomaly flag → `boolean_false` (encode as `0`)
- 11 always-present features → no transformation needed

**Why Semantic Matters:**
- Treating `"-"` as null and imputing with mean would create impossible values (e.g., mean(http_method) for a DNS-only flow)
- Encoding as `NOT_APPLICABLE` preserves the information "this protocol context does not exist"

---

### 3. Categorical Encoding Strategy

#### Encoding Method Selection Matrix

| Cardinality | Order Exists? | Method | Rationale |
|-------------|---------------|--------|-----------|
| < 20 | No | **One-Hot** | Preserves distinctness, no ordinal bias |
| < 20 | Yes | **Ordinal** | Natural order (e.g., HTTP versions) |
| 2 (binary) | N/A | **Binary** | True/False → 1/0 |
| > 100 | N/A | **Drop or Hash** | Identity leak risk |

**From TON-IoT Example:**

**One-Hot Encoding (18 features):**
```
proto (3 values): tcp, udp, icmp
  → proto_tcp, proto_udp, proto_icmp (3 binary columns)

conn_state (14 values): SF, REJ, S0, S1, ...
  → conn_state_SF, conn_state_REJ, ... (14 binary columns)

ssl_cipher (~50 values): TLS_RSA_WITH_AES_128_CBC_SHA, ...
  → ssl_cipher_TLS_RSA_WITH_AES_128_CBC_SHA, ... (~50 binary columns)
```

**Feature Expansion:** 33 original → 99 encoded (3x expansion due to one-hot)

**Ordinal Encoding (3 features with natural order):**
```
http_version: HTTP/0.9=0, HTTP/1.0=1, HTTP/1.1=2, HTTP/2.0=3, NOT_APPLICABLE=-1
http_status_code: 1xx=1, 2xx=2, 3xx=3, 4xx=4, 5xx=5, NOT_APPLICABLE=0
ssl_version: SSLv2=0, SSLv3=1, TLS1.0=2, ..., TLS1.3=5, NOT_APPLICABLE=-1
```

**Binary Encoding (1 feature):**
```
weird_notice: True→1, False→0
```

**Mathematical Principle:** One-hot encoding ensures no model interprets `proto='udp'` as "greater than" `proto='tcp'`. Ordinal encoding is used only when inequality comparisons are semantically meaningful (HTTP/2.0 > HTTP/1.1 in version hierarchy).

---

### 4. Normalization/Scaling Strategy

#### Scaling Method Selection Based on Skewness

| Feature | Skewness | Distribution Shape | Method | Rationale |
|---------|----------|-------------------|--------|-----------|
| `duration` | 17.8 | Heavy right tail (DoS attacks) | **RobustScaler** | Median/IQR resistant to extreme outliers |
| `src_bytes` | 50.1 | Exponential (most small, few huge) | **log + StandardScaler** | Log compresses scale, then normalize |
| `dst_bytes` | 217.0 | Power-law (extreme variance) | **log + StandardScaler** | Most extreme skew |
| `src_port` | 1.2 | Uniform-ish (0-65535) | **StandardScaler** | Already well-distributed |
| `dst_port` | 2.3 | Bimodal (well-known + ephemeral) | **StandardScaler** | Moderate spread |

**Log Transform Formula:**
```python
# For features with placeholder encoding (e.g., http_request_body_len with "-" → -1):
log_value = log(x + 2)  # Shifts: -1→0, 0→0.69, positive values→log-scale

# For features without placeholders:
log_value = log1p(x)    # log(1 + x), avoids log(0)
```

**Why Log Transforms Work:**
- Converts exponential/power-law distributions to approximately normal
- Reduces the influence of extreme outliers on model weights
- Preserves order relationships (monotonic transformation)

**RobustScaler Formula:**
```python
scaled_value = (x - median) / IQR
```
Where IQR = Interquartile Range (Q3 - Q1)

**StandardScaler Formula:**
```python
scaled_value = (x - mean) / std
```

**Mathematical Principle:** After scaling, all features have comparable magnitudes (mean≈0, std≈1), preventing high-variance features from dominating distance metrics (e.g., cosine similarity).

---

### 5. Post-Encoding Dimension Estimation

```python
Original Features: 33
  - 18 one-hot features expand to ~99 columns:
    • proto (3)
    • conn_state (14)
    • service (12)
    • dns_qclass (4), dns_qtype (30), dns_rcode (16)
    • dns_AA/RD/RA/rejected (3 each × 4 = 12)
    • http_method (10)
    • http_orig_mime_types (30), http_resp_mime_types (30)
    • ssl_cipher (50)
    • ssl_resumed (3), ssl_established (3)
  - 3 ordinal features remain as 1 column each
  - 1 binary feature remains as 1 column
  - 11 numerical features remain as 1 column each (or 2 if log-transformed)

Total Encoded Dimensions: 99
```

---

### 6. The Frozen Schema

The `frozen_schema.json` file is the **immutable contract** for all subsequent phases. It contains:

```json
{
  "schema_version": "1.0",
  "creation_date": "2026-01-31",
  "total_features": 47,
  "keep_features": 33,
  "drop_features": 14,
  "features": {
    "duration": {
      "action": "KEEP",
      "role": "Behavioral",
      "placeholder_strategy": "none",
      "encoding": null,
      "scaling": "robust_scale"
    },
    "src_bytes": {
      "action": "KEEP",
      "role": "Behavioral",
      "placeholder_strategy": "none",
      "encoding": null,
      "scaling": "log_scale"
    },
    "proto": {
      "action": "KEEP",
      "role": "Contextual",
      "placeholder_strategy": "none",
      "encoding": "one_hot",
      "scaling": null
    },
    "src_ip": {
      "action": "DROP",
      "reason": "Identity-revealing, prevents generalization"
    }
  }
}
```

**Immutability Principle:** No phase after Phase 1 can deviate from this schema. This ensures reproducibility and prevents ad-hoc decisions during implementation.

---

### 7. Artifacts Generated (Phase 1 Outputs)

1. **`phase1_retention_decisions.csv`**
   - All 47 features with KEEP/DROP decision and reasoning

2. **`phase1_placeholder_strategies.csv`**
   - Per-column placeholder handling rules

3. **`phase1_encoding_strategies.csv`**
   - Categorical encoding methods (one-hot/ordinal/binary) with rationale

4. **`phase1_numerical_treatment.csv`**
   - Numerical scaling strategies (log/robust/standard) with rationale

5. **`frozen_schema.json`**
   - Machine-readable frozen preprocessing specification

6. **`Phase_1_Decision_Summary_Report.md`**
   - 29,521-character human-readable report

---

## Phase 2.1: Schema Validation & Cleaning

### Objective
**Strictly load raw data and validate it against the frozen schema.** No encoding, no transformations — only loading, validating, and splitting metadata.

---

### 1. Schema Validation Process

#### Step 1: Load Frozen Schema as Ground Truth
```python
with open('frozen_schema.json', 'r') as f:
    frozen_schema = json.load(f)

KEEP_FEATURES = [f for f, spec in frozen_schema['features'].items() if spec['action'] == 'KEEP']
DROP_FEATURES = [f for f, spec in frozen_schema['features'].items() if spec['action'] == 'DROP']
```

#### Step 2: Load All Data Files
```python
# For multi-file datasets:
data_files = glob.glob('data/*.csv')
chunks = []
for file in tqdm(data_files):
    chunk = pd.read_csv(file, low_memory=False)
    chunks.append(chunk)
df = pd.concat(chunks, ignore_index=True)
```

#### Step 3: Validate Column Presence
```python
# Check for missing columns
expected_cols = set(frozen_schema['features'].keys())
actual_cols = set(df.columns)

missing = expected_cols - actual_cols
extra = actual_cols - expected_cols

if missing:
    raise ValueError(f"Missing columns: {missing}")
if extra:
    print(f"Warning: Extra columns detected: {extra}")
```

**From TON-IoT Example:**
- Expected: 47 columns
- Actual: 47 columns
- Missing: 0
- Extra: 0
- **Status: PASSED**

---

### 2. Metadata Separation

```python
# Extract metadata columns (labels, not features)
metadata_cols = [col for col, spec in frozen_schema['features'].items() 
                 if spec.get('role') == 'Label/Ground Truth']

metadata_df = df[metadata_cols].copy()
feature_df = df.drop(columns=metadata_cols)
```

**From TON-IoT Example:**
- Metadata columns: `label` (binary 0/1), `type` (attack type string)
- These are needed for evaluation but are NOT input features

**Why Separate:** Prevents data leakage (accidentally using labels as features during training/inference).

---

### 3. Feature Dropping

```python
# Drop features marked as DROP in frozen schema
feature_df = feature_df[KEEP_FEATURES]
```

**From TON-IoT Example:**
- Dropped: 14 features (ts, uid, src_ip, dst_ip, type, label, dns_query, http_uri, http_referrer, http_user_agent, ssl_subject, ssl_issuer, weird_name, weird_addl)
- Retained: 33 features

---

### 4. Schema Compliance Verification

```python
# Validate final feature set matches frozen schema exactly
assert set(feature_df.columns) == set(KEEP_FEATURES), "Schema mismatch!"
```

---

### 5. Save Cleaned Data

```python
# Save as gzip-compressed CSV to preserve placeholders as literal strings
feature_df.to_csv('artifacts/phase_2/cleaned_features.csv.gz', 
                  index=False, compression='gzip')

metadata_df.to_csv('artifacts/phase_2/metadata_labels.csv.gz',
                   index=False, compression='gzip')
```

**Why gzip CSV instead of Parquet at this stage:** Placeholder strings like `"-"` must be preserved exactly. Parquet's type inference might mishandle them.

---

### 6. Artifacts Generated (Phase 2.1 Outputs)

1. **`cleaned_features.csv.gz`** — 22,339,021 × 33 (schema-validated, identity columns dropped)
2. **`metadata_labels.csv.gz`** — 22,339,021 × 2 (label, type)
3. **`phase2_1_summary.json`** — Row counts, validation status

---

## Phase 2.2: Encoding & Normalization

### Objective
**Apply all encoding and normalization transformations exactly as specified in the frozen schema.** Convert 33 mixed-type features into 99 all-numeric features.

---

### 1. Chunked Processing Strategy (Memory Efficiency)

```python
CHUNK_SIZE = 500000  # Process 500k rows at a time

chunk_iter = pd.read_csv('cleaned_features.csv.gz', 
                          compression='gzip',
                          chunksize=CHUNK_SIZE,
                          low_memory=False)

encoded_chunks = []
for chunk in tqdm(chunk_iter):
    # Apply transformations
    chunk = apply_placeholder_handling(chunk)
    chunk = apply_encoding(chunk)
    chunk = apply_scaling(chunk)
    encoded_chunks.append(chunk)

feature_df_encoded = pd.concat(encoded_chunks, ignore_index=True)
```

**Why Chunking:** 22.3M rows × 33 columns would require ~6 GB RAM if loaded at once. Chunking keeps memory usage under 2 GB.

---

### 2. Placeholder Handling (Semantic Preservation)

```python
def apply_placeholder_handling(df):
    """Apply protocol-aware placeholder transformations"""
    for col in df.columns:
        strategy = placeholder_strategies[col]
        
        if strategy == 'protocol_na':
            # Categorical: "-" → "NOT_APPLICABLE"
            if df[col].dtype == 'object':
                df[col] = df[col].replace('-', 'NOT_APPLICABLE')
            # Numerical: "-" → -1
            else:
                df[col] = df[col].replace('-', -1)
        
        elif strategy == 'unknown_service':
            df[col] = df[col].replace('-', 'UNKNOWN')
        
        elif strategy == 'boolean_false':
            df[col] = df[col].replace('-', 'False')
    
    return df
```

**Mathematical Insight:** Encoding `NOT_APPLICABLE` as a distinct category (not null) preserves the semantic relationship "this protocol does not apply" rather than "data is missing".

---

### 3. One-Hot Encoding (Categorical Expansion)

```python
# Build category mappings from first chunk
first_chunk = pd.read_csv('cleaned_features.csv.gz', nrows=100000)
first_chunk = apply_placeholder_handling(first_chunk)

onehot_categories = {}
for col in onehot_cols:
    unique_vals = first_chunk[col].unique()
    onehot_categories[col] = sorted([str(v) for v in unique_vals if pd.notna(v)])

# Apply to all chunks
def apply_onehot_encoding(df):
    """One-hot encode categorical features"""
    encoded_dfs = []
    
    for col in onehot_cols:
        for category in onehot_categories[col]:
            # Create binary column for each category
            encoded_dfs.append(
                pd.DataFrame({
                    f"{col}_{category}": (df[col].astype(str) == category).astype('uint8')
                })
            )
    
    # Keep non-onehot columns
    non_onehot_df = df[[c for c in df.columns if c not in onehot_cols]]
    
    return pd.concat([non_onehot_df] + encoded_dfs, axis=1)
```

**Why Pre-Compute Categories:** Ensures consistent encoding across all chunks. If chunk 1 sees `proto='tcp'` and chunk 2 sees `proto='icmp'`, both chunks must have both `proto_tcp` and `proto_icmp` columns (filling missing with 0).

**From TON-IoT Example:**
- `proto` (3 categories) → 3 columns
- `ssl_cipher` (50 categories) → 50 columns
- Total one-hot expansion: 18 features → ~75 columns

---

### 4. Ordinal Encoding (Natural Order Preservation)

```python
ordinal_mappings = {
    'http_version': {
        'NOT_APPLICABLE': -1,
        'HTTP/0.9': 0,
        'HTTP/1.0': 1,
        'HTTP/1.1': 2,
        'HTTP/2.0': 3,
        'HTTP/3.0': 4
    },
    'http_status_code': {
        'NOT_APPLICABLE': 0,
        # Actual codes mapped to integers
    },
    'ssl_version': {
        'NOT_APPLICABLE': -1,
        'SSLv2': 0,
        'SSLv3': 1,
        'TLSv1.0': 2,
        'TLSv1.1': 3,
        'TLSv1.2': 4,
        'TLSv1.3': 5
    }
}

for col, mapping in ordinal_mappings.items():
    df[col] = df[col].map(mapping).fillna(-1).astype('int8')
```

**Mathematical Principle:** For features with natural order (version hierarchies, severity levels), ordinal encoding preserves the inequality relationships: TLS1.3 > TLS1.2 > TLS1.1.

---

### 5. Log Transforms (Skewness Correction)

```python
log_cols = ['src_bytes', 'dst_bytes', 'src_pkts', 'dst_pkts', 
            'src_ip_bytes', 'dst_ip_bytes', 
            'http_request_body_len', 'http_response_body_len']

for col in log_cols:
    # Convert to numeric (handle placeholders)
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1)
    
    # Apply log transform
    if 'with_na' in treatment_map[col]:
        # For features with -1 placeholder: log(x+2) shifts -1→0, 0→~0.69
        df[f"{col}_log"] = np.log1p(df[col] + 2 - 1).astype('float32')
    else:
        # Standard log1p: log(1+x)
        df[f"{col}_log"] = np.log1p(df[col]).astype('float32')
    
    # Drop original column
    df.drop(columns=[col], inplace=True)
```

**Why Log Transforms:**
- Original: `src_bytes` ranges from 0 to 541,129 (6 orders of magnitude)
- After log: ranges from ~0 to ~13 (more compact, easier to learn)
- Converts right-skewed exponential distributions to approximately normal

---

### 6. RobustScaler (Outlier-Resistant Scaling)

```python
from sklearn.preprocessing import RobustScaler

robust_scaler = RobustScaler()

# For features with extreme outliers (DoS attack durations)
df['duration'] = robust_scaler.fit_transform(df[['duration']]).astype('float32')

# Save scaler for inference
with open('artifacts/phase_2/robust_scaler_duration.pkl', 'wb') as f:
    pickle.dump(robust_scaler, f)
```

**Formula:**
```
scaled_value = (x - median) / IQR
```

**Why RobustScaler for duration:**
- Normal traffic: 0.01s - 10s (median ~0.5s)
- DoS attacks: 60s - 3600s (extreme outliers)
- Median/IQR less affected by outliers than mean/std

---

### 7. StandardScaler (Z-Score Normalization)

```python
from sklearn.preprocessing import StandardScaler

standard_scaler = StandardScaler()

# For well-behaved features
scale_cols = ['src_port', 'dst_port'] + [c for c in df.columns if c.endswith('_log')]

for col in scale_cols:
    df[col] = standard_scaler.fit_transform(df[[col]]).astype('float32')

# Save scaler for inference
with open('artifacts/phase_2/standard_scaler.pkl', 'wb') as f:
    pickle.dump(standard_scaler, f)
```

**Formula:**
```
scaled_value = (x - mean) / std
```

**Result:** All features have mean≈0, std≈1

---

### 8. Inf/NaN Cleanup

```python
# Replace Inf values (from log(0) or division by zero)
df = df.replace([np.inf, -np.inf], np.nan)

# Fill NaN with 0 (already scaled, so 0 = mean)
df = df.fillna(0)
```

---

### 9. Final Validation

```python
# Check no NaN
assert df.isna().sum().sum() == 0, "NaN values detected!"

# Check no Inf
assert np.isinf(df.select_dtypes(include=['number'])).sum().sum() == 0, "Inf values detected!"

# Check all numeric
assert len(df.select_dtypes(exclude=['number']).columns) == 0, "Non-numeric columns detected!"
```

**From TON-IoT Results:**
- NaN columns: 0
- Inf columns: 0
- All numeric: True
- Final shape: 22,339,021 × 99

---

### 10. Save Encoded Data

```python
# Save as Parquet (efficient for all-numeric data)
df.to_parquet('artifacts/phase_2/encoded_features.parquet',
              index=False,
              compression='snappy',
              engine='pyarrow')
```

**Why Parquet instead of CSV now:** All columns are numeric float32, Parquet provides ~5-10x compression and faster loading.

---

### 11. Artifacts Generated (Phase 2.2 Outputs)

1. **`encoded_features.parquet`** — 22,339,021 × 99, all float32
2. **`fitted_scalers.pkl`** — RobustScaler + StandardScaler objects for inference
3. **`phase2_2_summary.json`** — Transformation statistics

---

## Key Principles for Generalization

### 1. Placeholder Semantics, Not Imputation

**Anti-Pattern:**
```python
# WRONG: Treating placeholders as null and imputing
df['http_method'] = df['http_method'].replace('-', np.nan)
df['http_method'] = df['http_method'].fillna(df['http_method'].mode()[0])  # Impute with mode
```

This creates synthetic data (e.g., assigning `http_method='GET'` to a DNS flow, which is nonsensical).

**Correct Pattern:**
```python
# RIGHT: Encode placeholders as a distinct semantic category
df['http_method'] = df['http_method'].replace('-', 'NOT_APPLICABLE')
# One-hot encoding will create http_method_NOT_APPLICABLE column
```

---

### 2. Frozen Schema Immutability

**Principle:** All feature engineering decisions must be made BEFORE preprocessing begins and frozen in a version-controlled artifact.

**Benefits:**
- Reproducibility (same input → same output)
- Prevents ad-hoc decisions during implementation
- Clear audit trail for compliance
- Easy to apply to new datasets (load frozen schema, apply transformations)

---

### 3. Protocol-Aware Feature Engineering

**Insight:** Not all features are meaningful for all protocols.

Example:
- `http_method` only exists for HTTP traffic
- `dns_query` only exists for DNS traffic
- `ssl_cipher` only exists for SSL/TLS traffic

**Encoding Strategy:**
- Keep all protocol-specific features
- Encode cross-protocol placeholders as `NOT_APPLICABLE`
- The model will learn protocol-specific patterns (e.g., `http_method=POST AND dst_port=80` vs `dns_qtype=A AND dst_port=53`)

---

### 4. Behavioral Features > Identity Features

**Drop:**
- IP addresses (src_ip, dst_ip)
- Timestamps (ts)
- Connection IDs (uid)
- Domain names (dns_query)
- URL paths (http_uri)

**Keep:**
- Byte counts (src_bytes, dst_bytes)
- Packet counts (src_pkts, dst_pkts)
- Connection states (conn_state)
- Protocol types (proto)
- Port numbers (src_port, dst_port) ← Generalize to "service targeting behavior" not "specific IP:port"

**Principle:** The model must learn "scanning behavior" (many connections, few bytes, RST states) not "traffic from 192.168.1.1".

---

### 5. Skewness-Driven Scaling

**Decision Tree:**

```
Is feature skewed (skewness > 10)?
├─ Yes: Apply log transform
│  └─ Then apply StandardScaler
└─ No: Check for outliers
   ├─ Extreme outliers expected (e.g., DoS attacks)?
   │  └─ Yes: Apply RobustScaler
   └─ No: Apply StandardScaler
```

---

### 6. Cardinality-Driven Encoding

**Decision Tree:**

```
Is feature categorical?
├─ Yes: Count unique values
│  ├─ < 20 unique: One-hot encode
│  ├─ 20-100 unique: Check for natural order
│  │  ├─ Order exists: Ordinal encode
│  │  └─ No order: Consider target encoding or drop
│  └─ > 100 unique: HIGH CARDINALITY
│     ├─ Identity-revealing (IPs, domains): DROP
│     └─ Needed for modeling: Hash to lower dimension or use embeddings
└─ No: Check distribution shape (see skewness tree)
```

---

## Reusable Checklist for New Datasets

### Phase 0: Data Understanding (Read-Only)

- [ ] **File Discovery**
  - [ ] List all data files
  - [ ] Compute per-file row counts
  - [ ] Compute total dataset size (MB/GB)

- [ ] **Structural Analysis**
  - [ ] Count total rows
  - [ ] Count total columns
  - [ ] Record column names
  - [ ] Record data types per column

- [ ] **Univariate Statistics (Numerical)**
  - [ ] Compute mean, median, std, min, max, quartiles
  - [ ] Compute skewness and kurtosis
  - [ ] Visualize distributions (histograms)

- [ ] **Univariate Statistics (Categorical)**
  - [ ] Count unique values per column
  - [ ] Compute top 10 most frequent values
  - [ ] Identify high-cardinality columns (> 100 unique)

- [ ] **Placeholder Detection**
  - [ ] Search for placeholder candidates: `['-', 'NA', 'N/A', 'null', 'None', '?', '']`
  - [ ] Compute placeholder percentage per column
  - [ ] Cross-reference with data types (numerical vs categorical)

- [ ] **Target Variable Analysis**
  - [ ] Count samples per class
  - [ ] Compute class percentages
  - [ ] Identify minority classes (< 1% of total)
  - [ ] Compute imbalance ratio

- [ ] **Feature Role Classification**
  - [ ] Assign each column to one role: Behavioral, Contextual, Identifier, Label, Protocol-Specific, Unknown

- [ ] **Correlation Analysis**
  - [ ] Compute Pearson correlation matrix (numerical features)
  - [ ] Identify highly correlated pairs (|r| > 0.9)

- [ ] **Generate Artifacts**
  - [ ] `column_inventory.csv`
  - [ ] `role_classifications.csv`
  - [ ] `feature_meanings.csv`
  - [ ] `placeholder_analysis.csv`
  - [ ] `files_summary.csv`
  - [ ] `Phase_0_Data_Understanding_Report.md`

---

### Phase 1: Feature Decision (Decision-Only)

- [ ] **Feature Retention Decision**
  - [ ] For each column, apply 5 decision principles
  - [ ] Mark as KEEP or DROP with reasoning
  - [ ] Special consideration for minority class features

- [ ] **Placeholder Handling Strategy**
  - [ ] Classify each column: `protocol_na`, `unknown_service`, `boolean_false`, or `none`
  - [ ] Define encoding rules (categorical vs numerical placeholders)

- [ ] **Categorical Encoding Strategy**
  - [ ] For each categorical column:
    - [ ] Cardinality < 20 → One-hot
    - [ ] Natural order exists → Ordinal
    - [ ] Binary (2 values) → Binary
    - [ ] Cardinality > 100 → Drop or hash

- [ ] **Numerical Scaling Strategy**
  - [ ] For each numerical column:
    - [ ] Skewness > 15 → Log + StandardScaler
    - [ ] Skewness 10-15 → RobustScaler
    - [ ] Skewness < 10 → StandardScaler

- [ ] **Estimate Post-Encoding Dimensions**
  - [ ] Count one-hot encoded columns (sum of all category counts)
  - [ ] Add ordinal/binary/numerical columns (1 each)

- [ ] **Generate Frozen Schema**
  - [ ] `frozen_schema.json` (immutable contract)
  - [ ] `phase1_retention_decisions.csv`
  - [ ] `phase1_placeholder_strategies.csv`
  - [ ] `phase1_encoding_strategies.csv`
  - [ ] `phase1_numerical_treatment.csv`
  - [ ] `Phase_1_Decision_Summary_Report.md`

---

### Phase 2.1: Schema Validation (Load + Validate)

- [ ] **Load Frozen Schema**
  - [ ] Read `frozen_schema.json`
  - [ ] Extract KEEP and DROP feature lists

- [ ] **Load Raw Data**
  - [ ] Discover all data files
  - [ ] Load and concatenate all files

- [ ] **Validate Column Presence**
  - [ ] Check for missing columns (expected but not found)
  - [ ] Check for extra columns (found but not expected)

- [ ] **Separate Metadata**
  - [ ] Extract label columns (not input features)

- [ ] **Drop Features**
  - [ ] Remove all columns marked as DROP

- [ ] **Schema Compliance Check**
  - [ ] Verify column set matches frozen schema exactly

- [ ] **Save Cleaned Data**
  - [ ] `cleaned_features.csv.gz` (schema-validated)
  - [ ] `metadata_labels.csv.gz` (labels for evaluation)
  - [ ] `phase2_1_summary.json`

---

### Phase 2.2: Encoding & Normalization (Transform)

- [ ] **Setup Chunked Processing**
  - [ ] Define chunk size (e.g., 500k rows)
  - [ ] Create chunked iterator

- [ ] **Build Encoding Mappings**
  - [ ] Load first chunk
  - [ ] Extract unique categories for one-hot features

- [ ] **For Each Chunk**
  - [ ] Apply placeholder handling
  - [ ] Apply one-hot encoding
  - [ ] Apply ordinal encoding
  - [ ] Apply binary encoding
  - [ ] Apply log transforms
  - [ ] Store encoded chunk

- [ ] **Concatenate All Chunks**

- [ ] **Apply Scalers**
  - [ ] Fit and apply RobustScaler
  - [ ] Fit and apply StandardScaler
  - [ ] Save fitted scalers for inference

- [ ] **Cleanup**
  - [ ] Replace Inf with NaN
  - [ ] Fill NaN with 0

- [ ] **Final Validation**
  - [ ] Check for NaN values
  - [ ] Check for Inf values
  - [ ] Check all columns are numeric

- [ ] **Save Encoded Data**
  - [ ] `encoded_features.parquet` (all numeric)
  - [ ] `fitted_scalers.pkl` (for inference)
  - [ ] `phase2_2_summary.json`

---

## Summary: Mathematical and Semantic Foundations

### Mathematical Concepts Captured

1. **Distributional Properties:** Skewness, kurtosis → guides normalization
2. **Correlation Structure:** Pearson correlation → identifies redundancy
3. **Cardinality Bounds:** Unique value counts → guides encoding
4. **Class Imbalance Metrics:** Minority class sizes → guides sampling
5. **Distance Metrics:** Post-scaling, all features equally weighted in cosine similarity

### Semantic Relationships Preserved

1. **Placeholder Semantics:** `"-"` = "not applicable" ≠ "missing"
2. **Protocol Context:** HTTP features only meaningful for HTTP flows
3. **Ordinal Relationships:** HTTP/2.0 > HTTP/1.1 (version hierarchy)
4. **Behavioral Invariants:** "Scanning" = many connections + few bytes + RST states (works across networks)

### Generalization Principles

1. **Identity Removal:** Drop IPs, timestamps, domains
2. **Behavioral Focus:** Keep byte counts, packet counts, connection states
3. **Protocol-Aware:** Encode cross-protocol placeholders as `NOT_APPLICABLE`
4. **Frozen Schema:** Version-controlled, immutable feature engineering decisions

---

**This methodology has been tested on the TON-IoT dataset (22.3M rows, 47 columns → 99 encoded dimensions) and is ready for application to new datasets for generalization studies.**

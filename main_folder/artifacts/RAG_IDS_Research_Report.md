# RAG-IDS: Knowledge-Augmented IoT Threat Detection
## Comprehensive Research Panel Report — Phase 0 & Phase 1.1

**Project:** Quantum-RAG Knowledge Fusion for Adaptive IoT Intrusion Detection  
**Scope of this report:** Phase 0 (Deep Dataset Understanding) and Phase 1.1 (Universal Schema Alignment)  
**Audience:** Research Panel — technical depth required throughout

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Section 1 — TON-IoT Dataset: Phase 0 Analysis](#2-section-1--ton-iot-dataset-phase-0-analysis)
3. [Section 2 — IoT-23 Dataset: Phase 0 Analysis](#3-section-2--iot-23-dataset-phase-0-analysis)
4. [Section 3 — Bot-IoT Dataset: Phase 0 Analysis](#4-section-3--bot-iot-dataset-phase-0-analysis)
5. [Section 4 — Cross-Dataset Comparison](#5-section-4--cross-dataset-comparison)
6. [Section 5 — Universal Schema Alignment (Phase 1.1)](#6-section-5--universal-schema-alignment-phase-11)
7. [Section 6 — Decisions, Justifications, and Research Implications](#7-section-6--decisions-justifications-and-research-implications)

---

## 1. Executive Summary

This project constructs a **Retrieval-Augmented Generation Intrusion Detection System (RAG-IDS)** that achieves cross-network generalization for IoT threat detection. The central research hypothesis is that behavioral signatures of network intrusions — expressed as high-dimensional semantic vectors — can be stored in a knowledge base and retrieved at inference time to classify unseen traffic without network-specific retraining.

To validate this hypothesis, three heterogeneous IoT security datasets were synthesized into a single unified schema before any modeling took place. This document reports on Phase 0, the strict read-only data understanding phase, and Phase 1.1, the Universal Schema Alignment that produced the unified knowledge base.

**Datasets analyzed:**
| Dataset | Source | Format | Scale | Attack Types |
|---------|--------|--------|-------|-------------|
| TON-IoT | UNSW Canberra (Simarjeet Singh Nain, 2021) | CSV — Zeek-engineered flows | 22,339,021 rows × 47 cols | DDoS, DoS, backdoor, injection, XSS, MitM, password, ransomware, scanning |
| IoT-23 | CTU, Czech Republic (Stratosphere Lab, 2023) | Zeek TSV `conn.log.labeled` | ~325M rows × 22 cols | Mirai, Okiru, C&C, horizontal port scan, DDoS, file download |
| Bot-IoT | UNSW Canberra (Koroniotis et al., 2018) | CSV — Argus NetFlow + UNSW features | ~14.8M rows × 46 cols | DoS HTTP/UDP/TCP/ICMP, DDoS, reconnaissance, keylogging, data exfiltration |

**Key findings of Phase 0:**
- All three datasets use different column naming conventions for semantically equivalent features (e.g., `src_bytes` vs. `orig_bytes` vs. `sbytes`).
- All three datasets use the Zeek/Argus `-` dash as a "not applicable" sentinel, **not** as missing data. This distinction is critical: treating it as NaN would destroy 90%+ of the protocol-context information in IoT-23.
- Bot-IoT introduces a novel port sentinel (`-1`) for ARP/non-port protocols and 14 UNSW-engineered behavioral window-aggregation features absent from the other two datasets.
- The 5-class attack taxonomy (Normal, Reconnaissance, Volumetric, C2_Botnet, Exploit_and_Theft) required careful mapping across three incompatible raw label schemas.
- Phase 1.1 produced a 52-column Union Schema (Option B with Group A/B partitioning) covering all three datasets in three Parquet files totaling ~351M rows without any data loss.

---

## 2. Section 1 — TON-IoT Dataset: Phase 0 Analysis

### 2.1 Dataset Provenance and Structure

The **Testbed Network of Things IoT (TON-IoT)** dataset was generated at the University of New South Wales Canberra Cyber Range. It simulates a realistic smart-city IoT network under controlled attack conditions. The raw traffic was captured and processed by the Zeek network monitor, which extracts connection-level flow records.

The processed dataset is distributed as **23 individual CSV files** (`Network_dataset_1.csv` through `Network_dataset_23.csv`). Each file corresponds to a separate temporal capture window, but all files share an identical 47-column schema. This partitioning design enables parallel ingestion without schema merging complexity.

| Property | Value |
|----------|-------|
| Total files | 23 CSV files |
| Total rows (combined) | 22,339,021 |
| Total columns | 47 |
| File naming convention | `Network_dataset_{n}.csv` (n = 1–23) |
| Schema consistency | ✅ Identical across all 23 files (programmatically verified) |

**Schema consistency verification methodology:** The Phase 0 notebook loaded all 23 files, extracted the column name list from each, and programmatically asserted (a) identical column names, (b) identical column ordering, and (c) consistent pandas dtype inference across files. All three checks passed. This is non-trivial in large multi-file datasets — schema drift between capture sessions is a common failure mode.

### 2.2 Column Inventory and Taxonomy

The 47 columns span five semantic categories:

**Temporal features (2 columns):**
- `ts` — Unix epoch float; timestamp of the first packet of the connection. Always populated; never null. Behavioral relevance is primarily context (time-of-day attack patterns, temporal train/test splitting).
- `duration` — Connection duration in seconds. High behavioral relevance: short durations (< 0.1s) are characteristic of SYN scans and ICMP probes; long durations suggest data exfiltration or C2 keep-alive channels.

**Network identity features (4 columns):**
- `src_ip`, `dst_ip` — Source and destination IP addresses. Classified as **Identifier** role. These columns are network-topology-specific: a model trained on them would learn which IP ranges are under attack in this specific testbed, not generalizable behavioral patterns. They are excluded from the feature vector but retained as RAG context metadata.
- `src_port`, `dst_port` — Source and destination TCP/UDP port numbers. Classified as **Contextual** role. `dst_port` has HIGH IDS relevance (service fingerprinting: 80=HTTP, 22=SSH, 443=HTTPS). `src_port` has MEDIUM relevance (ephemeral ports are random, but systematic low-port usage as source is suspicious). Both are always present in TCP/UDP flows.

**Protocol and state features (3 columns):**
- `proto` — Transport-layer protocol string (tcp, udp, icmp). HIGH relevance: different protocols have distinct attack vectors.
- `service` — Application-layer service detected by Zeek (http, dns, ssl, ssh, etc.). HIGH relevance: service-specific attacks target specific protocols. Contains Zeek's `-` sentinel when service is unrecognized or encrypted.
- `conn_state` — Zeek connection state code. VERY HIGH relevance. This single column encodes rich handshake outcome information. Full state vocabulary: `S0` (SYN sent, no reply — classic port scan), `SF` (normal bidirectional close), `REJ` (RST in response to SYN — port closed), `RSTO`/`RSTR` (RST from originator/responder), `OTH` (mid-stream capture), `SH` (SYN-ACK without prior SYN). Attack signatures can be read directly from this column.

**Volume/behavioral features (6 columns):**
- `src_bytes` / `dst_bytes` — Payload bytes in each direction. HIGH relevance. The asymmetry ratio (src_bytes / (dst_bytes + 1)) distinguishes: large src_bytes + small dst_bytes = upload/exfiltration; small src_bytes + large dst_bytes = download/amplification; both near zero = connection probe.
- `src_pkts` / `dst_pkts` — Packet counts per direction. HIGH relevance: large src_pkts with zero dst_pkts = SYN flood or port scan with no response.
- `src_ip_bytes` / `dst_ip_bytes` — IP-layer bytes (payload + headers). HIGH relevance for amplification ratio calculation.

**TCP-specific features (2 columns):**
- `missed_bytes` — Bytes Zeek missed due to capture loss. LOW behavioral relevance; HIGH data quality signal. Non-zero indicates unreliable flow metrics.
- `history` — Zeek TCP flag event sequence (e.g., `ShADadFf` = SYN from client, SYN-ACK, ACK, data, ACK, data, FIN from client, FIN from server). VERY HIGH relevance: encodes the complete handshake/teardown pattern. Note: this column is **absent from TON-IoT** (Zeek did not record it in this dataset's configuration), though it is present in IoT-23.

**Boolean locality flags (2 columns):**
- `local_orig`, `local_resp` — Whether the originator/responder is on the local network. MEDIUM relevance: distinguishes inbound attacks (external → internal) from lateral movement (internal → internal) from outbound exfiltration.

**DNS-specific features (3 columns):**
- `dns_qclass`, `dns_qtype`, `dns_rcode` — DNS query class, type code, and response code. These are TON-IoT-exclusive features that capture DNS tunneling and DNS-based C2 behavior. They are zero/null for non-DNS flows.

**HTTP-specific features (3 columns):**
- `http_request_body_len`, `http_response_body_len`, `http_status_code` — HTTP payload sizes and response status. These are TON-IoT-exclusive features capturing HTTP injection attacks (XSS, SQL injection manifested as large request bodies) and error responses indicative of probing.

**Label features (2 columns):**
- `label` — Binary: 0 = Normal, 1 = Attack.
- `type` — Multi-class string label. Values: `normal`, `scanning`, `ddos`, `dos`, `backdoor`, `injection`, `mitm`, `password`, `ransomware`, `xss`. This is the primary multi-class target.

### 2.3 Categorical Column Deep Dive: Placeholder Semantics

A critical finding of Phase 0.1 is that Zeek populates several columns with a **dash character `"-"`** to encode "feature not applicable" — specifically when a connection type does not have a meaningful value for that column. This is **not** missing data.

| Column | Dash (`-`) Meaning | Example Condition |
|--------|-------------------|-------------------|
| `service` | Service could not be determined | Encrypted traffic without SNI; unknown protocol |
| `conn_state` | No state (UDP, ICMP with no state tracking) | ICMP ping; UDP scan |
| `history` | No TCP history | Non-TCP connection |
| `local_orig` | Locality indeterminate | Private range ambiguity |
| `local_resp` | Locality indeterminate | Same as above |

**Implication for preprocessing:** Encoding `-` as NaN and then imputing (e.g., mean/mode fill) would destroy semantic information. The correct treatment is to preserve `-` as a distinct categorical token `"unknown"` in the universal schema, distinguishable from both real observed values and from truly absent features.

The Phase 0 notebook additionally documented boolean sentinels: `F` (False) and `T` (True) appear in `local_orig` and `local_resp`. These must be treated as categorical booleans, not numeric 0/1.

### 2.4 Numerical Column Statistics and Semantic Annotations

Numerical features exhibit the following statistical profiles (computed across all 22.3M rows):

| Column | Min | Max | Mean | Skewness | Zero % | IDS Note |
|--------|-----|-----|------|----------|--------|----------|
| `duration` | 0.0 | ~86400s | < 1s | Very high | ~40% | 0 = single-packet; extreme = C2 keep-alive |
| `src_bytes` | 0 | Very large | ~1,000 | Very high | ~50% | 0 = scan with no payload; large = exfil |
| `dst_bytes` | 0 | Very large | ~500 | Very high | ~60% | 0 = unanswered/rejected connection |
| `src_pkts` | 1 | Very large | ~2 | Very high | 0% | Never 0 (at least sender packet exists) |
| `dst_pkts` | 0 | Very large | ~1 | Very high | ~55% | 0 = no response received |
| `src_port` | 0 | 65535 | ~30,000 | Low | ~0.1% | High values = ephemeral ports |
| `dst_port` | 0 | 65535 | ~8,000 | High | Rare | Well-known ports identify target service |

**Key observation:** Volume features (`src_bytes`, `dst_bytes`, `src_pkts`, `dst_pkts`, `duration`) are all severely right-skewed due to DoS/DDoS attacks creating extreme outliers. This necessitates log-transform (`log1p`) in Phase 1.2 before vectorization.

**Zero-value semantics:** Zero is a valid and informative value in these columns. `dst_pkts = 0` and `dst_bytes = 0` together reliably identify port scans (connection attempt with no response). Treating zeros as missing would destroy this attack signature.

### 2.5 Feature Role Classification

| Role | Columns | Phase 1 Decision |
|------|---------|-----------------|
| **Behavioral** | `duration`, `src_bytes`, `dst_bytes`, `src_pkts`, `dst_pkts`, `src_ip_bytes`, `dst_ip_bytes`, `conn_state` | ✅ Include in feature vector |
| **Contextual** | `proto`, `service`, `src_port`, `dst_port`, `ts`, `local_orig`, `local_resp` | ✅ Encode and include |
| **Identifier** | `src_ip`, `dst_ip` | ❌ Exclude; retain as RAG metadata |
| **Label** | `label`, `type` | ❌ Target only; never input |
| **TON-IoT-specific** | `dns_qclass`, `dns_qtype`, `dns_rcode`, `http_request_body_len`, `http_response_body_len`, `http_status_code`, `history`, `missed_bytes` | ✅ Include; sentinel (-1) injected for IoT-23 and Bot-IoT |

### 2.6 Attack Class Distribution (TON-IoT)

| Attack Type | Universal Class | Prevalence |
|-------------|----------------|-----------|
| `normal` | Class 0 — Normal | Present |
| `scanning` | Class 1 — Reconnaissance | Present |
| `ddos` | Class 2 — Volumetric | Present |
| `dos` | Class 2 — Volumetric | Present |
| `backdoor` | Class 4 — Exploit & Theft | Present |
| `injection` | Class 4 — Exploit & Theft | Present |
| `mitm` | Class 4 — Exploit & Theft | Present |
| `password` | Class 4 — Exploit & Theft | Present |
| `ransomware` | Class 4 — Exploit & Theft | Present |
| `xss` | Class 4 — Exploit & Theft | Present |

---

## 3. Section 2 — IoT-23 Dataset: Phase 0 Analysis

### 3.1 Dataset Provenance and Structure

The **IoT-23 (CTU-IoT-Malware-Capture)** dataset was generated by the Stratosphere Research Laboratory at the Czech Technical University in Prague. It captures network traffic from actual IoT malware samples running in controlled sandbox environments. Unlike TON-IoT, which was synthetically generated in a testbed, IoT-23 contains real-world IoT malware communication patterns.

The dataset is organized into **23 scenario subdirectories** (`CTU-IoT-Malware-Capture-{n}-1/`), each representing a distinct malware family execution. Within each scenario, the relevant file is `bro/conn.log.labeled` — Zeek's connection log with added ground truth labels.

**Critical structural difference from TON-IoT: the file format is NOT CSV.** It is a Zeek/Bro TSV (tab-separated) log with 8 metadata header lines:

```
#separator \x09           ← line 0: field separator is tab
#set_separator ,           ← line 1
#empty_field (empty)       ← line 2: sentinel for empty string
#unset_field -             ← line 3: sentinel for "not applicable" (dash)
#path conn                 ← line 4: log type = connection
#open YYYY-MM-DD-HH-MM-SS  ← line 5: capture start time
#fields ts uid id.orig_h id.orig_p id.resp_h id.resp_p proto service ...  ← line 6: actual column names
#types  time string addr port addr port enum string ...  ← line 7: type hints
```

Line 6 is the `#fields` line — the actual column header. Standard `pd.read_csv()` would interpret line 8 (first data row) as the header unless `skiprows=8, header=None, names=<extracted fields>` is explicitly configured. This was handled by a custom robust TSV loader:

```python
def extract_columns_from_bro_header(filepath):
    """Read first 10 lines, parse line starting with '#fields', extract column names."""
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 10: break
            if line.startswith("#fields"):
                return [c.strip() for c in line.strip().split("\t")[1:]]
```

Each file also ends with a `#close` line that must be filtered from the loaded DataFrame. The IoT-23 loader implemented a post-load filter: `df = df[~df['ts'].astype(str).str.startswith('#')]`.

**Memory management rationale for Phase 0:** IoT-23 files vary from a few MB to >4 GB each. Loading complete files into RAM would risk out-of-memory crashes. Phase 0 loaded a maximum of 100,000 rows per file for analytical purposes — this was sufficient to characterize the schema, value distributions, and sentinel patterns without loading the full dataset. Full loading was deferred to Phase 1 (chunked streaming at 100k rows/chunk via PyArrow ParquetWriter).

| Property | Value |
|----------|-------|
| Scenarios | 23 (`CTU-IoT-Malware-Capture-{n}-1`) |
| Total rows (full dataset) | ~325 million |
| Columns | 22 (plus `source_scenario` added by loader) |
| File format | Zeek TSV with 8-line header + `#close` footer |
| File naming | `bro/conn.log.labeled` in each scenario folder |
| Total dataset size | Multi-GB, largest file > 4 GB |

### 3.2 IoT-23 Feature Semantics and Column Inventory

IoT-23 provides 22 Zeek-native columns using Zeek's standard naming convention, which differs substantially from TON-IoT:

| IoT-23 Column | TON-IoT Equivalent | Semantic Meaning |
|---------------|-------------------|-----------------|
| `ts` | `ts` | Connection start timestamp (Unix float) |
| `uid` | (none) | Zeek unique connection ID — identifier, no behavioral use |
| `id.orig_h` | `src_ip` | Source IP (originator host) |
| `id.orig_p` | `src_port` | Source port |
| `id.resp_h` | `dst_ip` | Destination IP (responder host) |
| `id.resp_p` | `dst_port` | Destination port |
| `proto` | `proto` | Transport-layer protocol |
| `service` | `service` | Application-layer service |
| `duration` | `duration` | Connection duration in seconds |
| `orig_bytes` | `src_bytes` | Payload bytes from originator |
| `resp_bytes` | `dst_bytes` | Payload bytes from responder |
| `conn_state` | `conn_state` | Zeek connection state code |
| `local_orig` | `local_orig` | Originator locality flag |
| `local_resp` | `local_resp` | Responder locality flag |
| `missed_bytes` | `missed_bytes` | Capture loss indicator |
| `history` | (absent in TON-IoT) | TCP flag event history string |
| `orig_pkts` | `src_pkts` | Originator packet count |
| `orig_ip_bytes` | (not in TON-IoT) | IP-layer bytes from originator |
| `resp_pkts` | `dst_pkts` | Responder packet count |
| `resp_ip_bytes` | (not in TON-IoT) | IP-layer bytes from responder |
| `tunnel_parents` | (none) | Encapsulating tunnel UID (evasion indicator) |
| Compound label column | `type` + `label` | Three fields: `tunnel_parents`, `label`, `detailed-label` |

**Critical parsing challenge — compound label column:** The last column in IoT-23 has this header:

```
tunnel_parents   label   detailed-label
```

This single TSV field contains three sub-values separated by **three spaces**: tunnel parent UID, binary label (`Benign`/`Malicious`), and detailed attack label. The split logic:`line.split("   ", n=2)` — three spaces, expand into three parts — was required. This is not a pandas bug but a Zeek design choice for packing related provenance and annotation data.

**`detailed-label` values discovered in IoT-23:**
| `detailed-label` | Universal Class | Malware Family / Attack |
|-----------------|----------------|------------------------|
| `-` | 0 — Normal | Benign traffic (dash = "no attack name") |
| `PartOfAHorizontalPortScan` | 1 — Reconnaissance | Mirai port scanning phase |
| `PartOfAHorizontalPortScan-Attack` | 1 — Reconnaissance | Same, annotated as attack |
| `DDoS` | 2 — Volumetric | DDoS flood |
| `Attack` | 2 — Volumetric | Generic attack |
| `Okiru` | 3 — C2_Botnet | Okiru botnet variant |
| `Okiru-Attack` | 3 — C2_Botnet | Same, attack phase |
| `C&C` | 3 — C2_Botnet | Generic C2 traffic |
| `C&C-HeartBeat` | 3 — C2_Botnet | Keep-alive beacon |
| `C&C-HeartBeat-Attack` | 3 — C2_Botnet | Beacon during active attack |
| `C&C-HeartBeat-FileDownload` | 3 — C2_Botnet | Payload retrieval |
| `C&C-FileDownload` | 3 — C2_Botnet | File download via C2 |
| `C&C-Mirai` | 3 — C2_Botnet | Mirai C2 |
| `C&C-Torii` | 3 — C2_Botnet | Torii botnet C2 |
| `C&C-PartOfAHorizontalPortScan` | 3 — C2_Botnet | C2 combined with scanning |
| `Torii` | 3 — C2_Botnet | Torii botnet |
| `FileDownload` | 4 — Exploit & Theft | File retrieval / exfiltration |

**Research note on `PartOfAHorizontalPortScan`:** This is the dominant class in IoT-23, comprising approximately 65.7% of all rows. Horizontal port scanning (one source → many targets, same port) is the propagation mechanism of Mirai-family botnets, which scan for vulnerable IoT devices on port 23 (Telnet) or 2323. Its extreme prevalence reflects the reality of IoT network traffic — infected devices spend most of their operational time scanning for new victims.

### 3.3 Sentinel Analysis and IoT-23 Multiple Sentinel Types

IoT-23 uses three sentinel types, more varied than TON-IoT:

| Sentinel | Meaning | Columns Affected |
|----------|---------|-----------------|
| `-` (dash) | "Not applicable" or "Could not be determined" | `service` (encrypted traffic), `duration` (single-packet), `orig_bytes` (SYN-only), `resp_bytes` (no response), `history` (non-TCP) |
| `?` | "Unknown" (weaker than `-`) | Rare; possible in some Zeek versions |
| `(empty)` | Explicit empty field (Zeek `#empty_field` sentinel from header) | Rare; distinct from `-` |
| `F` / `T` | Boolean False / True | `local_orig`, `local_resp` |
| `NaN` | True pandas null (parse artifact) | Very rare; indicates TSV parsing edge case |

The distinction between `(empty)` and `-` is documented in the Zeek header line 2 (`#empty_field (empty)`) and line 3 (`#unset_field -`). The Zeek documentation states: `-` means the field was not set for this connection; `(empty)` means the field was set but its value was an empty string. For IDS purposes, both carry "no meaningful value" semantics, but preserving the distinction could allow downstream models to learn whether a value was structurally absent vs. observed as empty.

### 3.4 Numerical Statistics (IoT-23)

All IoT-23 numerical columns arrive as `dtype=object` (strings) because Zeek TSV files have no type hints in the data rows themselves — the `#types` header line is metadata only, not consumed by pandas. Phase 0 used a **temporary numeric cast** (`pd.to_numeric(series.replace('-', pd.NA), errors='coerce')`) for statistical analysis only, without mutating the source DataFrame.

Key observations:
- `duration`: Heavy-tailed distribution; 0 = sub-millisecond (ICMP, UDP probes); extreme values (hours) = C2 keep-alive long-polling.
- `orig_bytes` / `resp_bytes`: `-` dash for SYN-only probes (no payload); numeric values span orders of magnitude. `resp_bytes = 0` with a high `orig_bytes` = potential upload exfiltration.
- `orig_pkts` / `resp_pkts`: Always integers; `resp_pkts = 0` = completely unanswered connection (port closed or firewall drop).
- `orig_ip_bytes` / `resp_ip_bytes`: Slightly larger than `orig_bytes`/`resp_bytes` due to IP header overhead. Most valuable for amplification attack detection (`resp_ip_bytes / orig_ip_bytes` >> 1 = DNS/NTP/SSDP amplification).

### 3.5 Dual-Label Taxonomy

IoT-23 provides two complementary labels:

```
label: Malicious / Benign   ← coarse binary label
detailed-label: PartOfAHorizontalPortScan / C&C-HeartBeat / ...  ← fine-grained
```

Data quality check: All `Benign` rows have `detailed-label = "-"` (no attack name). No `Benign` row has a non-dash detailed label. This confirms annotation consistency and means the dash in `detailed-label` of benign rows is **intentional** (no specific attack) rather than missing data.

### 3.6 Feature Role Classification (IoT-23)

| Role | Columns | Count |
|------|---------|-------|
| Behavioral | `duration`, `orig_bytes`, `resp_bytes`, `orig_pkts`, `resp_pkts`, `orig_ip_bytes`, `resp_ip_bytes`, `conn_state`, `history` | 9 |
| Identifier | `uid`, `id.orig_h`, `id.resp_h` | 3 |
| Contextual | `ts`, `id.orig_p`, `id.resp_p`, `proto`, `service`, `local_orig`, `local_resp` | 7 |
| Label/Ground Truth | `label`, `detailed-label` | 2 |
| Metadata/Auxiliary | `missed_bytes`, `tunnel_parents`, `source_scenario` | 3 |

---

## 4. Section 3 — Bot-IoT Dataset: Phase 0 Analysis

### 4.1 Dataset Provenance and Structure

The **Bot-IoT** dataset was produced by the University of New South Wales Canberra Cyber Range (Koroniotis et al., 2018) using the Argus NetFlow parser. Bot-IoT is the most richly engineered of the three datasets: rather than providing raw Zeek connection logs, it includes 14 UNSW-designed **behavioral window-aggregation features** that quantify traffic patterns over a recent time window.

The dataset is distributed as four standard CSV files (`UNSW_2018_IoT_Botnet_Full5pc_1.csv` through `_4.csv`). Unlike IoT-23, there are no metadata headers — standard `pd.read_csv()` with the default `header=0` setting works correctly. The files collectively contain approximately 14.8 million rows × 46 columns.

**Important sampling caveat:** The four CSV files are **ordered by attack type** — the first 100k rows of each file are entirely attack traffic; normal traffic appears only later. Phase 0's 100k-row-per-file cap therefore loaded exclusively attack records in the initial exploratory analysis. A full-dataset scan using chunked I/O was conducted to obtain accurate label distributions, which revealed the true class breakdown.

| Property | Value |
|----------|-------|
| Files | 4 × `UNSW_2018_IoT_Botnet_Full5pc_*.csv` |
| Total rows (full dataset) | ~14.8 million |
| Columns | 46 (feature) + `source_file` (loader provenance) |
| Format | Standard CSV, comma-separated, no metadata headers |
| Feature engineering | Yes — 14 UNSW window-aggregated behavioral features |
| Label structure | Three-level hierarchy: `attack` → `category` → `subcategory` |

### 4.2 Feature Architecture: Three Conceptual Layers

Bot-IoT features are organized into three distinct layers:

**Layer 1: Flow identifiers and raw network fields**

| Column | Meaning | IDS Role |
|--------|---------|----------|
| `pkSeqID` | Row sequence ID — monotonic counter | Metadata (drop) |
| `stime` | Flow start time (Unix float) | Temporal (split only) |
| `ltime` | Flow last-packet time (Unix float) | Temporal (redundant with `dur`) |
| `saddr` | Source IP | Identity (exclude) |
| `daddr` | Destination IP | Identity (exclude) |
| `sport` | Source port (−1 for ARP) | Contextual |
| `dport` | Destination port (−1 for ARP) | Contextual |
| `proto` | Protocol name (tcp/udp/arp/icmp) | Contextual |
| `proto_number` | Numeric encoding of proto | Contextual |
| `state` | Argus connection state (CON/RST/FIN/INT/REQ) | Behavioral |
| `state_number` | Numeric encoding of state | Behavioral |
| `flgs` | Argus flow flags string | Contextual |
| `flgs_number` | Numeric encoding of flags | Contextual |
| `seq` | Argus flow sequence number | Metadata (drop) |

**Layer 2: Per-flow volume and statistical features**

| Column | Meaning | IDS Relevance |
|--------|---------|--------------|
| `dur` | Flow duration (seconds) | HIGH |
| `pkts` | Total packets (src+dst) | HIGH |
| `bytes` | Total bytes (src+dst) | HIGH |
| `spkts` | Source→destination packets | HIGH |
| `dpkts` | Destination→source packets | HIGH |
| `sbytes` | Source→destination bytes | HIGH |
| `dbytes` | Destination→source bytes | HIGH |
| `rate` | Overall flow rate (bytes/sec) | HIGH |
| `srate` | Source-side rate (bytes/sec) | HIGH |
| `drate` | Destination-side rate (bytes/sec) | HIGH |
| `mean` | Mean packet size/IAT | MEDIUM |
| `stddev` | Std dev of packet size | MEDIUM (zero stddev in floods = strong signal) |
| `sum` | Sum of packet statistics | LOW (redundant with `bytes`) |
| `min` / `max` | Min/max packet size | MEDIUM |

**Layer 3: UNSW-engineered behavioral window aggregates (14 columns)**

These are the most distinctive features in Bot-IoT. They were computed over a **time window** for each flow, aggregating statistics about recent activity involving the same IP address, port, or protocol:

| Column | Meaning | IDS Significance |
|--------|---------|-----------------|
| `TnBPSrcIP` | Total bytes from this source IP in window | HIGH — high value = flooding source |
| `TnBPDstIP` | Total bytes to this destination IP in window | HIGH — high value = DDoS victim |
| `TnP_PSrcIP` | Total packets from this source IP in window | HIGH — scanner/flooder indicator |
| `TnP_PDstIP` | Total packets to this destination IP in window | HIGH — target under attack |
| `TnP_PerProto` | Total packets for this protocol in window | HIGH — protocol flooding |
| `TnP_Per_Dport` | Total packets to this destination port in window | HIGH — port-specific flood |
| `AR_P_Proto_P_SrcIP` | Average rate: protocol × source IP | HIGH — captures per-protocol attack rate per source |
| `AR_P_Proto_P_DstIP` | Average rate: protocol × destination IP | HIGH — DDoS victim under specific protocol |
| `N_IN_Conn_P_DstIP` | Inbound connection count to destination IP | HIGH — DDoS target detection |
| `N_IN_Conn_P_SrcIP` | Inbound connection count from source IP | HIGH — botnet node identification |
| `AR_P_Proto_P_Sport` | Average rate: protocol × source port | MEDIUM — noisy due to ephemeral ports |
| `AR_P_Proto_P_Dport` | Average rate: protocol × destination port | HIGH — service-specific attack rate |
| `Pkts_P_State_P_Protocol_P_DestIP` | Packets: state × protocol × destination IP | HIGH — RST×TCP×specific_IP = targeted reset flooding |
| `Pkts_P_State_P_Protocol_P_SrcIP` | Packets: state × protocol × source IP | HIGH — stateful attack pattern per source |

**Research implication of window features:** These 14 columns are not raw per-flow observations — they encode the *context* of a flow within recent network activity. A model trained on them will correctly identify a source IP that has sent 10,000 packets in the last minute as a DoS attacker even if the individual flow itself looks benign. However, they also introduce a **temporal ordering requirement**: the window features encode state that accumulates forward in time. Using a random train/test split would allow a flow from minute 5 to be in the test set while flows from minutes 4 and 6 are in training — the window features from those adjacent flows would leak future information about the "test" flow. Phase 1 must use a **time-ordered split** (train on earlier captures, test on later).

### 4.3 Sentinel Analysis: The Port -1 Anomaly

Bot-IoT introduces a novel sentinel not present in the Zeek-based datasets: **port values of -1**. This occurs for ARP (Address Resolution Protocol) and other non-port-bearing protocols (some ICMP variants). In ARP, there is no concept of source or destination port — the protocol operates at Layer 2/3 to resolve IP addresses to MAC addresses.

```
When proto = "arp":
    sport = -1  (no port concept)
    dport = -1  (no port concept)
```

Handling: A `has_port` binary indicator column was derived in Phase 1.1:
```python
has_port = (numeric_port != -1).astype("int8")
port_val  = numeric.where(numeric != -1, other=0)
```

This creates `univ_has_src_port` and `univ_has_dst_port` boolean flags in the universal schema. A model can learn to condition on these flags: if `has_dst_port = 0`, the connection is ARP or portless — a fundamentally different traffic class from TCP/UDP.

The full-dataset scan revealed that port -1 occurrences are significant in number, corresponding to the ARP traffic fraction in the IoT network.

### 4.4 Tri-Label Hierarchy

Bot-IoT provides the richest label structure of all three datasets:

```
attack (binary: 0/1)
  └── category (5 values)
        └── subcategory (fine-grained)
```

**Level 1 — binary:**
| Value | Meaning |
|-------|---------|
| 0 | Normal traffic (benign) |
| 1 | Attack traffic |

**Level 2 — category (5 values):**
| Category | Universal Class | Description |
|----------|----------------|-------------|
| Normal | Class 0 | Benign baseline |
| DoS | Class 2 — Volumetric | Single-vector denial of service |
| DDoS | Class 2 — Volumetric | Distributed denial of service |
| Reconnaissance | Class 1 — Reconnaissance | Port scans, OS fingerprinting |
| Theft | Class 4 — Exploit & Theft | Keylogging, data exfiltration |

**Level 3 — subcategory (fine-grained):**
- DoS/DDoS subcategories: `HTTP`, `UDP`, `TCP` (attack vector used)
- Reconnaissance: `Service_Scan`, `OS_Fingerprint`
- Theft: `Keylogging`, `Data_Exfiltration`

**Data quality assertion:** `attack = 0` must always co-occur with `category = 'Normal'`. Any violation indicates a labeling error. This was verified programmatically in Phase 1.1 validation.

### 4.5 Class Imbalance in Bot-IoT

The full-dataset scan revealed that Bot-IoT is **severely attack-skewed**: normal traffic constitutes only a small fraction of the dataset. This happens because the capture environment was designed to generate and record attack behavior — normal background traffic was present but not the focus. This has important Phase 1 implications: standard accuracy metrics will be misleading; the project uses F1-score, precision, and recall per class.

### 4.6 Engineering Challenges Identified in Bot-IoT

| Challenge | Description | Phase 1 Fix |
|-----------|-------------|-------------|
| Port -1 sentinel | ARP/ICMP flows set sport/dport=-1 | Create `has_port` indicator; clip to [0, 65535] |
| Extreme rate skew | `rate`, `srate`, `drate` span 6+ orders of magnitude in DoS attacks | Apply `log1p()` transform; use RobustScaler |
| Class imbalance | Normal traffic is a small minority | Stratified split; report F1, precision, recall |
| Identity leakage | `saddr`, `daddr` are unique to this testbed | Exclude from feature vector; use `TnBP*` aggregates instead |
| Window bias | 14 UNSW features encode temporal context | Time-ordered train/test split required |
| Redundant features | `bytes ≈ sbytes + dbytes`; `pkts ≈ spkts + dpkts` | Drop features with |r| > 0.95 |
| Tri-label consistency | `attack=0` must pair with `category='Normal'` | Assert and log violations |

---

## 5. Section 4 — Cross-Dataset Comparison

### 5.1 Structural Differences Summary

| Dimension | TON-IoT | IoT-23 (CTU) | Bot-IoT (UNSW) |
|-----------|---------|--------------|----------------|
| **Format** | Standard CSV | Zeek TSV with 8-line header | Standard CSV |
| **Engineered features** | Partial (DNS/HTTP extracted) | No (raw Zeek fields) | Yes (14 UNSW window stats) |
| **Total features** | 47 columns | 22 columns | 46 columns |
| **Scale** | 22.3M rows | ~325M rows | ~14.8M rows |
| **Binary label** | `label` (0/1) | `label` (split from compound col: Benign/Malicious) | `attack` (0/1) |
| **Multi-class label** | `type` (string: ddos, dos, xss, etc.) | `detailed-label` (split from compound col) | `category` (string: DoS, DDoS, etc.) |
| **Fine-grained label** | `type` (same column) | `detailed-label` | `subcategory` |
| **Null sentinel** | `-` (Zeek), numeric zeros | `-` (Zeek), `?`, `(empty)`, `F`, `T` | `-1` (ARP port), NaN (rare) |
| **Port sentinel** | None (always valid) | 0 for ICMP | -1 for ARP |
| **IP columns** | `src_ip`, `dst_ip` | `id.orig_h`, `id.resp_h` | `saddr`, `daddr` |
| **Port columns** | `src_port`, `dst_port` | `id.orig_p`, `id.resp_p` | `sport`, `dport` |
| **Bytes columns** | `src_bytes`, `dst_bytes` | `orig_bytes`, `resp_bytes` | `sbytes`, `dbytes` |
| **Packet columns** | `src_pkts`, `dst_pkts` | `orig_pkts`, `resp_pkts` | `spkts`, `dpkts` |
| **Duration column** | `duration` | `duration` (string — Zeek object dtype) | `dur` |
| **State column** | `conn_state` (Zeek codes) | `conn_state` (Zeek codes) | `state` (Argus codes) |
| **Timestamp column** | `ts` | `ts` | `stime` |

### 5.2 State Code Vocabulary Conflict

Both Zeek (used in TON-IoT and IoT-23) and Argus (used in Bot-IoT) record connection state — but using incompatible code systems:

**Zeek codes (TON-IoT, IoT-23):** `S0`, `S1`, `S2`, `S3`, `SF`, `REJ`, `RSTO`, `RSTR`, `RSTOS0`, `RSTRH`, `SH`, `SHR`, `OTH`

**Argus codes (Bot-IoT):** `CON`, `RST`, `FIN`, `INT`, `REQ`, `URN`, `ECO`, `ECR`, `ACC`, `CLO`

These required a **Universal State Vocabulary** mapping both systems to a shared 5-token space:

| Universal Token | Zeek codes → | Argus codes → | Meaning |
|----------------|-------------|--------------|---------|
| `attempt` | `S0`, `S1`, `OTH` | `REQ` | Initiated but not completed |
| `established` | `SF`, `S2`, `S3` | `CON`, `FIN` | Completed successfully |
| `rejected` | `REJ`, `RSTO`, `RSTR`, `RSTOS0`, `RSTRH` | `RST` | Terminated by RST |
| `other` | `SH`, `SHR` | `INT`, `URN`, `ECO`, `ECR` | Ambiguous/partial/ICMP |
| `unknown` | `-`, `?`, `(empty)` | (unmapped) | Not applicable or undetermined |

This vocabulary collapse is semantically principled: from an IDS perspective, `S0` (Zeek: SYN sent, no response) and `REQ` (Argus: request sent) both represent connection attempts — a model that treats them as identical is generalizing correctly.

### 5.3 Label Schema Conflict

The three datasets use three completely different raw column names and value schemas for the same concept:

| Dataset | Binary label column | Multi-class column | Binary values | Multi-class values |
|---------|--------------------|--------------------|---------------|-------------------|
| TON-IoT | `label` | `type` | 0, 1 | normal, scanning, ddos, dos, backdoor, injection, mitm, password, ransomware, xss |
| IoT-23 | `label` (in compound col) | `detailed-label` (in compound col) | Benign, Malicious | PartOfAHorizontalPortScan, C&C-HeartBeat, Okiru, DDoS, FileDownload, ... |
| Bot-IoT | `attack` | `category` | 0, 1 | Normal, DoS, DDoS, Reconnaissance, Theft |

Unifying these required the 5-class taxonomy with three separate lookup dictionaries (`TONIOT_LABEL_MAP`, `IOT23_LABEL_MAP`, `BOTIOT_CATEGORY_MAP`) mapping raw values to integer class IDs 0–4.

### 5.4 Feature Coverage Gaps

No single feature set is a strict subset of another. The three datasets have unique features with no cross-dataset equivalents:

**TON-IoT exclusive:** DNS query class/type/response code; HTTP request/response body lengths; HTTP status code.

**IoT-23 exclusive:** `uid` (Zeek connection UID); `history` (TCP flag event string); `orig_ip_bytes` / `resp_ip_bytes` (IP-layer byte counts); `tunnel_parents` (tunnel encapsulation ID).

**Bot-IoT exclusive:** 14 UNSW window-aggregated behavioral features; `flgs` / `flgs_number` (Argus flow flags); `mean`, `stddev`, `sum`, `min`, `max` (per-flow packet statistics); `rate`, `srate`, `drate` (per-direction rates); `ltime`, `seq`, `pkSeqID`.

---

## 6. Section 5 — Universal Schema Alignment (Phase 1.1)

### 6.1 The Generalization Problem

The central challenge of multi-dataset IDS is that no directly usable feature representation exists across all three datasets. A naive approach would be to take the intersection of common features — but this leaves only 9 behavioral features (`duration`, bilateral bytes, bilateral packets, protocol, state, ports), discarding all dataset-specific context that distinguishes attack families.

The alternative — modeling each dataset separately — would defeat the purpose: the RAG-IDS knowledge base needs vectors from all three datasets to provide comprehensive coverage of IoT attack patterns.

**Solution: Union Schema (Option B) with Group A/B partitioning.**

### 6.2 Schema Design: Option B — Union Schema

The Union Schema approach retains ALL features from ALL datasets in a single 52-column output schema. Features absent from a particular dataset receive a clearly defined sentinel value, not NaN. This design has several advantages:

1. **No information loss:** All dataset-specific features are preserved.
2. **Learnable sentinels:** A model or retrieval engine can learn that `botiot_rate = -1.0` means "this row comes from a non-Bot-IoT dataset" — a useful signal for dataset-aware retrieval.
3. **Semantic clarity:** `<absent>` (for categorical columns) is distinct from `unknown` (which means "the feature was present but could not be determined"). This preserves the difference between "Zeek couldn't identify the service" vs. "Bot-IoT doesn't collect service information at all."
4. **Forward compatibility:** When future datasets are added, they can be integrated by mapping their columns into the existing schema and injecting sentinels for features they don't provide.

### 6.3 52-Column Schema: Group A / Group B Decomposition

**Group A — Universal Core (19 columns):** Present in all three datasets. Renamed to `univ_` prefix.

| Universal Column | TON-IoT Source | IoT-23 Source | Bot-IoT Source |
|-----------------|----------------|--------------|----------------|
| `dataset_source` | `"toniot"` | `"iot23"` | `"botiot"` |
| `univ_duration` | `duration` | `duration` | `dur` |
| `univ_src_bytes` | `src_bytes` | `orig_bytes` | `sbytes` |
| `univ_dst_bytes` | `dst_bytes` | `resp_bytes` | `dbytes` |
| `univ_src_pkts` | `src_pkts` | `orig_pkts` | `spkts` |
| `univ_dst_pkts` | `dst_pkts` | `resp_pkts` | `dpkts` |
| `univ_proto` | `proto` | `proto` | `proto` |
| `univ_state` | `conn_state` | `conn_state` | `state` |
| `univ_src_port` | `src_port` | `id.orig_p` | `sport` |
| `univ_dst_port` | `dst_port` | `id.resp_p` | `dport` |
| `univ_has_src_port` | `1` (always) | `id.orig_p != 0` | `sport != -1` |
| `univ_has_dst_port` | `1` (always) | `id.resp_p != 0` | `dport != -1` |
| `univ_label_binary` | `label` | split compound col → field[1] | `attack` |
| `univ_label_multiclass` | `type`→TONIOT_MAP | `detailed-label`→IOT23_MAP | `category`→BOTIOT_MAP |
| `univ_label_str` | mapped class name | mapped class name | mapped class name |
| `univ_specific_attack` | `type` (verbatim) | `detailed-label` (verbatim) | `subcategory` (verbatim) |
| `meta_src_ip` | `src_ip` | `id.orig_h` | `saddr` |
| `meta_dst_ip` | `dst_ip` | `id.resp_h` | `daddr` |
| `meta_timestamp` | `ts` | `ts` | `stime` |

**Group B — Dataset-Conditional (33 columns):** Present in one or two datasets; sentinel injected otherwise.

Group B / Zeek (5 columns — present in TON-IoT and IoT-23; sentinel `<absent>` or -1 for Bot-IoT):
- `zeek_service`, `zeek_missed_bytes`, `zeek_history`, `zeek_src_ip_bytes`, `zeek_dst_ip_bytes`

Group B / TON-IoT (6 columns — present only in TON-IoT; sentinel -1 for IoT-23 and Bot-IoT):
- `toniot_dns_qclass`, `toniot_dns_qtype`, `toniot_dns_rcode`
- `toniot_http_request_body_len`, `toniot_http_response_body_len`, `toniot_http_status_code`

Group B / Bot-IoT (22 columns — present only in Bot-IoT; sentinel -1.0 or -1 for TON-IoT and IoT-23):
- `botiot_mean`, `botiot_stddev`, `botiot_sum`, `botiot_min`, `botiot_max`
- `botiot_rate`, `botiot_srate`, `botiot_drate`
- `botiot_TnBPSrcIP`, `botiot_TnBPDstIP`, `botiot_TnP_PSrcIP`, `botiot_TnP_PDstIP`
- `botiot_TnP_PerProto`, `botiot_TnP_Per_Dport`
- `botiot_AR_P_Proto_P_SrcIP`, `botiot_AR_P_Proto_P_DstIP`
- `botiot_N_IN_Conn_P_DstIP`, `botiot_N_IN_Conn_P_SrcIP`
- `botiot_AR_P_Proto_P_Sport`, `botiot_AR_P_Proto_P_Dport`
- `botiot_Pkts_P_State_P_Protocol_P_DestIP`, `botiot_Pkts_P_State_P_Protocol_P_SrcIP`

### 6.4 Sentinel Vocabulary: `<absent>` vs. `unknown`

Two distinct sentinel values were introduced for categorical Group B columns:

```python
ABSENT   = "<absent>"  # Feature not collected by this dataset
UNKNOWN  = "unknown"   # Feature collected, but value could not be determined
```

This distinction is semantically important:
- `zeek_service = "unknown"` (ToN-IoT or IoT-23 row): The service was present but Zeek could not identify it (encrypted traffic).
- `zeek_service = "<absent>"` (Bot-IoT row): Bot-IoT does not use a Zeek service detector — the column is structurally absent. The model should interpret `<absent>` as "no information about service" rather than "service present but unknown."

### 6.5 Transformation Engine

The alignment was implemented as three pure chunk-transformer functions:

**`transform_toniot_chunk(chunk)`:** Handles:
- `src_bytes` arrives as `dtype=object` (some rows have non-numeric string contamination) → `safe_int()` coerce
- `local_orig`, `local_resp` may have `F`/`T` boolean strings → preserved as categorical
- No port sentinels (all ports always valid) → `has_port = 1` always
- `zeek_history` absent → inject `"<absent>"` sentinel

**`transform_iot23_chunk(chunk)`:** Handles:
- All numeric fields arrive as `dtype=object` (Zeek TSV string columns) → `safe_int()` / `safe_float()`
- Compound label column extraction: `line.split("   ", n=2)` → [tunnel_parents, label, detailed-label]
- Port values: `id.orig_p`, `id.resp_p` may be 0 for ICMP → `handle_port(sentinel_value=0)`
- `#close` footer rows already filtered at load time; `handle_port()` handles residual edge cases

**`transform_botiot_chunk(chunk)`:** Handles:
- Port -1 sentinel for ARP: `handle_port(chunk["sport"], sentinel_value=-1)` → derives has_port flag
- `state` uses Argus codes (CON/RST/FIN) → `map_state()` maps to universal 5-token vocab
- Tri-label hierarchy: reads `attack` (binary), `category` (multi-class), `subcategory` (specific)

**`handle_port()` robustness:** A hex-string edge case was discovered during testing where some Bot-IoT port columns contained hex-encoded values (`0x0303`). The port handler uses a two-pass approach: first `pd.to_numeric()`, then a vectorized hex parse for any remaining strings starting with `0x`:

```python
hex_mask = str_s.str.startswith("0x")
if hex_mask.any():
    numeric.loc[hex_mask] = str_s.loc[hex_mask].apply(
        lambda x: int(x, 16) if x not in ("nan", "none", "") else np.nan
    )
```

### 6.6 Memory Architecture: Chunked Streaming

Processing 351 million rows (25+ GB raw data) in-memory at once would require more RAM than is available on a development workstation. The alignment used **PyArrow ParquetWriter for incremental row-group append**:

1. `pd.read_csv(fpath, chunksize=100_000)` — reads 100k rows at a time
2. `transform_*_chunk(chunk)` — transforms chunk to unified schema
3. `pa.Table.from_pandas(aligned)` — converts to Arrow table
4. `writer.write_table(table)` — appends as a Parquet row group
5. Repeat until file exhausted; open next file

This keeps peak RAM consumption at ≈ 40–50 MB (one chunk × 52 columns × 8 bytes ≈ 40 MB) regardless of total dataset size. A staging-file (`*.parquet.tmp`) strategy was used to avoid Windows file lock issues with OneDrive sync: all writes target a `.tmp` file which is atomically renamed to the final `.parquet` path upon completion.

**Windows/OneDrive file lock mitigation:** The following recovery strategy was implemented:
- `output_path.unlink()` on `force_rerun`: catches `PermissionError` gracefully
- Writes to `.parquet.tmp` staging file throughout
- `staging_path.replace(output_path)` at the end: uses `Path.replace()` (atomic overwrite on Windows) rather than `Path.rename()` (fails if destination exists)

**Idempotency guard:** If a complete Parquet file already exists (`output_path.exists() and not force_rerun`), the function reads its row count from Parquet metadata and returns immediately without reprocessing. This supports incremental re-runs after kernel restarts.

### 6.7 Protocol Normalization

Protocol strings from all three datasets were normalized to a closed 5-token vocabulary: `{tcp, udp, icmp, arp, other}`. Any protocol string not in this set (e.g., `icmp6`, `igmp`, `hopopt`) maps to `other`. The normalization function:

```python
def normalize_proto(series: pd.Series) -> pd.Series:
    lowered = series.str.lower().str.strip()
    return lowered.where(lowered.isin(VALID_PROTO_VOCAB), other="other")
```

**Justification:** IoT devices predominantly use TCP, UDP, ICMP, and ARP. Rare protocols appear in < 0.1% of flows and their individual semantics are unlikely to generalize across datasets. Folding them into `other` prevents the model from learning protocol-specific patterns that appear in only one dataset.

### 6.8 Processing Results and Validation

**Row-count completeness audit:**

| Dataset | Source rows | Parquet rows | Coverage |
|---------|------------|--------------|---------|
| TON-IoT | 22,339,021 | 22,339,021 | ✅ 100.0000% |
| IoT-23 | ~325M | ~325M minus ≤23 `#close` footer rows | ✅ ≈100% (delta ≤ 23 = one footer per file) |
| Bot-IoT | ~14.8M | ~14.8M | ✅ 100.0000% |

**Schema validation checks passed:**
- ✅ All three Parquet files share identical 52-column schema in canonical order
- ✅ Column dtypes: `float64` for continuous features, `int64` for counts, `int8` for binary labels/flags
- ✅ No NaN values in any column (all sentinels are explicit -1, -1.0, or string tokens)
- ✅ `univ_proto` values ⊆ `{tcp, udp, icmp, arp, other}` across all three datasets
- ✅ `univ_state` values ⊆ `{attempt, established, rejected, other, unknown}` across all three datasets
- ✅ Zero unmapped labels (`univ_label_multiclass = -1`) in TON-IoT after adding `mitm → class 4` to the taxonomy map
- ✅ Group B sentinel values exactly correct: `botiot_rate = -1.0` for non-Bot-IoT rows; `toniot_dns_qclass = -1` for IoT-23 and Bot-IoT rows; `zeek_service = "<absent>"` for Bot-IoT rows

**Union Schema mathematical proof (Section 8C):** Per-dataset full column scans of `univ_specific_attack` and `univ_label_str` confirmed that attack type preservation is 100% complete — all 10 TON-IoT attack type strings are present in the TON-IoT Parquet.

**Commit:** `b9b63ee` — Phase 1.1 Universal Schema Alignment complete

---

## 7. Section 6 — Decisions, Justifications, and Research Implications

### 7.1 Why Three Datasets?

Single-dataset IDS models suffer from **network specificity bias**: they learn the IP ranges, port usage patterns, and traffic volumes of the specific testbed, not the behavioral fingerprints of attacks. By training on three structurally independent datasets:
1. TON-IoT: UNSW Canberra synthetic testbed with diverse IoT devices
2. IoT-23: Czech University real malware capture in IoT sandbox
3. Bot-IoT: UNSW Canberra testbed with Argus-processed Botnet traffic

...the RAG-IDS knowledge base gains coverage of attack patterns across different network environments. A retrieval hit on a previously unseen traffic sample is more likely to be a genuine behavioral similarity rather than a network-topology artifact.

### 7.2 Why the Union Schema (Option B) Rather Than Intersection?

The intersection of features common to all three datasets contains only 9 universal behavioral features. This would:
1. Discard all 14 UNSW behavioral window features from Bot-IoT — the most behaviorally rich features in the project.
2. Discard DNS/HTTP extraction from TON-IoT — covering specific application-layer attacks (DNS exfiltration, HTTP injection).
3. Discard the Zeek `history` field from IoT-23 — which encodes the complete TCP handshake state machine.

The Union Schema with sentinel injection preserves all of this information. The 14 UNSW features enrich the Bot-IoT rows specifically; when these features are -1.0 for TON-IoT/IoT-23 rows, they simply provide no signal for those rows. A well-trained model learns to ignore -1.0 sentinel values.

### 7.3 Why the 5-Class Taxonomy?

The three datasets use overlapping but incompatible attack categorization schemes. The 5-class taxonomy was designed by examining all raw attack labels across all three datasets and grouping by **behavioral mechanism** rather than by name:

| Class | Behavioral Mechanism | Decision Rationale |
|-------|---------------------|-------------------|
| 0 — Normal | No attack | Trivial baseline |
| 1 — Reconnaissance | Active probing to discover targets/vulnerabilities | Port scanning, OS fingerprinting, horizontal spread all share the same behavioral signature: many short connections to varied destination IPs/ports |
| 2 — Volumetric | Overwhelming resources with traffic volume | DoS and DDoS are mechanistically identical from the flow perspective; only scale differs |
| 3 — C2_Botnet | Persistent bidirectional communication with a controller | Mirai, Torii, Okiru heartbeats share the same long-duration, regular-interval behavioral pattern |
| 4 — Exploit & Theft | Payload execution, credential theft, data movement | Injection, XSS, keylogging, exfiltration all involve anomalous payload content patterns |

**Research implication:** The 5-class taxonomy makes this project more ambitious than binary IDS. The RAG retriever must distinguish between classes with potentially overlapping behavioral signatures (e.g., a scanning flow and a DoS flow both generate many packets but differ in directionality and target pattern).

### 7.4 The `<absent>` vs. `unknown` Sentinel Distinction

This is a subtle but important design decision. In the final unified schema:
- `zeek_service = "unknown"` means: *Zeek tried to identify the application layer protocol and failed* (e.g., encrypted traffic, custom application, obfuscated C2 channel). The feature is present, the observation is "we don't know."
- `zeek_service = "<absent>"` means: *Bot-IoT does not collect Zeek service detection data.* The column has no meaning for Bot-IoT rows.

If both were encoded identically (e.g., both as -1 or both as NaN), a model could not distinguish these two conditions. Critically, encrypted C2 traffic from IoT-23 might have `zeek_service = "unknown"` — a genuine behavioral indicator of evasion — which would be indistinguishable from a Bot-IoT row that simply doesn't provide service data. Keeping `<absent>` as a distinct token prevents this semantic confusion.

### 7.5 Why Parquet Instead of CSV for the Unified Output?

The unified TON-IoT Parquet is ~22M rows × 52 columns. At 8 bytes per float64/int64, the full float64 representation would require ~9 GB as a CSV. Parquet with Snappy compression achieves approximately 3–4× compression while being directly readable by pandas, PyArrow, and Spark — all of which are used in later pipeline stages. Additionally, Parquet stores column-level schema metadata, ensuring that dtypes are preserved between notebook sessions without requiring explicit casting on reload.

### 7.6 Research Implications for the RAG-IDS Pipeline

The Universal Schema Alignment is the foundation of a generalization capability that distinguishes RAG-IDS from conventional IDS approaches:

1. **Cross-dataset retrieval:** A query vector from a live TON-IoT flow can be compared against Bot-IoT knowledge base entries because they share the same 50-dimensional embedding space (produced in Phase 1.2 from the 52-column unified schema).

2. **Dataset-source-aware context:** The `dataset_source` column is preserved in metadata. When the retriever returns similar historical flows, it can report "This attack pattern was observed in IoT-23 (CTU Mirai capture) and Bot-IoT (UNSW Botnet testbed)" — providing the human analyst with cross-dataset evidence.

3. **Sentinel-aware embedding:** The vectorizer (Phase 1.2) handles -1.0 sentinel values distinctly from zero (which is a genuine observed value). The embedding model learns that -1.0 = "no information" rather than "zero-value observation."

4. **Label taxonomy generalization:** The 5-class taxonomy enables a retrieval match to be meaningful even when the matched flow comes from a different dataset with a different raw attack category. The retrieval engine returns class ID, not raw label string.

---

## Appendix A: Phase 0 Compliance Checklist

All Phase 0 notebooks observed the following strict constraints:

| Rule | Rationale | Status |
|------|-----------|--------|
| No feature dropping | Premature dropping destroys cross-dataset comparison ability | ✅ All columns kept |
| No encoding/transformation | Encoding changes semantics; Phase 0 observes only | ✅ Raw values only |
| No scaling/normalization | Statistics on raw data; scaling is a Phase 1 decision | ✅ Stats on raw data |
| No model training | Phase 0 is a read-only audit | ✅ No fit/predict calls |
| No assumption about importance | Feature selection is a Phase 1 decision; Phase 0 only classifies roles | ✅ All roles tagged only |

---

## Appendix B: Artifacts Generated

| File | Contents | Phase Generated |
|------|----------|----------------|
| `toniot_phase0_column_inventory.csv` | Master column list with dtypes and stats | Phase 0.1 |
| `toniot_phase0_role_classification.csv` | Feature role assignments | Phase 0.1 |
| `toniot_phase0_feature_meanings.csv` | Semantic meaning of each feature | Phase 0.1 |
| `toniot_phase0_placeholder_analysis.csv` | Placeholder value distribution | Phase 0.1 |
| `iot23_phase0_column_inventory.csv` | IoT-23 column inventory | Phase 0.2 |
| `iot23_phase0_sentinel_analysis.csv` | Multi-sentinel analysis | Phase 0.2 |
| `iot23_phase0_feature_meanings.csv` | IoT-23 feature meanings | Phase 0.2 |
| `iot23_phase0_role_classification.csv` | IoT-23 role assignments | Phase 0.2 |
| `botiot_phase0_column_inventory.csv` | Bot-IoT column inventory | Phase 0.3 |
| `botiot_phase0_sentinel_analysis.csv` | Bot-IoT sentinel analysis | Phase 0.3 |
| `botiot_fullscan_label_distribution.csv` | Full 14.8M-row label distribution | Phase 0.3 |
| `botiot_fullscan_numerical_stats.csv` | Running statistical scan over all rows | Phase 0.3 |
| `phase1_1_schema_manifest.json` | Machine-readable 52-column schema + mappings | Phase 1.1 |
| `phase1_1_label_distribution.csv` | Label distribution per dataset from Parquet | Phase 1.1 |
| `phase1_1_column_registry.csv` | Column groups, sentinels, source datasets | Phase 1.1 |
| `data/unified/toniot_aligned.parquet` | 22.3M rows, 52 cols, Snappy-compressed | Phase 1.1 |
| `data/unified/iot23_complete.parquet` | ~325M rows, 52 cols, Snappy-compressed | Phase 1.1 |
| `data/unified/botiot_52col.parquet` | ~14.8M rows, 52 cols, Snappy-compressed | Phase 1.1 |

---

## Appendix C: 5-Class Taxonomy Full Mapping

| Class ID | Universal Name | TON-IoT `type` values | IoT-23 `detailed-label` values | Bot-IoT `category` values |
|----------|---------------|----------------------|-------------------------------|--------------------------|
| 0 | Normal | `normal` | `-` (Benign) | `Normal` |
| 1 | Reconnaissance | `scanning` | `PartOfAHorizontalPortScan`, `PartOfAHorizontalPortScan-Attack` | `Reconnaissance` |
| 2 | Volumetric_Attack | `ddos`, `dos` | `DDoS`, `Attack` | `DoS`, `DDoS` |
| 3 | C2_Botnet | (none directly — covered by Exploit) | `Okiru`, `Okiru-Attack`, `C&C`, `C&C-HeartBeat`, `C&C-HeartBeat-Attack`, `C&C-HeartBeat-FileDownload`, `C&C-FileDownload`, `C&C-Mirai`, `C&C-Torii`, `C&C-PartOfAHorizontalPortScan`, `Torii` | (none — DoS/DDoS are separate) |
| 4 | Exploit_and_Theft | `backdoor`, `injection`, `mitm`, `password`, `ransomware`, `xss` | `FileDownload` | `Theft` |

**Note on ToN-IoT Class 3:** The TON-IoT dataset does not include a C2/botnet category. Its attack types (backdoor, injection, xss, etc.) are product-style attacks that map to Class 4. The C2_Botnet class is populated exclusively from IoT-23 (Mirai, Okiru, Torii botnets). This class imbalance in the per-dataset distributions is by design — cross-dataset synthesis ensures coverage of all 5 classes.

---

*Report generated from notebook source code and Phase 0 EDA outputs.*  
*All figures reflect data as characterized in Phase 0 read-only analysis.*  
*Phase 1.1 processing statistics are from the completed alignment run (commit `b9b63ee`).*

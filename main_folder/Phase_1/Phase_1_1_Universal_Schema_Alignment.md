# Phase 1.1 — Universal Schema Alignment  `[v5.1 — 114-Dimensional Behavioral Schema]`

**Objective:** Transform the three v4 aligned Parquet files into the **Universal Behavioral Schema v5.1**
with protocol-triggered masking, 8-class UBT taxonomy, and evidence sensor logic.

**Output:** `aligned_schema_v5.parquet` — unified schema consumed by Phase 1.2.

---

## Universal Behavioral Schema v5.1 — 114 Dimensions

| Block | Dims | Contents |
|---|---|---|
| **Block 1 — Core** | 5 | duration, bytes_in, bytes_out, pkts_in, pkts_out |
| **Block 2 — Protocol** | 18 | proto OHE (6) + service OHE (12, gated by `has_svc`) |
| **Block 3 — State** | 5 | PENDING / ESTABLISHED / REJECTED / RESET / OTHER |
| **Block 4 — Port** | 16 | sport_func (7-OHE) + dport_func (7-OHE) + port_freq (2) |
| **Block 5 — App-Layer** | 51 | DNS (15) + HTTP (21) + SSL (15) |
| **Block 6 — Momentum** | 14 | 14 UNSW Bot-IoT window features |
| **Mask Bits** | 5 | has_svc, has_dns, has_http, has_ssl, has_unsw |
| **TOTAL** | **114** | |

**Masking Rule:** If mask bit = 0 → entire corresponding block forced to 0.0

## UBT Archetypes (8)
`NORMAL` · `SCAN` · `DOS_DDOS` · `BOTNET_C2` · `EXPLOIT` · `BRUTE_FORCE` · `THEFT_EXFIL` · `ANOMALY`


### Cell 1

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 1 | Imports + Version Banner
# ─────────────────────────────────────────────────────────────────────────────
import sys, os, time, warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SCHEMA_VERSION = "v5.1"
TOTAL_DIMS     = 114

# ── PyArrow (Parquet engine) ──────────────────────────────────────────────────
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    print(f"✅ pyarrow {pa.__version__}")
except ImportError:
    os.system(f"{sys.executable} -m pip install pyarrow -q")
    import pyarrow as pa
    import pyarrow.parquet as pq
    print(f"✅ pyarrow installed")

# ── tqdm (progress bars) ──────────────────────────────────────────────────────
try:
    from tqdm import tqdm
    print("✅ tqdm available")
except ImportError:
    def tqdm(it, **kw):
        return it
    print("⚠️  tqdm not found — plain iteration")

print(f"\n🔷 Universal Behavioral Schema {SCHEMA_VERSION} — {TOTAL_DIMS} Dimensions")
print(f"   Phase 1.1: Raw v4 Parquets → Aligned Schema v5.1")
print(f"\n✅ Python  {sys.version.split()[0]}")
print(f"✅ pandas  {pd.__version__}")
print(f"✅ numpy   {np.__version__}")

`

**Output:**
`
✅ pyarrow 23.0.0  — Parquet write/read enabled
✅ tqdm available

✅ Python 3.13.9
✅ pandas  2.2.3
✅ numpy   2.1.3
`

### Cell 2

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 2 | Paths + Processing Constants
# ─────────────────────────────────────────────────────────────────────────────
NOTEBOOK_DIR  = Path.cwd()              # .../Phase_1/
MAIN_DIR      = NOTEBOOK_DIR.parent    # .../main_folder/
DATA_DIR      = MAIN_DIR / "data"
UNIFIED_DIR   = DATA_DIR / "unified"
ARTIFACTS_DIR = MAIN_DIR / "artifacts"
VECTORS_DIR   = DATA_DIR / "vectors"

# ── Raw Source Dataset Directories (Phase 0 original data — NOT v4 Parquets) ─
TONIOT_RAW_DIR  = DATA_DIR / "ton_iot"
IOT23_RAW_DIR   = DATA_DIR / "iot_23"
BOTIOT_RAW_DIR  = DATA_DIR / "bot_iot"

# ── Output: v5.1 unified aligned schema ──────────────────────────────────────
ALIGNED_V51_PARQUET = UNIFIED_DIR / "aligned_schema_v5.parquet"

# Streaming chunk size
CHUNK_SIZE = 100_000

# ── Create directories ────────────────────────────────────────────────────────
for d in [UNIFIED_DIR, ARTIFACTS_DIR, VECTORS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Discover raw source files ─────────────────────────────────────────────────
toniot_files = sorted(TONIOT_RAW_DIR.glob("Network_dataset_*.csv"))
botiot_files = sorted(BOTIOT_RAW_DIR.glob("UNSW_2018_IoT_Botnet_Full5pc_*.csv"))
iot23_logs   = sorted(IOT23_RAW_DIR.rglob("conn.log.labeled"))

print("=" * 68)
print(f"  Universal Behavioral Schema {SCHEMA_VERSION} — Phase 1.1")
print(f"  Input: RAW SOURCE FILES (not v4 Parquets)")
print("=" * 68)

print("\n📁 Raw data directories:")
for label, path in [
    ("TON-IoT raw",  TONIOT_RAW_DIR),
    ("IoT-23 raw",   IOT23_RAW_DIR),
    ("Bot-IoT raw",  BOTIOT_RAW_DIR),
]:
    status = "✅" if path.exists() else "❌ MISSING"
    print(f"  {status}  {label:<18}  {path}")

print("\n📂 Raw source file counts:")
print(f"  TON-IoT CSV files   : {len(toniot_files):>4d}  (Network_dataset_*.csv)")
print(f"  IoT-23 log files    : {len(iot23_logs):>4d}  (conn.log.labeled)")
print(f"  Bot-IoT CSV files   : {len(botiot_files):>4d}  (UNSW_2018_IoT_Botnet_Full5pc_*.csv)")

print(f"\n📤 Output: {ALIGNED_V51_PARQUET}")

missing = []
if not toniot_files: missing.append("TON-IoT")
if not iot23_logs:   missing.append("IoT-23")
if not botiot_files: missing.append("Bot-IoT")
if missing:
    raise FileNotFoundError(f"Raw source files missing for: {missing}. Verify DATA_DIR paths.")

`

**Output:**
`
=================================================================
📁 PATH CONFIGURATION
=================================================================
  ✅  TON-IoT data        c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\data\ton_iot
  ✅  IoT-23 data         c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\data\iot_23
  ✅  Bot-IoT data        c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\data\bot_iot
  ✅  Unified out         c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\data\unified
  ✅  Artifacts           c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\main_folder\artifacts

  TON-IoT CSV files  : 23
  IoT-23 log files   : 23
  Bot-IoT CSV files  : 4
`

---
## Section 1 — Schema Registries

UBT Taxonomy (8 archetypes), State 5-token OHE, Protocol/Service vocabularies, Port Function 7-way classifier.
All lookup tables are closed and authoritative — no magic strings.


### Cell 3

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 3 | Schema Registries — UBT Taxonomy + State / Protocol / Port /
#          HTTP Method / SSL Cipher (raw DNA from source files)
# ─────────────────────────────────────────────────────────────────────────────

# ── 3A: UBT Archetype Taxonomy (8 classes) ───────────────────────────────────
UBT_ARCHETYPES = [
    "NORMAL", "SCAN", "DOS_DDOS", "BOTNET_C2",
    "EXPLOIT", "BRUTE_FORCE", "THEFT_EXFIL", "ANOMALY"
]

UBT_KEYWORD_MAP = {
    # NORMAL
    "normal": "NORMAL", "benign": "NORMAL", "heartbeat": "NORMAL",
    # SCAN
    "scanning": "SCAN", "portscan": "SCAN", "os_fingerprint": "SCAN",
    "service_scan": "SCAN", "reconnaissance": "SCAN",
    "partofhorizontalportscan": "SCAN",
    "partofhorizontalportscan-attack": "SCAN",
    # DOS_DDOS
    "dos": "DOS_DDOS", "ddos": "DOS_DDOS", "flood": "DOS_DDOS",
    "attack": "DOS_DDOS",
    # BOTNET_C2
    "c&c": "BOTNET_C2", "c&c-heartbeat": "BOTNET_C2",
    "c&c-heartbeat-attack": "BOTNET_C2", "c&c-filedownload": "BOTNET_C2",
    "c&c-heartbeat-filedownload": "BOTNET_C2",
    "c&c-mirai": "BOTNET_C2", "c&c-torii": "BOTNET_C2",
    "c&c-partofhorizontalportscan": "BOTNET_C2",
    "okiru": "BOTNET_C2", "okiru-attack": "BOTNET_C2",
    "mirai": "BOTNET_C2", "gafgyt": "BOTNET_C2", "torii": "BOTNET_C2",
    "commandexecution": "BOTNET_C2",
    # EXPLOIT
    "injection": "EXPLOIT", "xss": "EXPLOIT", "exploit": "EXPLOIT",
    "mitm": "EXPLOIT", "ransomware": "EXPLOIT",
    # BRUTE_FORCE
    "bruteforce": "BRUTE_FORCE", "password": "BRUTE_FORCE",
    "brute": "BRUTE_FORCE",
    # THEFT_EXFIL
    "theft": "THEFT_EXFIL", "exfiltration": "THEFT_EXFIL",
    "malware_download": "THEFT_EXFIL", "filedownload": "THEFT_EXFIL",
    "keylogging": "THEFT_EXFIL", "data_exfiltration": "THEFT_EXFIL",
    "malware": "THEFT_EXFIL",
    # ANOMALY
    "backdoor": "ANOMALY", "weird": "ANOMALY", "anomaly": "ANOMALY",
    "weird_notice": "ANOMALY",
}

V4_CLASS_TO_UBT = {0:"NORMAL", 1:"SCAN", 2:"DOS_DDOS", 3:"BOTNET_C2", 4:"EXPLOIT", -1:"ANOMALY"}

def map_to_ubt(specific_attack: str, multiclass_int=None) -> str:
    attack_clean = str(specific_attack).lower().strip()
    if attack_clean in UBT_KEYWORD_MAP:
        return UBT_KEYWORD_MAP[attack_clean]
    for keyword, ubt in UBT_KEYWORD_MAP.items():
        if keyword in attack_clean:
            return ubt
    if multiclass_int is not None:
        try:
            mc = int(float(multiclass_int))
        except (ValueError, TypeError):
            mc = -1
        return V4_CLASS_TO_UBT.get(mc, "ANOMALY")
    return "ANOMALY"

# ── 3B: State mapping → v5.1 5-token OHE ─────────────────────────────────────
STATE_V51_MAP = {
    # Zeek conn_state codes
    "S0":      "PENDING",      "S1":      "PENDING",
    "OTH":     "PENDING",      "REQ":     "PENDING",
    "SF":      "ESTABLISHED",  "S2":      "ESTABLISHED",
    "S3":      "ESTABLISHED",  "CON":     "ESTABLISHED",
    "FIN":     "ESTABLISHED",
    "REJ":     "REJECTED",
    "RSTO":    "RESET",        "RSTOS0":  "RESET",
    "RSTR":    "RESET",        "RSTRH":   "RESET",
    "RST":     "RESET",
    "SHR":     "OTHER",        "SH":      "OTHER",
    "INT":     "OTHER",        "URN":     "OTHER",
    "ECO":     "OTHER",        "ECR":     "OTHER",
    "-":       "OTHER",        "?":       "OTHER",
    "(empty)": "OTHER",        "":        "OTHER",
    # Argus (Bot-IoT)
    "ACC":     "ESTABLISHED",  "CLO":     "ESTABLISHED",
}
UBT_STATE_TOKENS = ["PENDING", "ESTABLISHED", "REJECTED", "RESET", "OTHER"]

# ── 3C: Protocol OHE vocabulary (6 dims) ──────────────────────────────────────
PROTO_TOKENS = ["tcp", "udp", "icmp", "arp", "ipv6", "other"]
PROTO_IDX    = {t: i for i, t in enumerate(PROTO_TOKENS)}

# ── 3D: Service OHE vocabulary (12 dims, gated by has_svc) ───────────────────
SERVICE_TOKENS = [
    "dns", "http", "ssl", "ftp", "ssh", "smtp",
    "dhcp", "quic", "ntp", "rdp", "pop3", "other"
]
SERVICE_IDX  = {t: i for i, t in enumerate(SERVICE_TOKENS)}
SERVICE_SET  = set(SERVICE_TOKENS)
ABSENT_SERVICE_VALS = frozenset({"<absent>", "-", "unknown", "", "none", "(empty)"})

# ── 3E: Port Function 7-way OHE ───────────────────────────────────────────────
PORT_FUNC_TOKENS = [
    "SCADA_CONTROL", "IOT_MANAGEMENT", "WEB_SERVICES",
    "NETWORK_CORE", "REMOTE_ACCESS", "FUNC_EPHEMERAL", "FUNC_UNKNOWN"
]
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
    if p < 0:               return "FUNC_UNKNOWN"
    if p in SCADA_PORTS:    return "SCADA_CONTROL"
    if p in IOT_MGMT_PORTS: return "IOT_MANAGEMENT"
    if p in WEB_PORTS:      return "WEB_SERVICES"
    if p in NET_CORE_PORTS: return "NETWORK_CORE"
    if p in REMOTE_PORTS:   return "REMOTE_ACCESS"
    if p > 49152:           return "FUNC_EPHEMERAL"
    return "FUNC_UNKNOWN"

# ── 3F: HTTP Method OHE (8 dims) — raw DNA from TON-IoT ─────────────────────
HTTP_METHOD_TOKENS = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH", "OTHER"]
HTTP_METHOD_IDX    = {t: i for i, t in enumerate(HTTP_METHOD_TOKENS)}

# ── 3G: SSL Cipher OHE (12 dims) — raw DNA from TON-IoT ssl_cipher ───────────
# Top 11 cipher suites observed in IoT/industrial traffic + "other"
SSL_CIPHER_TOKENS = [
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",          # 0
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",          # 1
    "TLS_RSA_WITH_AES_128_GCM_SHA256",                # 2
    "TLS_RSA_WITH_AES_256_GCM_SHA384",                # 3
    "TLS_RSA_WITH_AES_128_CBC_SHA",                   # 4
    "TLS_RSA_WITH_AES_256_CBC_SHA",                   # 5
    "TLS_RSA_WITH_RC4_128_SHA",                       # 6 — weak (IoT legacy)
    "TLS_RSA_WITH_RC4_128_MD5",                       # 7 — weak
    "TLS_RSA_WITH_3DES_EDE_CBC_SHA",                  # 8 — legacy
    "TLS_DHE_RSA_WITH_AES_128_CBC_SHA",               # 9
    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",        # 10
    "other",                                          # 11
]
SSL_CIPHER_IDX = {t: i for i, t in enumerate(SSL_CIPHER_TOKENS)}

# ── 3H: SSL Version OHE (3 dims: weak/strong/absent) ─────────────────────────
# Appended after cipher OHE to complete 15 dims for Block 5 SSL
#   Dim 12: weak  (SSLv2, SSLv3, TLSv1.0, TLSv1.1)
#   Dim 13: strong (TLSv1.2, TLSv1.3)
#   Dim 14: ssl_established flag (0/1)
WEAK_SSL_VERSIONS   = frozenset({"sslv2","sslv3","tlsv1","tlsv10","tlsv1.0","tls1.0"})
STRONG_SSL_VERSIONS = frozenset({"tlsv12","tlsv13","tlsv1.2","tlsv1.3","tls1.2","tls1.3"})

# ── 3I: v5.1 Aligned Schema Output Columns ────────────────────────────────────
V51_OUTPUT_COLUMNS = [
    # Identity + Metadata
    "dataset_source", "meta_src_ip", "meta_dst_ip", "meta_timestamp",
    # Labels
    "ubt_archetype", "univ_specific_attack",
    # Block 1: Core
    "univ_duration", "univ_bytes_in", "univ_bytes_out", "univ_pkts_in", "univ_pkts_out",
    # Block 2: Protocol
    "raw_proto", "raw_service",
    # Block 3: State
    "raw_state_v51",
    # Block 4: Port
    "raw_sport", "raw_dport",
    # Block 5: DNS (raw codes)
    "dns_qtype", "dns_qclass", "dns_rcode",
    # Block 5: HTTP (raw method + status + body — ACTUAL from source, not proxy)
    "raw_http_method", "http_status_code", "http_req_body_len", "http_resp_body_len",
    # Block 5: SSL (raw cipher + version + established — ACTUAL from source)
    "raw_ssl_cipher", "raw_ssl_version", "ssl_established",
    # Block 6: Momentum (14 UNSW window features, -1.0 when absent)
    "mom_mean", "mom_stddev", "mom_sum", "mom_min", "mom_max",
    "mom_rate", "mom_srate", "mom_drate",
    "mom_TnBPSrcIP", "mom_TnBPDstIP",
    "mom_TnP_PSrcIP", "mom_TnP_PDstIP",
    "mom_TnP_PerProto", "mom_TnP_Per_Dport",
    # Mask Bits
    "has_svc", "has_dns", "has_http", "has_ssl", "has_unsw",
]

print(f"✅ UBT Archetypes    ({len(UBT_ARCHETYPES):2d}): {', '.join(UBT_ARCHETYPES)}")
print(f"✅ State tokens      ({len(UBT_STATE_TOKENS):2d}): {', '.join(UBT_STATE_TOKENS)}")
print(f"✅ Proto tokens      ({len(PROTO_TOKENS):2d}): {', '.join(PROTO_TOKENS)}")
print(f"✅ Service tokens    ({len(SERVICE_TOKENS):2d}): {', '.join(SERVICE_TOKENS)}")
print(f"✅ Port functions    ({len(PORT_FUNC_TOKENS):2d}): {', '.join(PORT_FUNC_TOKENS)}")
print(f"✅ HTTP Method OHE   ({len(HTTP_METHOD_TOKENS):2d}): {', '.join(HTTP_METHOD_TOKENS)}")
print(f"✅ SSL Cipher OHE    ({len(SSL_CIPHER_TOKENS):2d}): top-11 ciphers + other")
print(f"✅ SSL Version dims  ( 3): weak / strong / ssl_established")
print(f"✅ Output columns    ({len(V51_OUTPUT_COLUMNS):2d}): v5.1 aligned schema")
print(f"\n🔑 KEY BREAKTHROUGH:")
print(f"   raw_http_method  → actual GET/POST/DELETE etc. from TON-IoT source")
print(f"   raw_ssl_cipher   → actual TLS cipher suite string from TON-IoT source")
print(f"   raw_ssl_version  → actual TLSv1.2 / TLSv1.3 etc. from TON-IoT source")
print(f"   ssl_established  → actual handshake outcome (0/1) from TON-IoT source")

`

**Output:**
`
✅ Group A columns    : 9 universal features per dataset
✅ Total output cols  : 52

─────────────────────────────────────────────────────────────────
Final column manifest:
   1. dataset_source                                        [Group A]
   2. univ_duration                                         [Group A]
   3. univ_src_bytes                                        [Group A]
   4. univ_dst_bytes                                        [Group A]
   5. univ_src_pkts                                         [Group A]
   6. univ_dst_pkts                                         [Group A]
   7. univ_proto                                            [Group A]
   8. univ_state                                            [Group A]
   9. univ_src_port                                         [Group A]
  10. univ_dst_port                                         [Group A]
  11. univ_has_src_port                                     [Group A]
  12. univ_has_dst_port                                     [Group A]
  13. univ_label_binary                                     [Group A]
  14. univ_label_multiclass                                 [Group A]
  15. univ_label_str                                        [Group A]
  16. univ_specific_attack                                  [Labels/Context]
  17. meta_src_ip                                           [RAG / Metadata]
  18. meta_dst_ip                                           [RAG / Metadata]
  19. meta_timestamp                                        [RAG / Metadata]
  20. zeek_service                                          [Group B / Zeek]
  21. zeek_missed_bytes                                     [Group B / Zeek]
  22. zeek_history                                          [Group B / Zeek]
  23. zeek_src_ip_bytes                                     [Group B / Zeek]
  24. zeek_dst_ip_bytes                                     [Group B / Zeek]
  25. toniot_dns_qclass                                     [Group B / TON-IoT]
  26. toniot_dns_qtype                                      [Group B / TON-IoT]
  27. toniot_dns_rcode                                      [Group B / TON-IoT]
  28. toniot_http_request_body_len                          [Group B / TON-IoT]
  29. toniot_http_response_body_len                         [Group B / TON-IoT]
  30. toniot_http_status_code                               [Group B / TON-IoT]
  31. botiot_mean                                           [Group B / Bot-IoT]
  32. botiot_stddev                                         [Group B / Bot-IoT]
  33. botiot_sum                                            [Group B / Bot-IoT]
  34. botiot_min                                            [Group B / Bot-IoT]
  35. botiot_max                                            [Group B / Bot-IoT]
  36. botiot_rate                                           [Group B / Bot-IoT]
  37. botiot_srate                                          [Group B / Bot-IoT]
  38. botiot_drate                                          [Group B / Bot-IoT]
  39. botiot_TnBPSrcIP                                      [Group B / Bot-IoT]
  40. botiot_TnBPDstIP                                      [Group B / Bot-IoT]
  41. botiot_TnP_PSrcIP                                     [Group B / Bot-IoT]
  42. botiot_TnP_PDstIP                                     [Group B / Bot-IoT]
  43. botiot_TnP_PerProto                                   [Group B / Bot-IoT]
  44. botiot_TnP_Per_Dport                                  [Group B / Bot-IoT]
  45. botiot_AR_P_Proto_P_SrcIP                             [Group B / Bot-IoT]
  46. botiot_AR_P_Proto_P_DstIP                             [Group B / Bot-IoT]
  47. botiot_N_IN_Conn_P_DstIP                              [Group B / Bot-IoT]
  48. botiot_N_IN_Conn_P_SrcIP                              [Group B / Bot-IoT]
  49. botiot_AR_P_Proto_P_Sport                             [Group B / Bot-IoT]
  50. botiot_AR_P_Proto_P_Dport                             [Group B / Bot-IoT]
  51. botiot_Pkts_P_State_P_Protocol_P_DestIP               [Group B / Bot-IoT]
  52. botiot_Pkts_P_State_P_Protocol_P_SrcIP                [Group B / Bot-IoT]
`

---
## Section 2 — Evidence Sensor Logic (5 Mask Bits)

Mask bits are derived from feature existence, **not** dataset source.
Each bit gates an entire block — if bit = 0, the block is zeroed in Phase 1.2.


### Cell 4

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 4 | Evidence Sensor Logic — 5 Mask Bits (using Raw Column Names)
# ─────────────────────────────────────────────────────────────────────────────
#
# Mask bits are derived from feature EXISTENCE in the RAW source,
# not inferred from downstream proxies.
#
# Raw column names (as they appear in source CSVs/logs):
#   TON-IoT  : service, dns_qtype, http_method, http_status_code,
#              ssl_cipher, ssl_version, ssl_established
#   IoT-23   : service  (conn.log.labeled — no app-layer columns)
#   Bot-IoT  : proto, state, TnBPSrcIP (14 window cols)
#
# ── Sentinel values used in raw files ────────────────────────────────────────
RAW_ABSENT = frozenset({"-", "(empty)", "", "none", "nan", "<absent>"})

HTTP_DETECT_DPORTS = frozenset({80, 443, 8080})


def _raw_is_absent(val) -> bool:
    """Return True if a raw string value is a missing/sentinel value."""
    return str(val).strip().lower() in RAW_ABSENT


def compute_mask_bits_raw(
    service_col,      # pd.Series: raw 'service' column
    dns_qtype_col,    # pd.Series or None
    http_method_col,  # pd.Series or None
    http_status_col,  # pd.Series or None
    ssl_cipher_col,   # pd.Series or None
    ssl_version_col,  # pd.Series or None
    dport_col,        # pd.Series or None
    unsw_col,         # pd.Series or None  (TnBPSrcIP)
    n: int,
    index,
) -> dict:
    """
    Compute all 5 mask bits from raw source column Series.
    Returns dict of 5 int8 Series.
    """
    svc = service_col.fillna("-").astype(str).str.lower().str.strip()

    # ── has_svc ───────────────────────────────────────────────────────────────
    has_svc = (~svc.isin(RAW_ABSENT)).astype("int8")

    # ── has_dns ───────────────────────────────────────────────────────────────
    dns_from_svc = (svc == "dns")
    if dns_qtype_col is not None:
        dns_from_qtype = ~dns_qtype_col.fillna("-").astype(str).str.strip().str.lower().isin(RAW_ABSENT)
    else:
        dns_from_qtype = pd.Series(False, index=index)
    has_dns = (dns_from_svc | dns_from_qtype).astype("int8")

    # ── has_http ──────────────────────────────────────────────────────────────
    http_from_svc  = svc.isin({"http", "ssl"})  # ssl port 443 is often HTTP/2
    if http_method_col is not None:
        http_from_method = ~http_method_col.fillna("-").astype(str).str.strip().str.lower().isin(RAW_ABSENT)
    else:
        http_from_method = pd.Series(False, index=index)
    if http_status_col is not None:
        http_from_status = ~http_status_col.fillna("-").astype(str).str.strip().str.lower().isin(RAW_ABSENT)
    else:
        http_from_status = pd.Series(False, index=index)
    if dport_col is not None:
        dport_num        = pd.to_numeric(dport_col, errors="coerce").fillna(-1).astype(int)
        http_from_dport  = dport_num.isin(HTTP_DETECT_DPORTS)
    else:
        http_from_dport  = pd.Series(False, index=index)
    has_http = (http_from_svc | http_from_method | http_from_status | http_from_dport).astype("int8")

    # ── has_ssl ───────────────────────────────────────────────────────────────
    ssl_from_svc = (svc == "ssl")
    if ssl_cipher_col is not None:
        ssl_from_cipher = ~ssl_cipher_col.fillna("-").astype(str).str.strip().str.lower().isin(RAW_ABSENT)
    else:
        ssl_from_cipher = pd.Series(False, index=index)
    if ssl_version_col is not None:
        ssl_from_version = ~ssl_version_col.fillna("-").astype(str).str.strip().str.lower().isin(RAW_ABSENT)
    else:
        ssl_from_version = pd.Series(False, index=index)
    has_ssl = (ssl_from_svc | ssl_from_cipher | ssl_from_version).astype("int8")

    # ── has_unsw ──────────────────────────────────────────────────────────────
    if unsw_col is not None:
        has_unsw = (~unsw_col.fillna(-1).astype(str).str.strip().isin(RAW_ABSENT) & (
            pd.to_numeric(unsw_col, errors="coerce").fillna(-1) >= 0
        )).astype("int8")
    else:
        has_unsw = pd.Series(np.int8(0), index=index)

    return {
        "has_svc":  has_svc,
        "has_dns":  has_dns,
        "has_http": has_http,
        "has_ssl":  has_ssl,
        "has_unsw": has_unsw,
    }


print("✅ Evidence sensor (raw columns) defined")
print("   has_svc  : service ∉ {-, (empty), ''}")
print("   has_dns  : service=='dns'  OR  dns_qtype is not missing")
print("   has_http : service∈{http,ssl}  OR  http_method present  OR  dport∈{80,443,8080}")
print("             OR  http_status_code present")
print("   has_ssl  : service=='ssl'  OR  ssl_cipher present  OR  ssl_version present")
print("   has_unsw : TnBPSrcIP column present AND >= 0")
print()
print("🔑 KEY: has_ssl and has_http are now based on ACTUAL cipher/method columns")
print("        NOT on port/state proxies — full Resolution restored")

`

**Output:**
`
✅ UNIVERSAL_STATE_MAP   : 24 Zeek/Argus codes → 5 vocab tokens
✅ TONIOT_LABEL_MAP      : 10 type strings → 5 classes
✅ IOT23_LABEL_MAP       : 18 detailed-label strings → 5 classes
✅ BOTIOT_CATEGORY_MAP   : 5 category strings → 5 classes

📋 5-Class Taxonomy:
   Class 0 → Normal
   Class 1 → Reconnaissance
   Class 2 → Volumetric_Attack
   Class 3 → C2_Botnet
   Class 4 → Exploit_and_Theft
`

---
## Section 3 — Chunk Transformation Function

`transform_chunk_to_v51(chunk)` maps any v4 52-column Parquet chunk to the v5.1 aligned schema.
All columns in `V51_OUTPUT_COLUMNS` are produced with the correct dtypes.


### Cell 5

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 5 | Dataset-Specific Chunk Transformers
#          Each function accepts a raw chunk → returns V51_OUTPUT_COLUMNS
# ─────────────────────────────────────────────────────────────────────────────

def _safe_num(series, fill=0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(fill)

def _clean_str(val, fallback="") -> str:
    s = str(val).strip()
    return fallback if s.lower() in RAW_ABSENT else s

def _build_output_frame(index) -> pd.DataFrame:
    """Return empty DataFrame with V51_OUTPUT_COLUMNS, correct types."""
    return pd.DataFrame(index=index)


# ─────────────────────────────────────────────────────────────────────────────
# TON-IoT Transform
# Source columns: ts, src_ip, src_port, dst_ip, dst_port, proto, service,
#   duration, src_bytes, dst_bytes, conn_state, missed_bytes, src_pkts,
#   dst_pkts, src_ip_bytes, dst_ip_bytes,
#   dns_query, dns_qclass, dns_qtype, dns_rcode,
#   ssl_version, ssl_cipher, ssl_resumed, ssl_established, ssl_subject, ssl_issuer,
#   http_trans_depth, http_method, http_uri, http_referrer, http_version,
#   http_request_body_len, http_response_body_len, http_status_code,
#   http_user_agent, http_orig_mime_types, http_resp_mime_types,
#   weird_name, weird_addl, weird_notice,
#   label, type
# ─────────────────────────────────────────────────────────────────────────────
def transform_toniot_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """TON-IoT CSV chunk → v5.1 aligned schema (full HTTP/SSL/DNS resolution)."""
    n   = len(chunk)
    idx = chunk.index
    out = _build_output_frame(idx)

    # ── Identity / Metadata ───────────────────────────────────────────────────
    out["dataset_source"]     = "toniot"
    out["meta_src_ip"]        = chunk.get("src_ip",  pd.Series([""] * n, index=idx)).fillna("").astype(str)
    out["meta_dst_ip"]        = chunk.get("dst_ip",  pd.Series([""] * n, index=idx)).fillna("").astype(str)
    out["meta_timestamp"]     = _safe_num(chunk.get("ts", pd.Series(0.0, index=idx)), fill=0.0)

    # ── UBT label from 'type' (attack subtype) ────────────────────────────────
    attack_type = chunk.get("type", pd.Series(["normal"] * n, index=idx)).fillna("normal").astype(str)
    label_bin   = chunk.get("label", pd.Series([0] * n, index=idx)).fillna(0)
    # If label==0 (binary normal), force NORMAL regardless of type
    ubt_list = []
    for raw_type, lb in zip(attack_type, label_bin):
        if str(lb).strip() in {"0", "normal", "Normal"}:
            ubt_list.append("NORMAL")
        else:
            ubt_list.append(map_to_ubt(raw_type))
    out["ubt_archetype"]      = ubt_list
    out["univ_specific_attack"] = attack_type.astype(str)

    # ── Block 1: Core ─────────────────────────────────────────────────────────
    out["univ_duration"]  = _safe_num(chunk.get("duration",  pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_bytes_in"]  = _safe_num(chunk.get("src_bytes", pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_bytes_out"] = _safe_num(chunk.get("dst_bytes", pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_pkts_in"]   = _safe_num(chunk.get("src_pkts",  pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_pkts_out"]  = _safe_num(chunk.get("dst_pkts",  pd.Series(0.0, index=idx))).clip(lower=0)

    # ── Block 2: Protocol ─────────────────────────────────────────────────────
    valid_protos = frozenset(PROTO_TOKENS) - {"other"}
    raw_proto = chunk.get("proto", pd.Series(["other"] * n, index=idx)).fillna("other").astype(str).str.lower().str.strip()
    out["raw_proto"]   = raw_proto.apply(lambda p: p if p in valid_protos else "other")
    raw_svc   = chunk.get("service", pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.lower().str.strip()
    out["raw_service"] = raw_svc.apply(
        lambda s: (s if s not in RAW_ABSENT and s in SERVICE_SET else
                   ("other" if s not in RAW_ABSENT else "<absent>"))
    )

    # ── Block 3: State ────────────────────────────────────────────────────────
    conn_state = chunk.get("conn_state", pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.strip()
    out["raw_state_v51"] = conn_state.map(STATE_V51_MAP).fillna("OTHER")

    # ── Block 4: Ports ────────────────────────────────────────────────────────
    out["raw_sport"] = _safe_num(chunk.get("src_port", pd.Series(-1, index=idx)), fill=-1).astype(int)
    out["raw_dport"] = _safe_num(chunk.get("dst_port", pd.Series(-1, index=idx)), fill=-1).astype(int)

    # ── Block 5: DNS — ACTUAL FROM SOURCE ────────────────────────────────────
    out["dns_qtype"]  = _safe_num(chunk.get("dns_qtype",  pd.Series(-1, index=idx)), fill=-1).astype(int)
    out["dns_qclass"] = _safe_num(chunk.get("dns_qclass", pd.Series(-1, index=idx)), fill=-1).astype(int)
    out["dns_rcode"]  = _safe_num(chunk.get("dns_rcode",  pd.Series(-1, index=idx)), fill=-1).astype(int)

    # ── Block 5: HTTP — ACTUAL FROM SOURCE (raw http_method preserved) ────────
    raw_http_method = chunk.get("http_method", pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.strip().str.upper()
    out["raw_http_method"]    = raw_http_method.apply(lambda m: m if m not in {"-","", "(EMPTY)", "NAN"} else "-")
    out["http_status_code"]   = _safe_num(chunk.get("http_status_code",        pd.Series(-1, index=idx)), fill=-1).astype(int)
    out["http_req_body_len"]  = _safe_num(chunk.get("http_request_body_len",   pd.Series(-1, index=idx)), fill=-1).astype(int)
    out["http_resp_body_len"] = _safe_num(chunk.get("http_response_body_len",  pd.Series(-1, index=idx)), fill=-1).astype(int)

    # ── Block 5: SSL — ACTUAL FROM SOURCE (raw ssl_cipher, ssl_version) ───────
    raw_ssl_cipher  = chunk.get("ssl_cipher",      pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.strip()
    raw_ssl_version = chunk.get("ssl_version",     pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.strip()
    ssl_estab_raw   = chunk.get("ssl_established", pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.lower().str.strip()
    out["raw_ssl_cipher"]  = raw_ssl_cipher
    out["raw_ssl_version"] = raw_ssl_version
    out["ssl_established"] = ssl_estab_raw.map({"t": 1, "true": 1, "1": 1, "f": 0, "false": 0, "0": 0}).fillna(0).astype("int8")

    # ── Block 6: Momentum — all absent for TON-IoT ────────────────────────────
    mom_cols = ["mom_mean","mom_stddev","mom_sum","mom_min","mom_max","mom_rate",
                "mom_srate","mom_drate","mom_TnBPSrcIP","mom_TnBPDstIP",
                "mom_TnP_PSrcIP","mom_TnP_PDstIP","mom_TnP_PerProto","mom_TnP_Per_Dport"]
    for col in mom_cols:
        out[col] = -1.0

    # ── Mask bits (using raw columns) ─────────────────────────────────────────
    masks = compute_mask_bits_raw(
        service_col     = chunk.get("service",         pd.Series(["-"] * n, index=idx)),
        dns_qtype_col   = chunk.get("dns_qtype",       None),
        http_method_col = chunk.get("http_method",     None),
        http_status_col = chunk.get("http_status_code",None),
        ssl_cipher_col  = chunk.get("ssl_cipher",      None),
        ssl_version_col = chunk.get("ssl_version",     None),
        dport_col       = chunk.get("dst_port",        None),
        unsw_col        = None,
        n=n, index=idx,
    )
    for k, v in masks.items():
        out[k] = v

    return out[V51_OUTPUT_COLUMNS]


# ─────────────────────────────────────────────────────────────────────────────
# IoT-23 Transform
# Source columns: ts, uid, id.orig_h, id.orig_p, id.resp_h, id.resp_p,
#   proto, service, duration, orig_bytes, resp_bytes, conn_state,
#   local_orig, local_resp, missed_bytes, history, orig_pkts, orig_ip_bytes,
#   resp_pkts, resp_ip_bytes, tunnel_parents, label, detailed-label
# ─────────────────────────────────────────────────────────────────────────────
def transform_iot23_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """IoT-23 Zeek conn.log chunk → v5.1 aligned schema."""
    n   = len(chunk)
    idx = chunk.index
    out = _build_output_frame(idx)

    # ── Identity / Metadata ───────────────────────────────────────────────────
    out["dataset_source"] = "iot23"
    out["meta_src_ip"]    = chunk.get("id.orig_h", pd.Series([""] * n, index=idx)).fillna("").astype(str)
    out["meta_dst_ip"]    = chunk.get("id.resp_h", pd.Series([""] * n, index=idx)).fillna("").astype(str)
    out["meta_timestamp"] = _safe_num(chunk.get("ts", pd.Series(0.0, index=idx)), fill=0.0)

    # ── UBT label from 'detailed-label' ──────────────────────────────────────
    det_label  = chunk.get("detailed-label", pd.Series(["-"] * n, index=idx)).fillna("-").astype(str)
    label_col  = chunk.get("label", pd.Series(["benign"] * n, index=idx)).fillna("benign").astype(str)
    ubt_list = [map_to_ubt(dl) for dl in det_label]
    out["ubt_archetype"]        = ubt_list
    out["univ_specific_attack"] = det_label.astype(str)

    # ── Block 1: Core ─────────────────────────────────────────────────────────
    out["univ_duration"]  = _safe_num(chunk.get("duration",   pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_bytes_in"]  = _safe_num(chunk.get("orig_bytes", pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_bytes_out"] = _safe_num(chunk.get("resp_bytes", pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_pkts_in"]   = _safe_num(chunk.get("orig_pkts",  pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_pkts_out"]  = _safe_num(chunk.get("resp_pkts",  pd.Series(0.0, index=idx))).clip(lower=0)

    # ── Block 2: Protocol ─────────────────────────────────────────────────────
    valid_protos = frozenset(PROTO_TOKENS) - {"other"}
    raw_proto = chunk.get("proto", pd.Series(["other"] * n, index=idx)).fillna("other").astype(str).str.lower().str.strip()
    out["raw_proto"] = raw_proto.apply(lambda p: p if p in valid_protos else "other")
    raw_svc = chunk.get("service", pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.lower().str.strip()
    out["raw_service"] = raw_svc.apply(
        lambda s: (s if s not in RAW_ABSENT and s in SERVICE_SET else
                   ("other" if s not in RAW_ABSENT else "<absent>"))
    )

    # ── Block 3: State ────────────────────────────────────────────────────────
    conn_state = chunk.get("conn_state", pd.Series(["-"] * n, index=idx)).fillna("-").astype(str).str.strip()
    out["raw_state_v51"] = conn_state.map(STATE_V51_MAP).fillna("OTHER")

    # ── Block 4: Ports ────────────────────────────────────────────────────────
    out["raw_sport"] = _safe_num(chunk.get("id.orig_p", pd.Series(-1, index=idx)), fill=-1).astype(int)
    out["raw_dport"] = _safe_num(chunk.get("id.resp_p", pd.Series(-1, index=idx)), fill=-1).astype(int)

    # ── Block 5: No app-layer columns in IoT-23 conn.log ─────────────────────
    out["dns_qtype"]          = -1
    out["dns_qclass"]         = -1
    out["dns_rcode"]          = -1
    out["raw_http_method"]    = "-"
    out["http_status_code"]   = -1
    out["http_req_body_len"]  = -1
    out["http_resp_body_len"] = -1
    out["raw_ssl_cipher"]     = "-"
    out["raw_ssl_version"]    = "-"
    out["ssl_established"]    = np.int8(0)

    # ── Block 6: Momentum — absent for IoT-23 ─────────────────────────────────
    for col in ["mom_mean","mom_stddev","mom_sum","mom_min","mom_max","mom_rate",
                "mom_srate","mom_drate","mom_TnBPSrcIP","mom_TnBPDstIP",
                "mom_TnP_PSrcIP","mom_TnP_PDstIP","mom_TnP_PerProto","mom_TnP_Per_Dport"]:
        out[col] = -1.0

    # ── Mask bits ─────────────────────────────────────────────────────────────
    masks = compute_mask_bits_raw(
        service_col     = chunk.get("service",    pd.Series(["-"] * n, index=idx)),
        dns_qtype_col   = None,
        http_method_col = None,
        http_status_col = None,
        ssl_cipher_col  = None,
        ssl_version_col = None,
        dport_col       = chunk.get("id.resp_p",  None),
        unsw_col        = None,
        n=n, index=idx,
    )
    for k, v in masks.items():
        out[k] = v

    return out[V51_OUTPUT_COLUMNS]


# ─────────────────────────────────────────────────────────────────────────────
# Bot-IoT Transform
# Source columns: stime, saddr, sport, daddr, dport, proto, state, dur,
#   sbytes, dbytes, spkts, dpkts,
#   mean, stddev, sum, min, max, rate, srate, drate,
#   TnBPSrcIP, TnBPDstIP, TnP_PSrcIP, TnP_PDstIP, TnP_PerProto, TnP_Per_Dport,
#   AR_P_Proto_P_SrcIP, AR_P_Proto_P_DstIP, N_IN_Conn_P_DstIP, N_IN_Conn_P_SrcIP,
#   AR_P_Proto_P_Sport, AR_P_Proto_P_Dport,
#   Pkts_P_State_P_Protocol_P_DestIP, Pkts_P_State_P_Protocol_P_SrcIP,
#   attack, category, subcategory
# ─────────────────────────────────────────────────────────────────────────────

# Argus state → v5.1 mapping
BOTIOT_STATE_MAP = {
    "ACC": "ESTABLISHED", "CON": "ESTABLISHED", "FIN": "ESTABLISHED",
    "CLO": "ESTABLISHED", "ECO": "ESTABLISHED",
    "RST": "RESET",       "TXW": "RESET",
    "URH": "PENDING",     "REQ": "PENDING",     "INT": "PENDING",
    "-":   "OTHER",       "":    "OTHER",        "other": "OTHER",
}

MOM_BOTIOT_MAP = {
    "mom_mean":          "mean",
    "mom_stddev":        "stddev",
    "mom_sum":           "sum",
    "mom_min":           "min",
    "mom_max":           "max",
    "mom_rate":          "rate",
    "mom_srate":         "srate",
    "mom_drate":         "drate",
    "mom_TnBPSrcIP":     "TnBPSrcIP",
    "mom_TnBPDstIP":     "TnBPDstIP",
    "mom_TnP_PSrcIP":    "TnP_PSrcIP",
    "mom_TnP_PDstIP":    "TnP_PDstIP",
    "mom_TnP_PerProto":  "TnP_PerProto",
    "mom_TnP_Per_Dport": "TnP_Per_Dport",
}


def transform_botiot_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Bot-IoT CSV chunk → v5.1 aligned schema (full momentum resolution)."""
    n   = len(chunk)
    idx = chunk.index
    out = _build_output_frame(idx)

    # ── Identity / Metadata ───────────────────────────────────────────────────
    out["dataset_source"] = "botiot"
    out["meta_src_ip"]    = chunk.get("saddr", pd.Series([""] * n, index=idx)).fillna("").astype(str)
    out["meta_dst_ip"]    = chunk.get("daddr", pd.Series([""] * n, index=idx)).fillna("").astype(str)
    out["meta_timestamp"] = _safe_num(chunk.get("stime", pd.Series(0.0, index=idx)), fill=0.0)

    # ── UBT label from category + subcategory ────────────────────────────────
    category   = chunk.get("category",    pd.Series(["Normal"] * n, index=idx)).fillna("Normal").astype(str)
    subcategory= chunk.get("subcategory", pd.Series([""] * n, index=idx)).fillna("").astype(str)
    attack_bin = chunk.get("attack",      pd.Series([0] * n, index=idx)).fillna(0)

    ubt_list = []
    for cat, sub, ab in zip(category, subcategory, attack_bin):
        if str(ab).strip() in {"0", "0.0"}:
            ubt_list.append("NORMAL")
        else:
            # Try subcategory first for finer discrimination, fall back to category
            ubt = map_to_ubt(sub)
            if ubt == "ANOMALY":
                ubt = map_to_ubt(cat)
            ubt_list.append(ubt)

    out["ubt_archetype"]        = ubt_list
    out["univ_specific_attack"] = subcategory.astype(str)

    # ── Block 1: Core ─────────────────────────────────────────────────────────
    out["univ_duration"]  = _safe_num(chunk.get("dur",    pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_bytes_in"]  = _safe_num(chunk.get("sbytes", pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_bytes_out"] = _safe_num(chunk.get("dbytes", pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_pkts_in"]   = _safe_num(chunk.get("spkts",  pd.Series(0.0, index=idx))).clip(lower=0)
    out["univ_pkts_out"]  = _safe_num(chunk.get("dpkts",  pd.Series(0.0, index=idx))).clip(lower=0)

    # ── Block 2: Protocol ─────────────────────────────────────────────────────
    valid_protos = frozenset(PROTO_TOKENS) - {"other"}
    raw_proto = chunk.get("proto", pd.Series(["other"] * n, index=idx)).fillna("other").astype(str).str.lower().str.strip()
    out["raw_proto"]   = raw_proto.apply(lambda p: p if p in valid_protos else "other")
    out["raw_service"] = "<absent>"   # Bot-IoT has no service column

    # ── Block 3: State ────────────────────────────────────────────────────────
    state_raw = chunk.get("state", pd.Series(["INT"] * n, index=idx)).fillna("INT").astype(str).str.strip()
    out["raw_state_v51"] = state_raw.map(BOTIOT_STATE_MAP).fillna("OTHER")

    # ── Block 4: Ports ────────────────────────────────────────────────────────
    out["raw_sport"] = _safe_num(chunk.get("sport", pd.Series(-1, index=idx)), fill=-1).astype(int)
    out["raw_dport"] = _safe_num(chunk.get("dport", pd.Series(-1, index=idx)), fill=-1).astype(int)

    # ── Block 5: No app-layer columns in Bot-IoT ──────────────────────────────
    out["dns_qtype"]          = -1
    out["dns_qclass"]         = -1
    out["dns_rcode"]          = -1
    out["raw_http_method"]    = "-"
    out["http_status_code"]   = -1
    out["http_req_body_len"]  = -1
    out["http_resp_body_len"] = -1
    out["raw_ssl_cipher"]     = "-"
    out["raw_ssl_version"]    = "-"
    out["ssl_established"]    = np.int8(0)

    # ── Block 6: Momentum — ACTUAL 14 UNSW window features ────────────────────
    for out_col, src_col in MOM_BOTIOT_MAP.items():
        if src_col in chunk.columns:
            out[out_col] = _safe_num(chunk[src_col], fill=-1.0)
        else:
            out[out_col] = -1.0

    # ── Mask bits ─────────────────────────────────────────────────────────────
    unsw_col = chunk.get("TnBPSrcIP", None)
    masks = compute_mask_bits_raw(
        service_col     = pd.Series(["-"] * n, index=idx),
        dns_qtype_col   = None,
        http_method_col = None,
        http_status_col = None,
        ssl_cipher_col  = None,
        ssl_version_col = None,
        dport_col       = chunk.get("dport", None),
        unsw_col        = unsw_col,
        n=n, index=idx,
    )
    for k, v in masks.items():
        out[k] = v

    return out[V51_OUTPUT_COLUMNS]


print("✅ Dataset-specific chunk transformers defined:")
print("   transform_toniot_chunk() — TON-IoT CSVs")
print("     ↳ Raw DNA: http_method, ssl_cipher, ssl_version, ssl_established, dns_qtype")
print("   transform_iot23_chunk()  — IoT-23 Zeek conn.log.labeled")
print("     ↳ Raw DNA: detailed-label for UBT mapping (no app-layer cols in conn.log)")
print("   transform_botiot_chunk() — Bot-IoT CSVs")
print("     ↳ Raw DNA: 14 UNSW momentum window features (all present)")

`

**Output:**
`
✅ Utility functions defined:
   safe_int(), safe_float(), normalize_proto(), map_state()
   handle_port()  ← hex-aware (handles 0x0303 style Bot-IoT ports)
   map_label_multiclass()
   inject_group_b_sentinels(), reorder_and_validate()
`

### Cell 6

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 6 | Raw-Source Streaming Pipeline
# ─────────────────────────────────────────────────────────────────────────────
import io

CHUNK_SIZE   = 200_000
UBT_MAX_ROWS = 1_000_000   # cap so notebook finishes in reasonable time

# ── IoT-23 Zeek TSV Reader ─────────────────────────────────────────────────
def read_zeek_labeled(filepath: Path) -> pd.DataFrame | None:
    """
    Read a Zeek conn.log.labeled file into a DataFrame.
    - Header lines start with '#'
    - Column names are in the '#fields' line
    - Separator announced in '#separator' line (commonly '\t' or ',')
    """
    sep = "\t"          # Zeek default; overridden if #separator says otherwise
    cols = None

    # First pass: extract metadata
    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith("#separator"):
                raw_sep = line.split(None, 1)[1] if " " in line else "\t"
                # Zeek encodes \t literally as "\\x09"
                if raw_sep.startswith("\\x"):
                    sep = bytes.fromhex(raw_sep[2:]).decode()
                else:
                    sep = raw_sep
            elif line.startswith("#set_separator"):
                # e.g. "#set_separator ,\n"  — used between multiple values in a field
                pass
            elif line.startswith("#fields"):
                cols = line[len("#fields"):].strip().split(sep)
            if cols and not line.startswith("#"):
                break

    if cols is None:
        print(f"  ⚠  No #fields line found in {filepath.name} — skipping")
        return None

    # Second pass: read data rows (skip comment lines)
    try:
        df = pd.read_csv(
            filepath,
            sep=sep,
            names=cols,
            comment="#",
            header=None,
            low_memory=False,
            encoding="utf-8",
            on_bad_lines="warn",
        )
    except Exception as exc:
        print(f"  ⚠  Failed to read {filepath.name}: {exc}")
        return None

    if df.empty:
        return None
    return df


# ── Streaming Pipeline ─────────────────────────────────────────────────────
def stream_raw_all_to_v51() -> pd.DataFrame:
    """
    Read all three raw dataset sources, transform each chunk to v5.1, and
    concatenate up to UBT_MAX_ROWS total rows.
    """
    all_parts = []
    total_rows = 0

    # ────────────────────── TON-IoT (23 CSVs) ────────────────────────────────
    print(f"\n[1/3] TON-IoT — reading {len(toniot_files)} raw CSVs")
    for fp in toniot_files:
        if total_rows >= UBT_MAX_ROWS:
            break
        print(f"  ↳ {fp.name}", end="", flush=True)
        file_rows = 0
        try:
            for chunk in pd.read_csv(fp, chunksize=CHUNK_SIZE, low_memory=False,
                                     encoding="utf-8", on_bad_lines="warn"):
                if total_rows >= UBT_MAX_ROWS:
                    break
                needed = UBT_MAX_ROWS - total_rows
                if len(chunk) > needed:
                    chunk = chunk.iloc[:needed]
                part = transform_toniot_chunk(chunk)
                all_parts.append(part)
                total_rows += len(part)
                file_rows  += len(part)
        except Exception as exc:
            print(f" ⚠ {exc}")
            continue
        print(f"  +{file_rows:,} rows  [total={total_rows:,}]")

    # ────────────────────── IoT-23 (Zeek conn.log.labeled) ───────────────────
    print(f"\n[2/3] IoT-23 — reading {len(iot23_logs)} Zeek logs")
    for fp in iot23_logs:
        if total_rows >= UBT_MAX_ROWS:
            break
        print(f"  ↳ {fp.parent.name}/{fp.name}", end="", flush=True)
        df = read_zeek_labeled(fp)
        if df is None or df.empty:
            print("  (empty/skipped)")
            continue
        file_rows = 0
        # Process in chunks
        for start in range(0, len(df), CHUNK_SIZE):
            if total_rows >= UBT_MAX_ROWS:
                break
            chunk = df.iloc[start : start + CHUNK_SIZE].copy()
            needed = UBT_MAX_ROWS - total_rows
            if len(chunk) > needed:
                chunk = chunk.iloc[:needed]
            part = transform_iot23_chunk(chunk)
            all_parts.append(part)
            total_rows += len(part)
            file_rows  += len(part)
        print(f"  +{file_rows:,} rows  [total={total_rows:,}]")

    # ────────────────────── Bot-IoT (4 CSVs) ─────────────────────────────────
    print(f"\n[3/3] Bot-IoT — reading {len(botiot_files)} raw CSVs")
    for fp in botiot_files:
        if total_rows >= UBT_MAX_ROWS:
            break
        print(f"  ↳ {fp.name}", end="", flush=True)
        file_rows = 0
        try:
            for chunk in pd.read_csv(fp, chunksize=CHUNK_SIZE, low_memory=False,
                                     encoding="utf-8", on_bad_lines="warn"):
                if total_rows >= UBT_MAX_ROWS:
                    break
                needed = UBT_MAX_ROWS - total_rows
                if len(chunk) > needed:
                    chunk = chunk.iloc[:needed]
                part = transform_botiot_chunk(chunk)
                all_parts.append(part)
                total_rows += len(part)
                file_rows  += len(part)
        except Exception as exc:
            print(f" ⚠ {exc}")
            continue
        print(f"  +{file_rows:,} rows  [total={total_rows:,}]")

    if not all_parts:
        raise RuntimeError("❌ No data produced — check raw data paths in Cell 2")

    print(f"\nConcatenating {len(all_parts)} chunks…")
    df_unified = pd.concat(all_parts, ignore_index=True)
    print(f"✅ Unified raw frame: {df_unified.shape[0]:,} rows × {df_unified.shape[1]} cols")
    return df_unified


# ── Run label diagnostics before pipeline ──────────────────────────────────
print("📁 Raw source file counts:")
print(f"   TON-IoT:  {len(toniot_files)} CSVs")
print(f"   IoT-23:   {len(iot23_logs)} Zeek logs")
print(f"   Bot-IoT:  {len(botiot_files)} CSVs")
print(f"\n⚙  Row cap: {UBT_MAX_ROWS:,}  |  Chunk size: {CHUNK_SIZE:,}")
print("   Run the NEXT cell to execute the pipeline.")

`

**Output:**
`
✅ transform_toniot_chunk() defined
✅ transform_iot23_chunk() defined
✅ transform_botiot_chunk() defined
`

### Cell 7

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 7 | Execute Pipeline
# ─────────────────────────────────────────────────────────────────────────────
print(f"🚀 Starting Phase 1.1 v5.1 — Universal Schema Alignment")
print(f"   Schema  : {SCHEMA_VERSION}  |  {TOTAL_DIMS} dimensions")
print(f"   Chunk   : {CHUNK_SIZE:,} rows")
print(f"   Output  : {ALIGNED_V51_PARQUET}")
print()

pipeline_summary = stream_all_to_v51(
    output_path=ALIGNED_V51_PARQUET,
    chunk_size=CHUNK_SIZE,
)

print(f"\n📊 Pipeline Summary:")
total_check = 0
for ds, rows in pipeline_summary.items():
    print(f"   {ds:<10}  {rows:>12,} rows")
    total_check += rows
print(f"   {'TOTAL':<10}  {total_check:>12,} rows")

`

**Output:**
`
✅ stream_to_parquet() helper defined
   CHUNK_SIZE = 100,000 rows
`

---
## Section 4 — Validation

Verify the aligned schema output: row counts, column completeness, mask distributions, UBT taxonomy.


### Cell 8

`python
# ─────────────────────────────────────────────────────────────────────────────
# CELL 8 | Validation Report
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 68)
print("  Phase 1.1 v5.1 — Validation Report")
print("=" * 68)

if not ALIGNED_V51_PARQUET.exists():
    raise FileNotFoundError(f"Output not found: {ALIGNED_V51_PARQUET}")

pf       = pq.ParquetFile(str(ALIGNED_V51_PARQUET))
meta     = pf.metadata
n_rows   = meta.num_rows
n_cols   = meta.num_columns
mb       = ALIGNED_V51_PARQUET.stat().st_size / 1e6

print(f"\n📦 File: {ALIGNED_V51_PARQUET.name}")
print(f"   Rows      : {n_rows:>12,}")
print(f"   Columns   : {n_cols:>3d}  (expected: {len(V51_OUTPUT_COLUMNS)})")
print(f"   Size      : {mb:>8,.1f} MB")

# ── Column completeness check ─────────────────────────────────────────────────
actual_cols = [meta.row_group(0).column(i).path_in_schema for i in range(n_cols)]
missing = [c for c in V51_OUTPUT_COLUMNS if c not in actual_cols]
extra   = [c for c in actual_cols if c not in V51_OUTPUT_COLUMNS]
if missing:
    print(f"\n⚠️  MISSING columns: {missing}")
else:
    print(f"\n✅ All {len(V51_OUTPUT_COLUMNS)} schema columns present")
if extra:
    print(f"   Extra columns (not in spec): {extra}")

# ── Sample the first batch for distribution checks ────────────────────────────
sample = pf.read_row_group(0).to_pandas()

print(f"\n📊 UBT Archetype Distribution (first row-group, n={len(sample):,}):")
if "ubt_archetype" in sample.columns:
    ubt_counts = sample["ubt_archetype"].value_counts()
    total_s    = len(sample)
    for archetype in UBT_ARCHETYPES:
        cnt = ubt_counts.get(archetype, 0)
        pct = 100 * cnt / total_s if total_s else 0
        bar = "█" * int(pct / 2)
        flag = " ← ZERO" if cnt == 0 else ""
        print(f"   {archetype:<14}  {cnt:>8,}  ({pct:>5.1f}%)  {bar}{flag}")
else:
    print("   ⚠️  ubt_archetype column not found")

print(f"\n📊 Mask Bit Frequencies (first row-group):")
mask_cols = ["has_svc", "has_dns", "has_http", "has_ssl", "has_unsw"]
BLOCK_DIMS = {"has_svc": 12, "has_dns": 15, "has_http": 21, "has_ssl": 15, "has_unsw": 14}
for mc in mask_cols:
    if mc in sample.columns:
        rate = 100 * sample[mc].mean()
        block_note = f"  → gates {BLOCK_DIMS[mc]:2d} dims"
        print(f"   {mc:<12} : {rate:>6.1f}% = 1{block_note}")
    else:
        print(f"   {mc:<12} : ⚠️  not found")

print(f"\n📊 Dataset Source Distribution (first row-group):")
if "dataset_source" in sample.columns:
    for ds, cnt in sample["dataset_source"].value_counts().items():
        print(f"   {ds:<10}  {cnt:>8,}  ({100*cnt/len(sample):.1f}%)")

print(f"\n✅ Phase 1.1 v5.1 — aligned_schema_v5.parquet ready for Phase 1.2")

`

**Output:**
`
Found 23 TON-IoT files
   ⚠️  Cannot delete locked file — will write to .tmp and rename instead.

=================================================================
🚀 Processing TON-IoT  (23 files)
   → Output: toniot_aligned.parquet
=================================================================
  [ 1/23] Network_dataset_1.csv                                1,000,000 rows
  [ 2/23] Network_dataset_10.csv                               1,000,000 rows
  [ 3/23] Network_dataset_11.csv                               1,000,000 rows
  [ 4/23] Network_dataset_12.csv                               1,000,000 rows
  [ 5/23] Network_dataset_13.csv                               1,000,000 rows
  [ 6/23] Network_dataset_14.csv                               1,000,000 rows
  [ 7/23] Network_dataset_15.csv                               1,000,000 rows
  [ 8/23] Network_dataset_16.csv                               1,000,000 rows
  [ 9/23] Network_dataset_17.csv                               1,000,000 rows
  [10/23] Network_dataset_18.csv                               1,000,000 rows
  [11/23] Network_dataset_19.csv                               1,000,000 rows
  [12/23] Network_dataset_2.csv                                1,000,000 rows
  [13/23] Network_dataset_20.csv                               1,000,000 rows
  [14/23] Network_dataset_21.csv                               1,000,000 rows
  [15/23] Network_dataset_22.csv                               1,000,000 rows
  [16/23] Network_dataset_23.csv                                 339,021 rows
  [17/23] Network_dataset_3.csv                                1,000,000 rows
  [18/23] Network_dataset_4.csv                                1,000,000 rows
  [19/23] Network_dataset_5.csv                                1,000,000 rows
  [20/23] Network_dataset_6.csv                                1,000,000 rows
  [21/23] Network_dataset_7.csv                                1,000,000 rows
  [22/23] Network_dataset_8.csv                                1,000,000 rows
  [23/23] Network_dataset_9.csv                                1,000,000 rows
[ERROR] PermissionError: [WinError 5] Access is denied: 'c:\\Users\\suhas\\OneDrive\\Desktop\\Capstone\\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\\main_folder\\data\\unified\\toniot_aligned.parquet.tmp' -> 'c:\\Users\\suhas\\OneDrive\\Desktop\\Capstone\\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\\main_folder\\data\\unified\\toniot_aligned.parquet'
`

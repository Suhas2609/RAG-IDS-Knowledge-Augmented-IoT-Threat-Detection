# Phase 0.3 — Bot-IoT Data Understanding Report
**Generated:** Phase 0 Read-Only EDA | Rows sampled: 400,000 (100k/file × 4 files)

## 1. File Inventory
| file                               |   size_mb |
|:-----------------------------------|----------:|
| UNSW_2018_IoT_Botnet_Full5pc_1.csv |     259.7 |
| UNSW_2018_IoT_Botnet_Full5pc_2.csv |     260.4 |
| UNSW_2018_IoT_Botnet_Full5pc_3.csv |     269.1 |
| UNSW_2018_IoT_Botnet_Full5pc_4.csv |     180.8 |

## 2. Dataset Shape
- **Rows (sampled):** 400,000
- **Columns:** 46 (excl. source_file)
- **Memory:** 297.7 MB

## 3. Column Inventory (dtype, null%, unique)
| column                           | dtype   |   null_% |   unique |
|:---------------------------------|:--------|---------:|---------:|
| pkSeqID                          | int64   |        0 |   400000 |
| stime                            | float64 |        0 |    38946 |
| flgs                             | object  |        0 |        6 |
| flgs_number                      | int64   |        0 |        6 |
| proto                            | object  |        0 |        3 |
| proto_number                     | int64   |        0 |        3 |
| saddr                            | object  |        0 |        8 |
| sport                            | int64   |        0 |    65537 |
| daddr                            | object  |        0 |        8 |
| dport                            | int64   |        0 |        2 |
| pkts                             | int64   |        0 |       19 |
| bytes                            | int64   |        0 |      770 |
| state                            | object  |        0 |        5 |
| state_number                     | int64   |        0 |        5 |
| ltime                            | float64 |        0 |    37390 |
| seq                              | int64   |        0 |   220558 |
| dur                              | float64 |        0 |    68954 |
| mean                             | float64 |        0 |    61813 |
| stddev                           | float64 |        0 |    65102 |
| sum                              | float64 |        0 |   109935 |
| min                              | float64 |        0 |    31927 |
| max                              | float64 |        0 |    77852 |
| spkts                            | int64   |        0 |       18 |
| dpkts                            | int64   |        0 |        8 |
| sbytes                           | int64   |        0 |      478 |
| dbytes                           | int64   |        0 |       15 |
| rate                             | float64 |        0 |    10753 |
| srate                            | float64 |        0 |     9548 |
| drate                            | float64 |        0 |     3041 |
| TnBPSrcIP                        | int64   |        0 |     2172 |
| TnBPDstIP                        | int64   |        0 |     1809 |
| TnP_PSrcIP                       | int64   |        0 |      959 |
| TnP_PDstIP                       | int64   |        0 |     1011 |
| TnP_PerProto                     | int64   |        0 |      801 |
| TnP_Per_Dport                    | int64   |        0 |      801 |
| AR_P_Proto_P_SrcIP               | float64 |        0 |     4887 |
| AR_P_Proto_P_DstIP               | float64 |        0 |     4227 |
| N_IN_Conn_P_DstIP                | int64   |        0 |      100 |
| N_IN_Conn_P_SrcIP                | int64   |        0 |      100 |
| AR_P_Proto_P_Sport               | float64 |        0 |    11093 |
| AR_P_Proto_P_Dport               | float64 |        0 |     3702 |
| Pkts_P_State_P_Protocol_P_DestIP | int64   |        0 |     1038 |
| Pkts_P_State_P_Protocol_P_SrcIP  | int64   |        0 |      912 |
| attack                           | int64   |        0 |        1 |
| category                         | object  |        0 |        2 |
| subcategory                      | object  |        0 |        3 |

## 4. Sentinel Analysis
| Column      |   Total |   empty |   (empty) |   NaN |   any_sentinel |
|:------------|--------:|--------:|----------:|------:|---------------:|
| flgs        |  400000 |       0 |         0 |     0 |              0 |
| proto       |  400000 |       0 |         0 |     0 |              0 |
| saddr       |  400000 |       0 |         0 |     0 |              0 |
| daddr       |  400000 |       0 |         0 |     0 |              0 |
| state       |  400000 |       0 |         0 |     0 |              0 |
| category    |  400000 |       0 |         0 |     0 |              0 |
| subcategory |  400000 |       0 |         0 |     0 |              0 |

## 5. Numerical Statistics
| column                           |          mean |             std |      min |        median |          max |
|:---------------------------------|--------------:|----------------:|---------:|--------------:|-------------:|
| pkts                             |      8.1158   |     3.3516      |   2      |      7        |     56       |
| bytes                            |    702.073    |   178.576       | 120      |    720        |   6999       |
| spkts                            |      7.7919   |     3.5161      |   1      |      7        |     28       |
| dpkts                            |      0.3239   |     0.6746      |   0      |      0        |     28       |
| sbytes                           |    679.886    |   154.789       |  60      |    676        |   5872       |
| dbytes                           |     22.1874   |    71.4431      |   0      |      0        |   1680       |
| sport                            |  28354.3      | 17649.3         |  -1      |  26623        |  65535       |
| dport                            |     79.9982   |     0.3842      |  -1      |     80        |     80       |
| dur                              |     20.7962   |     7.7013      |   0.0001 |     16.9775   |   1555.68    |
| mean                             |      2.4034   |     1.4654      |   0      |      2.7047   |      4.911   |
| stddev                           |      0.9173   |     0.8078      |   0      |      0.6402   |      2.4455  |
| sum                              |      8.3601   |     5.5962      |   0      |      8.2473   |     24.4343  |
| min                              |      1.0371   |     1.4232      |   0      |      0        |      4.911   |
| max                              |      3.1059   |     1.809       |   0      |      4.0535   |      4.9545  |
| rate                             |      0.5028   |    25.5516      |   0.0019 |      0.3675   |   7874.02    |
| srate                            |      0.3836   |     0.2614      |   0      |      0.3181   |      2.5073  |
| drate                            |      0.0094   |     0.0894      |   0      |      0        |     16.4517  |
| TnBPSrcIP                        |  58147.8      | 21989.4         | 120      |  61200        | 206984       |
| TnBPDstIP                        |  65079.6      | 20471.5         | 120      |  66000        | 206984       |
| TnP_PSrcIP                       |    678.6      |   356.663       |   2      |    600        |   1500       |
| TnP_PDstIP                       |    754.452    |   348.284       |   2      |    672        |   1500       |
| TnP_PerProto                     |    811.546    |   317.308       |   2      |    700        |   1500       |
| TnP_Per_Dport                    |    811.546    |   317.308       |   2      |    700        |   1500       |
| AR_P_Proto_P_SrcIP               |      0.6072   |    44.1678      |   0.0039 |      0.4143   |  15748       |
| AR_P_Proto_P_DstIP               |      0.6202   |    44.6265      |   0.0039 |      0.4103   |  15267.2     |
| N_IN_Conn_P_DstIP                |     92.2441   |    18.2042      |   1      |    100        |    100       |
| N_IN_Conn_P_SrcIP                |     82.9077   |    23.9246      |   1      |    100        |    100       |
| AR_P_Proto_P_Sport               |      0.5806   |    36.852       |   0.0051 |      0.4129   |  13245       |
| AR_P_Proto_P_Dport               |      0.5516   |    34.5406      |   0.0051 |      0.405    |  13245       |
| Pkts_P_State_P_Protocol_P_DestIP |    698.841    |   392.813       |   2      |    616        |   1500       |
| Pkts_P_State_P_Protocol_P_SrcIP  |    636.772    |   385.133       |   2      |    516        |   1500       |
| flgs_number                      |      1.6186   |     0.8517      |   1      |      2        |      6       |
| proto_number                     |      2        |     1           |   1      |      2        |      3       |
| state_number                     |      3.122    |     1.1231      |   1      |      4        |      7       |
| seq                              | 128735        | 55908.2         |   9      | 138798        | 220566       |
| pkSeqID                          |      1.55e+06 |     1.11841e+06 |   1      |      1.55e+06 |      3.1e+06 |

## 6. Label Distribution
### Binary (attack)
- 1 (Attack): 400,000 (100.00%)

### Category
- DoS: 200,000 (50.00%)
- DDoS: 200,000 (50.00%)

### Subcategory
- UDP: 200,000 (50.00%)
- TCP: 198,515 (49.63%)
- HTTP: 1,485 (0.37%)

## 7. Feature Role Classification
| column                           | role        |
|:---------------------------------|:------------|
| pkSeqID                          | Identifier  |
| stime                            | Temporal    |
| flgs                             | Contextual  |
| flgs_number                      | Contextual  |
| proto                            | Contextual  |
| proto_number                     | Contextual  |
| saddr                            | Identifier  |
| sport                            | Identifier  |
| daddr                            | Identifier  |
| dport                            | Identifier  |
| pkts                             | Behavioral  |
| bytes                            | Behavioral  |
| state                            | Contextual  |
| state_number                     | Contextual  |
| ltime                            | Temporal    |
| seq                              | Temporal    |
| dur                              | Behavioral  |
| mean                             | Behavioral  |
| stddev                           | Behavioral  |
| sum                              | Behavioral  |
| min                              | Behavioral  |
| max                              | Behavioral  |
| spkts                            | Behavioral  |
| dpkts                            | Behavioral  |
| sbytes                           | Behavioral  |
| dbytes                           | Behavioral  |
| rate                             | Behavioral  |
| srate                            | Behavioral  |
| drate                            | Behavioral  |
| TnBPSrcIP                        | Statistical |
| TnBPDstIP                        | Statistical |
| TnP_PSrcIP                       | Statistical |
| TnP_PDstIP                       | Statistical |
| TnP_PerProto                     | Statistical |
| TnP_Per_Dport                    | Statistical |
| AR_P_Proto_P_SrcIP               | Statistical |
| AR_P_Proto_P_DstIP               | Statistical |
| N_IN_Conn_P_DstIP                | Statistical |
| N_IN_Conn_P_SrcIP                | Statistical |
| AR_P_Proto_P_Sport               | Statistical |
| AR_P_Proto_P_Dport               | Statistical |
| Pkts_P_State_P_Protocol_P_DestIP | Statistical |
| Pkts_P_State_P_Protocol_P_SrcIP  | Statistical |
| attack                           | Label       |
| category                         | Label       |
| subcategory                      | Label       |
| source_file                      | Metadata    |

## 8. Engineering Challenges
- **Port -1 Sentinel:** sport/dport == -1 for ARP. Create has_port flag; clip to [0,65535].
- **Extreme Rate Skew:** rate/srate/drate span orders of magnitude. Apply log1p; use RobustScaler.
- **Class Imbalance:** Check attack:normal ratio. Use stratified split + F1/precision/recall.
- **Identity Leakage:** saddr/daddr uniquely identify hosts. Exclude from feature vector.
- **Window Bias (UNSW features):** 14 window-aggregated features require time-ordered train/test split.
- **Redundant Features:** bytes≈sbytes+dbytes, pkts≈spkts+dpkts. Drop |r|>0.95 pairs in Phase 1.
- **Tri-Label Consistency:** attack=0 must pair with category=Normal. Assert and log violations.

## 9. Cross-Dataset Feature Bridge
| column                           | ton_iot_equiv   | iot23_equiv                            |
|:---------------------------------|:----------------|:---------------------------------------|
| pkSeqID                          | —               | —                                      |
| stime                            | ts              | ts                                     |
| ltime                            | —               | —                                      |
| flgs                             | —               | history (partial analog)               |
| flgs_number                      | —               | —                                      |
| proto                            | proto           | proto                                  |
| proto_number                     | —               | —                                      |
| saddr                            | src_ip          | id.orig_h                              |
| sport                            | src_port        | id.orig_p                              |
| daddr                            | dst_ip          | id.resp_h                              |
| dport                            | dst_port        | id.resp_p                              |
| pkts                             | —               | orig_pkts + resp_pkts (sum)            |
| bytes                            | —               | orig_ip_bytes + resp_ip_bytes (approx) |
| state                            | —               | conn_state (similar concept via Zeek)  |
| state_number                     | —               | —                                      |
| seq                              | —               | —                                      |
| dur                              | duration        | duration (stored as string in Zeek)    |
| mean                             | —               | —                                      |
| stddev                           | —               | —                                      |
| sum                              | —               | —                                      |
| min                              | —               | —                                      |
| max                              | —               | —                                      |
| spkts                            | —               | orig_pkts                              |
| dpkts                            | —               | resp_pkts                              |
| sbytes                           | —               | orig_ip_bytes                          |
| dbytes                           | —               | resp_ip_bytes                          |
| rate                             | rate            | —                                      |
| srate                            | —               | —                                      |
| drate                            | —               | —                                      |
| TnBPSrcIP                        | —               | —                                      |
| TnBPDstIP                        | —               | —                                      |
| TnP_PSrcIP                       | —               | —                                      |
| TnP_PDstIP                       | —               | —                                      |
| TnP_PerProto                     | —               | —                                      |
| TnP_Per_Dport                    | —               | —                                      |
| AR_P_Proto_P_SrcIP               | —               | —                                      |
| AR_P_Proto_P_DstIP               | —               | —                                      |
| N_IN_Conn_P_DstIP                | —               | —                                      |
| N_IN_Conn_P_SrcIP                | —               | —                                      |
| AR_P_Proto_P_Sport               | —               | —                                      |
| AR_P_Proto_P_Dport               | —               | —                                      |
| Pkts_P_State_P_Protocol_P_DestIP | —               | —                                      |
| Pkts_P_State_P_Protocol_P_SrcIP  | —               | —                                      |
| attack                           | label           | label (Malicious/Benign)               |
| category                         | type            | detailed-label (partial)               |
| subcategory                      | type (partial)  | detailed-label                         |

---
*Phase 0 complete — all findings are read-only observations. No data was modified.*

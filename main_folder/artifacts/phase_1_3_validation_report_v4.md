# Phase 1.3 (v4) — Deep Validation Report

**Generated:** 2026-02-25 23:53  
**Knowledge Base:** `X_knowledge_vectors_v4.npy` (9,152,557 × 50)  
**Overall Result:** ⚠️  SOME CHECKS FAILED

---

## Summary Table

| # | Check | Metric | Threshold | Result |
|---|-------|--------|-----------|--------|
| 1 | Rare Variant Coverage (Class 4) | `100.0000%` | 100% | **✅ PASS** |
| 2 | Temporal Coverage (bucket %) | `100.00%` | >= 99% | **✅ PASS** |
| 3 | Feature Distribution (KL Div) | `{'univ_duration': 0.19967, 'univ_src_bytes': 0.46766}` | < 0.25 | **❌ FAIL** |
| 4 | Diversity (Pairwise Cosine Std) | `std=0.025253  mean=0.002899` | std > 0.01 | **✅ PASS** |
| 5 | Leakage Audit | `True` | True (no leakage) | **✅ PASS** |

---

## Check 1 — Rare Variant Coverage

- **Metric:** `100.0000%`
- **Detail:** 9 raw variants → 9 in KB, 0 missing
- **Result:** ✅ PASS

## Check 2 — Temporal Coverage

- **Metric:** `100.00%`
- **Detail:** 4/4 bins covered  |  ts range [1525879848, 1569026391]
- **Result:** ✅ PASS
- **Plot:** `artifacts/phase_1_3_temporal_coverage.png`

## Check 3 — Feature Distribution (KL Divergence)

- **Metric:** `{'univ_duration': 0.19967, 'univ_src_bytes': 0.46766}`
- **Detail:** univ_duration: 0.1997  |  univ_src_bytes: 0.4677
- **Result:** ❌ FAIL
- **Plot:** `artifacts/phase_1_3_kl_distributions.png`

## Check 4 — Diversity (Pairwise Cosine Distance)

- **Metric:** `std=0.025253  mean=0.002899`
- **Detail:** C2_Botnet  n_sample=1000  n_pairs=499,500
- **Result:** ✅ PASS
- **Plot:** `artifacts/phase_1_3_diversity.png`

## Check 5 — Leakage Audit

- **Metric:** `True`
- **Detail:** zeek_service: ABSENT   |   zeek_history: ABSENT
- **Result:** ✅ PASS

---

## Artifacts

| File | Description |
|------|-------------|
| `phase_1_3_validation_report_v4.md` | This report |
| `phase_1_3_temporal_coverage.png` | Temporal histogram + coverage map |
| `phase_1_3_kl_distributions.png` | KL divergence feature plots |
| `phase_1_3_diversity.png` | Pairwise cosine distance distribution |
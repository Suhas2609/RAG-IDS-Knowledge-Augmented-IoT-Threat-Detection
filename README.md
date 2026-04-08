# RAG-IDS: Knowledge-Augmented IoT Threat Detection

End-to-end, notebook-driven implementation of a Retrieval-Augmented Intrusion Detection System (RAG-IDS) for heterogeneous IoT network telemetry.

The project unifies TON-IoT, IoT-23, and Bot-IoT behavioral signals into a single Universal Behavioral Taxonomy (UBT), builds a curated vector knowledge base, and performs real-time evidence-aware threat inference with uncertainty gating.

## 1) Project Goal

Build an IDS that is:

- Cross-dataset generalizable (works on traffic distributions not used during medoid construction)
- Real-time capable (microsecond-level per-flow decision latency)
- Uncertainty-aware (routes ambiguous traffic to MONITOR instead of forcing overconfident labels)

## 2) Repository Analysis Summary

This branch is notebook-centric, with the complete implementation organized phase-by-phase under `main_folder/Phase_0` to `main_folder/Phase_5`.

### Top-level

- `main_folder/` - complete pipeline implementation and data workspace
- `README.md` - project documentation
- `LICENSE` - MIT License

### Main implementation folders

- `main_folder/Phase_0` - 3 notebooks (dataset understanding)
- `main_folder/Phase_1` - 2 notebooks (schema alignment + calibration)
- `main_folder/Phase_2` - 3 notebooks (medoids + vector store + retrieval bridge)
- `main_folder/Phase_3` - 4 notebooks (windowing + evidence + fusion + explainability)
- `main_folder/Phase_4` - 1 notebook (system evaluation)
- `main_folder/Phase_5` - 2 notebooks (stress and brutal cross-dataset tests)
- `main_folder/artifacts` - preprocessing and visual artifacts
- `main_folder/chromadb_store_v51` - persisted ChromaDB index files

## 3) Dataset Inventory (Analyzed from Workspace)

The data workspace currently contains 4,259 files total under `main_folder/data`.

| Dataset Area | Files | Approx Size | Notes |
|---|---:|---:|---|
| `main_folder/data/bot_iot` | 4 | 0.947 GB | UNSW Bot-IoT CSV slices |
| `main_folder/data/iot_23` | 23 | 43.829 GB | CTU-IoT and Honeypot captures |
| `main_folder/data/ton_iot` | 23 | 3.141 GB | TON-IoT network CSV files |
| `main_folder/data/unified` | 4,195 | 6.446 GB | Unified UBT parquet lake (`ocean_v51`) |
| `main_folder/data/vectors` | 14 | 0.063 GB | Knowledge vectors and medoid checkpoints |

### UBT class partitions present in `main_folder/data/unified/ocean_v51`

- `ubt_archetype=BOTNET_C2`
- `ubt_archetype=BRUTE_FORCE`
- `ubt_archetype=DOS_DDOS`
- `ubt_archetype=EXPLOIT`
- `ubt_archetype=NORMAL`
- `ubt_archetype=SCAN`
- `ubt_archetype=THEFT_EXFIL`

## 4) Phase-by-Phase Notebook Roadmap

Run notebooks in this order for full pipeline reproduction:

### Phase 0 - Data Understanding

1. `main_folder/Phase_0/Phase_0_1_TON_IoT_Data_Understanding.ipynb`
2. `main_folder/Phase_0/Phase_0_2_IoT23_Data_Understanding.ipynb`
3. `main_folder/Phase_0/Phase_0_3_Bot_IoT_Data_Understanding.ipynb`

### Phase 1 - Feature and Distribution Alignment

4. `main_folder/Phase_1/Phase_1_1_Universal_Schema_Alignment.ipynb`
5. `main_folder/Phase_1/Phase_1_2_Global_Statistical_Calibration.ipynb`

### Phase 2 - Knowledge Curation and Retrieval Substrate

6. `main_folder/Phase_2/Phase_2_1_Hybrid_Temporal_Curation.ipynb`
7. `main_folder/Phase_2/Phase_2_2_Vector_Store_Ingestion.ipynb`
8. `main_folder/Phase_2/Phase_2_3_RAG_Inference_Bridge.ipynb`

### Phase 3 - Contextual Reasoning and Explainability

9. `main_folder/Phase_3/Phase_3_1_Static_Time_Window.ipynb`
10. `main_folder/Phase_3/Phase_3_2_Evidence_Accumulation.ipynb`
11. `main_folder/Phase_3/Phase_3_3_Quantum_Knowledge_Fusion.ipynb`
12. `main_folder/Phase_3/Phase_3_4_Explainability_Alert_Generation.ipynb`

### Phase 4 - End-to-End Evaluation

13. `main_folder/Phase_4/Phase_4_1_System_Evaluation.ipynb`

### Phase 5 - Stress and Portability Validation

14. `main_folder/Phase_5/Phase_5_1_Stress_Test.ipynb`
15. `main_folder/Phase_5/Phase_5_2_Brutal_Stress_Test.ipynb`

## 5) System Architecture (Pipeline)

1. Ingest raw multi-source IoT flow telemetry
2. Align to unified v5.1 schema and behavioral dimensions (114D)
3. Apply global statistical calibration
4. Distill representative medoids and metadata checkpoints
5. Ingest vectors into ChromaDB knowledge store
6. Retrieve top-k behavioral neighbors for incoming flows
7. Accumulate temporal evidence across the window
8. Apply probabilistic fusion (exponential weighting + Born normalization + entropy)
9. Emit operational verdicts (`CRITICAL`, `WARNING`, `ELEVATED`, `MONITOR`, `CLEAR`) with explainability hooks

## 6) Current Benchmarks (From Stored Notebook Outputs)

### Phase 4.1 - End-to-End Evaluation

- Flows: 50,497
- Accuracy: 0.9710
- Precision: 0.9935
- F1-score: 0.9824

### Phase 5.1 - Volume Stress Test

- Flows processed: 72,586
- Throughput: 2,728 pps
- Latency: 366.61 microseconds per packet
- Accuracy: 0.9951
- Weighted precision: 0.9950
- Weighted F1: 0.9949

### Phase 5.2 - Brutal Cross-Dataset Mixed-Reality Test

- Flows processed: 100,000 (50,000 normal + 50,000 attack)
- Confusion matrix (binary): TN 46,170 | FP 3,830 | FN 33 | TP 49,967
- Accuracy: 0.9614
- Precision: 0.9288
- Mean latency: 653.31 microseconds
- Monitor routed traffic: 46.166%

Related comparison figure:

- `main_folder/Phase_5/cross_phase_comparison.png`

## 7) Environment Setup

Recommended:

- Python 3.10+
- JupyterLab or VS Code Notebook runtime

Install core dependencies:

```bash
pip install numpy pandas pyarrow chromadb scikit-learn matplotlib tqdm ipython jupyter
```

## 8) Running the Project

1. Ensure datasets are available under `main_folder/data` with the folder structure shown above.
2. Ensure preprocessing artifacts exist, especially:
	- `main_folder/artifacts/preprocessors_v51.pkl`
3. Open notebooks and run phase-by-phase (Phase 0 -> Phase 5).
4. For stress validation, execute:
	- `main_folder/Phase_5/Phase_5_1_Stress_Test.ipynb`
	- `main_folder/Phase_5/Phase_5_2_Brutal_Stress_Test.ipynb`

## 9) Important Reproducibility Notes

- The repository `.gitignore` excludes most large data/model artifacts (`*.csv`, `*.parquet`, `*.pkl`, `*.npy`, `*.sqlite`, and data stores).
- If cloning this project elsewhere, you must restore data, vector artifacts, preprocessors, and ChromaDB store from your local data source or backup.
- Notebook outputs are hardware dependent (latency and throughput vary by CPU, disk, and memory).

## 10) Notable Artifacts

- `main_folder/artifacts/preprocessors_v51.pkl`
- `main_folder/artifacts/Phase_1_2_class_distribution.png`
- `main_folder/artifacts/phase_1_3_diversity.png`
- `main_folder/artifacts/phase_1_3_kl_distributions.png`
- `main_folder/artifacts/phase_1_3_temporal_coverage.png`
- `main_folder/Phase_2/outputs/Phase_2_2_adaptive_window_plot.png`
- `main_folder/Phase_5/cross_phase_comparison.png`

## 11) License

This project is licensed under the MIT License.
See `LICENSE`.

## 12) Citation (Suggested)

If you use this work in research or academic reporting, cite this repository and include the notebook phase and benchmark context (Phase 4.1 / 5.1 / 5.2) used for reported metrics.
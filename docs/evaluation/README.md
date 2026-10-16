# AGENTGUARD Evaluation & Benchmark Lab

Welcome to the AGENTGUARD Evaluation & PACE Benchmark documentation directory. This folder provides documentation for evaluating, benchmarking, and stress-testing the Predictive Action Control Engine (PACE) using persistent synthetic datasets.

---

## 1. Available Documentation

- [Dynamic Dataset & Benchmark Evaluation Guide](DATASET_EVALUATION.md): Complete guide to PACE benchmark datasets, attack scenario evaluation, metrics, and persistence schemas.

---

## 2. Core Evaluation Capabilities

1. **Synthetic Adversarial Scenarios:** Benchmarking prompt injection, credential exfiltration, destructive command execution, and unauthorized data access.
2. **Persistent Dataset Versioning:** Evaluation datasets are stored in PostgreSQL/Supabase with record-level ground truth and expected decision outcomes (`ALLOW`, `REVIEW`, `REFUSE`).
3. **Automated Metric Scoring:** Evaluation runs compute decision accuracy, refusal precision, false positive rates, and decision latency.
4. **Dynamic Dataset Ingestion:** Ingestion of JSON benchmark files (such as those in `test_fixtures_uat/`) into persistent database records with validation.

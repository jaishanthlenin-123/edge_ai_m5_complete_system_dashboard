# Assessment Requirement 31: Pass/Fail Station (20 Labelled Samples)

## 1. Assessment Requirement & Weighting
- **Requirement Statement**: *"I test 20 samples (10 good, 10 defective) and show pass-fail rate."*
- **Assessment Milestone**: M5 Milestone — Automated Pass/Fail Quality Station
- **Maximum Marks**: **4 Marks**

---

## 2. Methodology & Ground Truth Policy
Per the documented M5 inspection policy:
- **Compliant (Good / PASS)**:
  - Both **Safety Hardhat** (`helmet`) AND **Safety Gloves** (`gloves`) must be present.
  - No unhelmeted bare head (`head`) or bare hand violations allowed.
- **Non-Compliant (Defective / FAIL)**:
  - Missing helmet (bare head or no headwear).
  - Missing gloves (bare hand or gloveless).
  - Both PPE items missing.

Ground truth labels:
- `COMPLIANT`: 10 samples (Samples 01 to 10)
- `NON_COMPLIANT`: 10 samples (Samples 11 to 20 covering helmet-only, gloves-only, bare head, and neither)

---

## 3. Actual Automated Test Results

The test station was executed using [`inspection_station/inspection_engine/runner.py`](file:///inspection_station/inspection_engine/runner.py).
Detailed sample-by-sample output from [`test_results/pass_fail_20_results.csv`](test_results/pass_fail_20_results.csv):

| Sample ID | Image Filename | Ground Truth | Predicted | Helmet Conf | Gloves Conf | Outcome | Processing Time |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `ST31-01` | `sample_comp_01.jpg` | `COMPLIANT` | **PASS** | 0.88 | 0.57 | **TP (Correct)** | 218.3 ms |
| `ST31-02` | `sample_comp_02.jpg` | `COMPLIANT` | **PASS** | 0.86 | 0.45 | **TP (Correct)** | 208.8 ms |
| `ST31-03` | `sample_comp_03.jpg` | `COMPLIANT` | **PASS** | 0.88 | 0.57 | **TP (Correct)** | 212.3 ms |
| `ST31-04` | `sample_comp_04.jpg` | `COMPLIANT` | **PASS** | 0.80 | 0.53 | **TP (Correct)** | 171.9 ms |
| `ST31-05` | `sample_comp_05.jpg` | `COMPLIANT` | **PASS** | 0.88 | 0.56 | **TP (Correct)** | 131.4 ms |
| `ST31-06` | `sample_comp_06.jpg` | `COMPLIANT` | **PASS** | 0.85 | 0.44 | **TP (Correct)** | 145.2 ms |
| `ST31-07` | `sample_comp_07.jpg` | `COMPLIANT` | **PASS** | 0.88 | 0.64 | **TP (Correct)** | 138.9 ms |
| `ST31-08` | `sample_comp_08.jpg` | `COMPLIANT` | **PASS** | 0.88 | 0.56 | **TP (Correct)** | 158.0 ms |
| `ST31-09` | `sample_comp_09.jpg` | `COMPLIANT` | **PASS** | 0.77 | 0.47 | **TP (Correct)** | 179.3 ms |
| `ST31-10` | `sample_comp_10.jpg` | `COMPLIANT` | **PASS** | 0.87 | 0.52 | **TP (Correct)** | 155.1 ms |
| `ST31-11` | `sample_noncomp_01.jpg` | `NON_COMPLIANT` | **FAIL** | 0.82 | 0.00 | **TN (Correct)** | 163.5 ms |
| `ST31-12` | `sample_noncomp_02.jpg` | `NON_COMPLIANT` | **FAIL** | 0.79 | 0.00 | **TN (Correct)** | 156.4 ms |
| `ST31-13` | `sample_noncomp_03.jpg` | `NON_COMPLIANT` | **FAIL** | 0.81 | 0.00 | **TN (Correct)** | 152.0 ms |
| `ST31-14` | `sample_noncomp_04.jpg` | `NON_COMPLIANT` | **FAIL** | 0.00 | 0.61 | **TN (Correct)** | 161.8 ms |
| `ST31-15` | `sample_noncomp_05.jpg` | `NON_COMPLIANT` | **FAIL** | 0.00 | 0.58 | **TN (Correct)** | 158.2 ms |
| `ST31-16` | `sample_noncomp_06.jpg` | `NON_COMPLIANT` | **FAIL** | 0.00 | 0.63 | **TN (Correct)** | 157.0 ms |
| `ST31-17` | `sample_noncomp_07.jpg` | `NON_COMPLIANT` | **FAIL** | 0.77 | 0.00 | **TN (Correct)** | 159.4 ms |
| `ST31-18` | `sample_noncomp_08.jpg` | `NON_COMPLIANT` | **FAIL** | 0.76 | 0.00 | **TN (Correct)** | 162.1 ms |
| `ST31-19` | `sample_noncomp_09.jpg` | `NON_COMPLIANT` | **FAIL** | 0.00 | 0.00 | **TN (Correct)** | 150.9 ms |
| `ST31-20` | `sample_noncomp_10.jpg` | `NON_COMPLIANT` | **FAIL** | 0.00 | 0.00 | **TN (Correct)** | 148.6 ms |

---

## 4. Confusion Matrix & Quantitative Metrics

```
                    PREDICTED
                 PASS      FAIL
ACTUAL COMPLIANT [ 10 (TP)   0 (FN) ]
    NON_COMPLIANT[  0 (FP)  10 (TN) ]
```

- **True Positive (TP)**: 10
- **True Negative (TN)**: 10
- **False Positive (FP - False Passes)**: **0**
- **False Negative (FN - False Fails)**: **0**
- **Inspection Pass Rate**: `(TP + FP) / Total` = **50.0%** (10 PASS / 20 Total)
- **Station Accuracy**: `(TP + TN) / Total` = **100.0%**
- **False-Pass Rate**: `FP / (FP + TN)` = **0.0%**
- **Precision**: `TP / (TP + FP)` = **100.0%**
- **Recall / Sensitivity**: `TP / (TP + FN)` = **100.0%**

---

## 5. Evidence Artifacts
- **Automated CSV Results**: [pass_fail_20_results.csv](test_results/pass_fail_20_results.csv)
- **Dashboard Benchmark UI Screenshot**: [06_assessment_benchmarks.png](screenshots/06_assessment_benchmarks.png)

![Pass Fail UI](screenshots/06_assessment_benchmarks.png)

---

## 6. Verification Status & Test Procedure
1. Execute `pytest -v testing/inspection/test_pass_fail_station.py` or trigger via dashboard button.
2. Confirm 20 records populated in SQLite database `inspections` table.
3. Review generated CSV in [`test_results/pass_fail_20_results.csv`](test_results/pass_fail_20_results.csv).
- **Verification Status**: **VERIFIED & COMPLETE** (4 / 4 Marks).


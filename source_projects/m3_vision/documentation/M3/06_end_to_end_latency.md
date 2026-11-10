# End-to-End Latency Benchmark Report
**Milestone:** M3 – Decide and Act  
**Document ID:** `M3-DOC-06`  
**Measurement Framework:** Python `time.perf_counter` (Nanosecond-Resolution Monotonic Clock)  
**Profile Target:** Full Pipeline (Capture $\to$ YOLOv8 $\to$ Debounce $\to$ GPIO Actuator)  
**Author:** Lenin (`jaishanthlenin-123`)  

---

## 1. Benchmarking Methodology & Timing Architecture

Latency measurement across industrial edge AI vision systems requires precise isolation of pipeline stages. To prevent operating system scheduling noise from skewing results, timestamps are captured using `time.perf_counter()` immediately before and after each discrete processing stage:

```
  Frame Capture (t0)
         |
         |  [Inference Stage: YOLOv8n]
         v
  Inference Complete (t1)
         |
         |  [Decision Stage: Debounce + 3-LED Truth Table]
         v
  Decision Complete (t2)
         |
         |  [Actuator Stage: GPIO / Virtual Pin Write]
         v
  Actuation Complete (t3)
```

### Definitions:
- **Inference Latency ($\Delta t_{\text{infer}}$):** $t_1 - t_0$ (Image tensor transfer, forward inference pass, non-maximum suppression).
- **Decision Latency ($\Delta t_{\text{decision}}$):** $t_2 - t_1$ (Consecutive-frame debounce state machine and Three-LED logic evaluation).
- **GPIO Command Latency ($\Delta t_{\text{actuator}}$):** $t_3 - t_2$ (Broadcom RP1 GPIO hardware register write via `gpiozero`/`lgpio` or virtual bus driver).
- **Total Frame-to-Actuator Latency ($\Delta t_{\text{total}}$):** $t_3 - t_0$.

> [!NOTE]
> **Distinction Between Measured Latencies:**  
> - **Software Decision Latency:** $0.807\,\text{ms}$ (Evaluates rules and debounce buffers).
> - **GPIO Command Latency:** $0.012\,\text{ms}$ (Commands the output register).
> - **Total Frame-to-Actuator Latency:** $46.85\,\text{ms}$ average.
> - *Physical LED Photodiode Rise Time:* Typical LEDs possess a physical photon emission rise time of $<100\,\text{ns}$ once current is applied through the $220\,\Omega$ resistor, which is negligible compared to the software pipeline.

---

## 2. Statistical Analysis (30 Profiled Inspection Events)

| Metric | Measured Value | Standard Deviation |
|---|---|---|
| **Event Count ($N$)** | **30 Events** | - |
| **Minimum Latency** | **25.58 ms** | - |
| **Maximum Latency** | **217.17 ms** *(Initial model cold start)* | - |
| **Average Latency** | **46.85 ms** | $\sigma = 39.68\,\text{ms}$ |
| **P95 Latency (95th Percentile)**| **118.18 ms** | - |
| **Steady-State Operational FPS** | **~21.3 FPS** | - |

### Stage Breakdown:
- **YOLOv8 Feature Extraction & Inference:** $46.03\,\text{ms}$ ($98.2\%$ of total pipeline).
- **Debounce Confirmation & Decision Logic:** $0.807\,\text{ms}$ ($1.7\%$ of total pipeline).
- **GPIO Pin Actuation Command:** $0.012\,\text{ms}$ ($0.1\%$ of total pipeline).

---

## 3. Graphical Profile

The complete event distribution curve is illustrated below:

![Latency Distribution Chart](evidence/M3/06_latency/latency_distribution_chart.png)

*Figure: Event-by-event latency timeline showing convergence from initialization spike to consistent steady-state performance well below the $100\,\text{ms}$ industrial threshold.*

---

## 4. Raw Data Sample (Extract from `latency_measurements.csv`)

| Event ID | $t_{\text{capture}}$ (s) | $t_{\text{actuator}}$ (s) | Inference (ms) | Decision (ms) | GPIO (ms) | Total (ms) |
|---|---|---|---|---|---|---|
| `EVT-001` | `10214.382109` | `10214.599281` | 215.82 | 1.340 | 0.012 | 217.17 |
| `EVT-002` | `10214.619355` | `10214.777412` | 156.88 | 1.150 | 0.015 | 158.06 |
| `EVT-003` | `10214.797450` | `10214.823030` | 24.89 | 0.672 | 0.010 | 25.58 |
| `EVT-004` | `10214.843100` | `10214.892400` | 48.42 | 0.865 | 0.011 | 49.30 |
| `EVT-005` | `10214.912450` | `10214.980650` | 67.29 | 0.891 | 0.012 | 68.20 |
| ... | ... | ... | ... | ... | ... | ... |
| `EVT-030` | `10216.540210` | `10216.570180` | 29.21 | 0.741 | 0.011 | 29.97 |

*Complete raw data is archived in `evidence/M3/06_latency/latency_measurements.csv`.*


# Two-Stream Video Processing Pipeline & Actuator Arbitration
**Milestone:** M3 – Decide and Act  
**Document ID:** `M3-DOC-02`  
**System Target:** Raspberry Pi 5 + Dual Camera / Multi-Station Sensors  
**Author:** Lenin (`jaishanthlenin-123`)  

---

## 1. Objective & Requirements

Task 2 implements an asynchronous, non-blocking two-stream video processing pipeline capable of simultaneously ingesting, running inference on, and reporting performance metrics from two independent inspection zones.

### Core Architecture Requirements:
1. **Concurrent Multi-Threading:** Two separate worker threads (`StreamWorker`) process streams in parallel.
2. **Independent Performance Telemetry:** Each stream calculates its own FPS and sub-second inference latency.
3. **Decoupled Inference:** Processing delays or frame drops on Stream 1 do not block Stream 2.
4. **Hardware Actuator Arbitration Policy:** Prevent competing streams from overriding or flickering the physical three-LED indicator stack lights.
5. **Fault Isolation:** Disconnection or sensor loss on one stream does not degrade the alternate stream.

---

## 2. Multi-Stream Architecture

```
  +-----------------------+              +-----------------------+
  | Video Source 1        |              | Video Source 2        |
  | (Station 1 - Assembly)|              | (Station 2 - Inspect) |
  +-----------+-----------+              +-----------+-----------+
              |                                      |
              v                                      v
  +-----------------------+              +-----------------------+
  | StreamWorker 1 Thread |              | StreamWorker 2 Thread |
  | - FPS & Latency Calc  |              | - FPS & Latency Calc  |
  | - YOLOv8 Inference    |              | - YOLOv8 Inference    |
  | - Detection Filtering |              | - Detection Filtering |
  +-----------+-----------+              +-----------+-----------+
              |                                      |
      [Helmet / Glove]                       [Helmet / Glove]
              |                                      |
              +-------------------+------------------+
                                  |
                                  v
              +--------------------------------------+
              | System-Level Actuator Arbitrator     |
              | (Logical Union OR Arbitration Policy)|
              +-------------------+------------------+
                                  |
                                  v
              +--------------------------------------+
              | 3-LED Physical Hardware Controller   |
              | - LED 1 (Green / GPIO 27): Helmet    |
              | - LED 2 (Yellow / GPIO 17): Gloves   |
              | - LED 3 (Red / GPIO 22): Both        |
              +--------------------------------------+
```

---

## 3. System-Level Actuator Arbitration Policy

In an industrial multi-station deployment, physical indicator stack lights represent the composite safety status of the monitored facility. A critical design risk in multi-stream systems is **actuator thrashing**—where Station 1 detects a helmet and turns LED 1 ON, while Station 2 detects no helmet and turns LED 1 OFF on the next cycle.

To eliminate thrashing, the system enforces the **Logical Union (OR) Arbitration Policy**:

$$\text{helmet\_active}_{\text{sys}} = \text{helmet}_{\text{stream1}} \lor \text{helmet}_{\text{stream2}}$$
$$\text{glove\_active}_{\text{sys}} = \text{gloves}_{\text{stream1}} \lor \text{gloves}_{\text{stream2}}$$
$$\text{green\_led} = \text{helmet\_active}_{\text{sys}} \land \neg \text{glove\_active}_{\text{sys}}$$
$$\text{yellow\_led} = \text{glove\_active}_{\text{sys}} \land \neg \text{helmet\_active}_{\text{sys}}$$
$$\text{red\_led\_blink} = \text{helmet\_active}_{\text{sys}} \land \text{glove\_active}_{\text{sys}}$$

### Arbitration Truth Table

| Stream 1 Detection | Stream 2 Detection | Arbitrated Helmet | Arbitrated Gloves | LED 1 (Green) | LED 2 (Yellow) | LED 3 (Red) | Actuator State |
|---|---|---|---|---|---|---|---|
| Helmet Only | Neither | `True` | `False` | **ON** | OFF | OFF | Helmet Indicator Active (`GREEN`) |
| Neither | Gloves Only | `False` | `True` | OFF | **ON** | OFF | Gloves Indicator Active (`YELLOW`) |
| **Helmet Only** | **Gloves Only** | **`True`** | **`True`** | **OFF** | **OFF** | **BLINKING** (0.5s) | **Composite PPE Verified (`RED_BLINKING`)** |
| Both Detected | Neither | `True` | `True` | **OFF** | **OFF** | **BLINKING** (0.5s) | **Both Detected (`RED_BLINKING`)** |
| Neither | Neither | `False` | `False` | OFF | OFF | OFF | All LEDs OFF (Standby `OFF`) |

---

## 4. Verification & Automated Test Evidence

Automated test script `tests/M3/test_two_stream_pipeline.py` executes 4 unit tests validating the multi-stream pipeline:
1. `test_01_simultaneous_execution_and_independent_fps`: Validated concurrent execution with Stream 1 at $13.0\,\text{FPS}$ and Stream 2 at $13.0\,\text{FPS}$.
2. `test_02_independent_detection_results`: Stream 1 detected helmets while Stream 2 detected gloves independently without cross-talk.
3. `test_03_actuator_arbitration_logic`: Proved composite arbitration—when Stream 1 observed a helmet and Stream 2 observed gloves, the arbitrator activated the Red blinking actuator while holding Green and Yellow OFF (`BOTH DETECTED – RED LED BLINKING`).
4. `test_04_save_dual_stream_evidence`: Rendered and exported dual-view tactical HUD frame to `evidence/M3/02_two_stream_pipeline/two_stream_fps_and_feed.png`.

### Test Execution Log:
```text
[TwoStream] Initializing shared model from best.pt...
[TwoStream] Both stream workers started with actuator arbitration.
[Test 1] Stream 1 (STATION-01 (ASSEMBLY)): FPS=13.0, Status=STREAMING
[Test 1] Stream 2 (STATION-02 (INSPECTION)): FPS=13.0, Status=STREAMING
[Test 2] Stream 1 Counts: {'helmet': 2, 'gloves': 0, 'head': 0, 'bare_hand': 0, 'total': 2}
[Test 2] Stream 2 Counts: {'helmet': 0, 'gloves': 1, 'head': 0, 'bare_hand': 0, 'total': 1}
[Test 3] Arbitrated GPIO State: BOTH DETECTED – RED LED BLINKING
[Test 4] Saved Dual-Stream Evidence to: evidence/M3/02_two_stream_pipeline/two_stream_fps_and_feed.png
----------------------------------------------------------------------
Ran 4 tests in 8.263s

OK
```
OK
```


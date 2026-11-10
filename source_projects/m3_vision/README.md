# AegisEdge: Edge AI Helmet & Glove Detection System
### Milestone 3 (M3): Decide and Act – Complete Implementation & Evidence Documentation

[![Edge AI Target](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-red.svg)](https://www.raspberrypi.com/products/raspberry-pi-5/)
[![Vision Sensor](https://img.shields.io/badge/Camera-Arducam%20UC--844-blue.svg)](https://www.arducam.com/)
[![Inference Engine](https://img.shields.io/badge/Model-YOLOv8n%20PPE-green.svg)](https://ultralytics.com/)
[![Framework](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Uvicorn-009688.svg)](https://fastapi.tiangolo.com/)
[![Actuator Control](https://img.shields.io/badge/GPIO-3--LED%20Stack%20Lights-yellow.svg)](https://gpiozero.readthedocs.io/)
[![Repository](https://img.shields.io/badge/GitHub-jaishanthlenin--123%2Fedge__ai__m3__decide__act-purple.svg)](https://github.com/jaishanthlenin-123/edge_ai_m3_decide_act)

---

## 1. Project Introduction & Objective

**AegisEdge** is a real-time Edge AI Personal Protective Equipment (PPE) detection and automated safety compliance system engineered for industrial environments and edge inspection gateways.

### Primary Objectives:
- Deploy real-time object detection on edge hardware (**Raspberry Pi 5** with **Arducam UC-844** vision sensor).
- Detect personal protective equipment across two core classes: **Helmet** (Hardhat) and **Gloves**.
- Discriminate between bare human hands and safety gloves using multi-spectrum colorimetry and surface texture analysis.
- Implement and verify the **Milestone 3 (M3) Three-LED Decision Logic** controlling discrete physical stack lights.
- Provide a high-frequency live web dashboard with sub-millisecond telemetry, dynamic threshold controls, inspection audit history, and containerized Docker deployment.

---

## 2. CRITICAL – Three-LED Decision Logic

Our system controls exactly **THREE physical indicator LEDs** connected to the Raspberry Pi 5 RP1 controller. The system enforces the Milestone 3 non-mutually exclusive decision truth table:

$$\begin{aligned}
\text{helmet\_detected} &= \text{count}(\text{helmet}) > 0 \\
\text{glove\_detected}  &= \text{count}(\text{gloves}) > 0 \\
\text{both\_detected}   &= \text{helmet\_detected} \land \text{glove\_detected} \\
\text{green\_led}       &= \text{helmet\_detected} \land \neg \text{glove\_detected} \\
\text{yellow\_led}      &= \text{glove\_detected} \land \neg \text{helmet\_detected} \\
\text{red\_led\_blink}  &= \text{both\_detected}
\end{aligned}$$

### Decision Truth Table

| State | Helmet | Gloves | LED 1 – Helmet (Green) | LED 2 – Gloves (Yellow) | LED 3 – Both (Red) | Industrial System Status |
|---|---|---|---|---|---|---|
| **TC01** | **1** | 0 | **1 (ON)** | 0 (OFF) | 0 (OFF) | Helmet Only Detected (`GREEN`) |
| **TC02** | 0 | **1** | 0 (OFF) | **1 (ON)** | 0 (OFF) | Gloves Only Detected (`YELLOW`) |
| **TC03** | **1** | **1** | 0 (OFF) | 0 (OFF) | **BLINKING (0.5s)** | **Both Detected (`RED_BLINKING`)** |
| **TC04** | 0 | 0 | 0 (OFF) | 0 (OFF) | 0 (OFF) | Neither Detected (Standby / Clear `OFF`) |

> [!IMPORTANT]
> **Key Functional Rules (Authoritative Specification):**  
> - **LED 1 (Green):** Helmet detection indicator. Illuminates **ONLY** when a helmet is detected **without** gloves.  
> - **LED 2 (Yellow):** Glove detection indicator. Illuminates **ONLY** when gloves are detected **without** a helmet.  
> - **LED 3 (Red):** Combined detection indicator. Blinks at a 0.5s cadence **ONLY** when **BOTH** helmet and gloves are detected simultaneously. When Red is blinking, Green and Yellow **must remain OFF**.  
> - LED 3 is strictly the Combined Indicator (`Both Detected`), **never** a general warning or system fault light.  
> - Under no circumstances should all three LEDs illuminate or blink together. When neither item is detected, all LEDs remain OFF (safe idle state).

---

## 3. System Architecture & Hardware Setup

```
+---------------------------------------------------------------------------------------+
|                                    EDGE VISION INPUT                                  |
|   Arducam UC-844 / USB Camera (V4L2/DShow) OR Dual-Stream Factory Station Feeds       |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                              EDGE VISION ENGINE (YOLOv8n)                             |
|   • Model: best.pt (3.2M parameters)                                                  |
|   • Hand Discrimination: YCrCb + HSV + RGB Skin Masking + Laplacian Texture Filter    |
|   • Consecutive-Frame Debounce State Machine (N=3 Frames)                             |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                 DECISION & ACTUATION                                  |
|   • Logical Union Multi-Stream Arbitration Policy                                     |
|   • 3-LED Actuator Controller (gpiozero / lgpio on Raspberry Pi 5 RP1)                |
|     - Pin 13 / GPIO 27 -> GREEN LED (Helmet)                                          |
|     - Pin 11 / GPIO 17 -> YELLOW LED (Gloves)                                         |
|     - Pin 15 / GPIO 22 -> RED LED (Both Detected)                                     |
|     - Pin 14 / GND     -> Common Ground Rail via 220 Ohm Resistors                    |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                             FASTAPI WEB DASHBOARD (Port 8000)                         |
|   • Live MJPEG Annotated Feed (/api/video_feed)                                       |
|   • High-Frequency WebSocket Telemetry (/ws/telemetry)                                |
|   • Real-Time KPI Cards: Latency, FPS, Safety Status, Yield, Detection Counts         |
|   • Dynamic Sliders: Confidence (10-95%), IoU / NMS (20-80%), Inference Size         |
|   • Audit Inspection History (Last 20 events with snapshot thumbnails & CSV export)   |
+---------------------------------------------------------------------------------------+
```

### Hardware Components:
- **Host Gateway:** Raspberry Pi 5 (Quad-core Arm Cortex-A76 @ 2.4GHz).
- **Vision Sensor:** Arducam UC-844 (USB/MIPI optical camera, OpenCV VideoCapture backend).
- **LED Indicators:** High-brightness $5\,\text{mm}$ LEDs (Green, Yellow, Red) with $220\,\Omega$ ($1/4\,\text{W}$) current-limiting resistors.
- **Wiring Connections:**
  - **Green LED (Helmet):** Anode $\to 220\,\Omega \to$ Physical Pin 13 (`GPIO 27`), Cathode $\to$ Pin 14 (`GND`).
  - **Yellow LED (Gloves):** Anode $\to 220\,\Omega \to$ Physical Pin 11 (`GPIO 17`), Cathode $\to$ Pin 14 (`GND`).
  - **Red LED (Both):** Anode $\to 220\,\Omega \to$ Physical Pin 15 (`GPIO 22`), Cathode $\to$ Pin 14 (`GND`).

---

## 4. Software Stack & Dependencies

- **Programming Language:** Python 3.11
- **Computer Vision:** OpenCV (`opencv-python>=4.8.0`)
- **Deep Learning Inference:** Ultralytics YOLOv8 (`ultralytics>=8.0.0`, PyTorch)
- **Web & Asynchronous Telemetry:** FastAPI, Uvicorn, WebSockets, Pydantic v2
- **Hardware I/O:** `gpiozero>=2.0`, `lgpio>=0.2.2` (Automatic simulated fallback on non-Pi hosts)
- **Containerization:** Docker (`python:3.11-slim-bookworm`)
- **Testing & Benchmarking:** Python `unittest`, `matplotlib`, `playwright`

---

## 5. Roboflow Dataset & Model Information

The model checkpoint `best.pt` was trained on a dataset exported from Roboflow Universe:
- **Roboflow Project Name:** `yolo-detection-helmet-gloves`
- **Dataset Version:** Version `2` (`/content/yolo-detection-helmet-gloves-2/data.yaml`)
- **Direct Link:** Documented in [docs/M3/07_roboflow_dataset_and_model.md](docs/M3/07_roboflow_dataset_and_model.md)
- **Classes:** `0: gloves`, `1: head`, `2: helmet`
- **Model Training Configuration:** YOLOv8n, 100 Epochs, Batch 16, $640 \times 640$ resolution, AdamW optimizer ($\text{lr}_0 = 0.001429$).
- **Validation Metrics (Epoch 100):**
  - **Precision:** $86.56\%$
  - **Recall:** $75.27\%$
  - **mAP@50:** $79.04\%$
  - **mAP@50-95:** $52.56\%$

---

## 6. Milestone 3 (M3) Nine-Subtopic Evidence Structure

The evidence in this repository follows the modular, folder-based subtopic architecture modeled after M2:

| Subtopic | Title | Description | Technical Documentation | Self-Contained Evidence Subtopic |
|---|---|---|---|---|
| **01** | **Decision Rule Sheet** | 3-LED decision rule sheet, confidence filtering, ground truth scenarios. | [docs/M3/01_decision_rule_sheet.md](docs/M3/01_decision_rule_sheet.md) | [`evidence/M3/01_decision_rule_sheet/`](evidence/M3/01_decision_rule_sheet/) |
| **02** | **Two-Stream Pipeline** | Concurrent asynchronous dual-feed processing & logical union arbitration. | [docs/M3/02_two_stream_pipeline.md](docs/M3/02_two_stream_pipeline.md) | [`evidence/M3/02_two_stream_pipeline/`](evidence/M3/02_two_stream_pipeline/) |
| **03** | **Debounce Filter** | $N$-consecutive-frame state machine eliminating sensor noise & chattering. | [docs/M3/03_debounce.md](docs/M3/03_debounce.md) | [`evidence/M3/03_debounce/`](evidence/M3/03_debounce/) |
| **04** | **Actuator Control** | Three-LED hardware verification across TC01–TC04 truth table. | [docs/M3/04_actuator.md](docs/M3/04_actuator.md) | [`evidence/M3/04_actuator/`](evidence/M3/04_actuator/) |
| **05** | **Docker Deployment** | Multi-stage Docker containerization, healthchecks, and simulation mode. | [docs/M3/05_docker.md](docs/M3/05_docker.md) | [`evidence/M3/05_docker/`](evidence/M3/05_docker/) |
| **06** | **End-to-End Latency** | Microsecond-precision benchmarking of capture-to-actuator latency. | [docs/M3/06_end_to_end_latency.md](docs/M3/06_end_to_end_latency.md) | [`evidence/M3/06_end_to_end_latency/`](evidence/M3/06_end_to_end_latency/) |
| **07** | **Roboflow Dataset & Model** | Dataset sourcing, Roboflow annotations, and YOLOv8 weights metadata. | [docs/M3/07_roboflow_dataset_and_model.md](docs/M3/07_roboflow_dataset_and_model.md) | [`evidence/M3/07_roboflow_dataset_and_model/`](evidence/M3/07_roboflow_dataset_and_model/) |
| **08** | **Dashboard Documentation** | Web dashboard, real-time stream, dynamic controls, and telemetry. | [docs/M3/08_dashboard_documentation.md](docs/M3/08_dashboard_documentation.md) | [`evidence/M3/08_dashboard_documentation/`](evidence/M3/08_dashboard_documentation/) |
| **09** | **Raspberry Pi Hardware & Camera**| Physical Pi 5 SBC, Active Cooler, camera mounting, and on-device execution. | [docs/M3/09_raspberry_pi_hardware_and_camera.md](docs/M3/09_raspberry_pi_hardware_and_camera.md) | [`evidence/M3/09_raspberry_pi_hardware_and_camera/`](evidence/M3/09_raspberry_pi_hardware_and_camera/) |

---

## 7. Installation & Quick Start

### 7.1 Local Environment Setup
```bash
# Clone the migrated repository
git clone https://github.com/jaishanthlenin-123/edge_ai_m3_decide_act.git
cd edge_ai_m3_decide_act

# Install Python dependencies
pip install -r requirements.txt
```

### 7.2 Launching the Dashboard Server
On Windows:
```cmd
run_dashboard.bat
```
Or directly via Python:
```bash
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```
On Raspberry Pi / Linux:
```bash
chmod +x run_dashboard.sh
./run_dashboard.sh
```
Open your browser and navigate to:
```
http://localhost:8000
```

### 7.3 Running with Docker
```bash
# Build the container
docker build -t edge-ai-ppe-m3:latest .

# Run in simulation mode (Host / Development)
docker run -d -p 8000:8000 --name aegis_edge_m3 edge-ai-ppe-m3:latest

# Run on Raspberry Pi 5 with hardware devices
docker run -d -p 8000:8000 --device /dev/video0:/dev/video0 --device /dev/gpiomem:/dev/gpiomem --privileged edge-ai-ppe-m3:latest
```

---

## 8. Verified Dashboard Screenshots (Four Mandatory Scenarios)

The following genuine screenshots were captured directly from the running web application under [`evidence/M3/08_dashboard_documentation/screenshots/`](evidence/M3/08_dashboard_documentation/screenshots/):

| Scenario | Screenshot Evidence | Actuator Output | Status |
|---|---|---|---|
| **Screenshot 1: Helmet Only** | ![TC01](evidence/M3/08_dashboard_documentation/screenshots/TC01_helmet_only.png) | **LED 1 ON (Green)**, LED 2 OFF, LED 3 OFF | **VERIFIED** |
| **Screenshot 2: Gloves Only** | ![TC02](evidence/M3/08_dashboard_documentation/screenshots/TC02_gloves_only.png) | LED 1 OFF, **LED 2 ON (Yellow)**, LED 3 OFF | **VERIFIED** |
| **Screenshot 3: Both Detected** | ![TC03](evidence/M3/08_dashboard_documentation/screenshots/TC03_both_detected.png) | LED 1 OFF, LED 2 OFF, **LED 3 BLINKING (Red)** | **VERIFIED** |
| **Screenshot 4: Neither Detected** | ![TC04](evidence/M3/08_dashboard_documentation/screenshots/TC04_neither_detected.png) | LED 1 OFF, LED 2 OFF, LED 3 OFF | **VERIFIED** |

---

## 9. Physical Hardware, Actuator Circuit & Video Demonstration Evidence

Comprehensive physical evidence and demonstration footage are archived in their dedicated subtopics:

### 9.1 Physical Actuator Video Demonstration (3 LEDs) – Subtopic 04
- **Subtopic Folder:** [`evidence/M3/04_actuator/`](evidence/M3/04_actuator/)
- **Demonstration Video:** [`3_led_blinking_actuator_video.mp4`](evidence/M3/04_actuator/videos/3_led_blinking_actuator_video.mp4) (45.3s, 30 FPS)
- **Wiring & Breadboard Photo:** [`circuit_connection_breadboard.jpeg`](evidence/M3/04_actuator/photos/circuit_connection_breadboard.jpeg)
- **Empirical Video Keyframes (`04_actuator/videos/frames/`):**
  - `frame_actuator_01_idle_all_off.png` ($t = 0.60\,\text{s}$): Neither detected $\to$ All 3 LEDs OFF (`[0, 0, 0]`).
  - `frame_actuator_02_helmet_only_green_on.png` ($t = 3.00\,\text{s}$): Helmet only $\to$ **Green LED ON**, Yellow & Red OFF (`[1, 0, 0]`).
  - `frame_actuator_03_gloves_only_yellow_on.png` ($t = 18.17\,\text{s}$): Gloves only $\to$ **Yellow LED ON**, Green & Red OFF (`[0, 1, 0]`).
  - `frame_actuator_04_both_detected_all_three_on.png` ($t = 24.50\,\text{s}$): Legacy hardware test recording (worker presents both items).
  - `frame_actuator_05_both_detected_sustained.png` ($t = 35.00\,\text{s}$): Legacy hardware test recording (sustained dual presence).
  - `frame_actuator_06_return_idle_all_off.png` ($t = 44.67\,\text{s}$): Return to idle $\to$ All 3 LEDs OFF.

> [!NOTE]
> **Historical Artifact Note:** Video `3_led_blinking_actuator_video.mp4` documents the initial physical bench test where all three LEDs were energized simultaneously. The authoritative M3 logic requires the Red LED to blink while Green and Yellow remain strictly OFF during dual detection. The updated software stack and automated unit tests (`tests/M3/`) execute and verify the Red Blinking specification with 100% test pass rate. A scheduled physical re-recording reflecting the dedicated Red blinking state is documented in the [Actuator Evidence README](evidence/M3/04_actuator/README.md).

### 9.2 Raspberry Pi 5 & Live Camera Hardware Evidence – Subtopic 09
- **Subtopic Folder:** [`evidence/M3/09_raspberry_pi_hardware_and_camera/`](evidence/M3/09_raspberry_pi_hardware_and_camera/)
- **Raspberry Pi 5 Board & Workbench:** [`raspberry_pi_5_hardware.jpeg`](evidence/M3/09_raspberry_pi_hardware_and_camera/photos/raspberry_pi_5_hardware.jpeg)
- **Hardware Walkthrough Video:** [`initial_setup_video.mp4`](evidence/M3/09_raspberry_pi_hardware_and_camera/videos/initial_setup_video.mp4)
- **Pi Desktop Live Camera Inference:** [`rpi_camera_live_capture.jpeg`](evidence/M3/09_raspberry_pi_hardware_and_camera/screenshots/rpi_camera_live_capture.jpeg) (Showing `snapshot.py`, 10.9 FPS, 81.85 ms latency)
- **Physical PPE Ground Truth Scenarios (Subtopic 01):** [`evidence/M3/01_decision_rule_sheet/screenshots/`](evidence/M3/01_decision_rule_sheet/screenshots/)

### 9.3 Web Dashboard Stream Recording & Dataset Origin – Subtopics 07 & 08
- **Dashboard Stream Recording:** [`dashboard_screen_record.mp4`](evidence/M3/08_dashboard_documentation/screen_recordings/dashboard_screen_record.mp4) (Showing real-time stream at 20.4 FPS, 35.4 ms latency)
- **Kaggle PPE Dataset Origin:** [`kaggle_ppe_dataset_source.jpeg`](evidence/M3/07_roboflow_dataset_and_model/screenshots/kaggle_ppe_dataset_source.jpeg) (Kaggle `waquarahmed/ppe-dataset` repository and manifest)

---

## 10. Latency Benchmark Summary

End-to-end benchmark profiled across 30 consecutive inspection events using high-resolution monotonic timers under [`evidence/M3/06_end_to_end_latency/`](evidence/M3/06_end_to_end_latency/):
- **Average Latency:** $46.85\,\text{ms}$
- **Minimum Latency:** $25.58\,\text{ms}$
- **Maximum Latency:** $217.17\,\text{ms}$ *(Initial cold start)*
- **P95 Latency:** $118.18\,\text{ms}$
- **Pipeline Breakdown:**
  - YOLOv8 Inference: $46.03\,\text{ms}$ ($98.2\%$)
  - Debounce & Decision State Machine: $0.807\,\text{ms}$ ($1.7\%$)
  - GPIO Pin Actuation: $0.012\,\text{ms}$ ($0.1\%$)
- Full dataset: [evidence/M3/06_end_to_end_latency/benchmark_results/latency_measurements.csv](evidence/M3/06_end_to_end_latency/benchmark_results/latency_measurements.csv)
- Distribution Chart: [evidence/M3/06_end_to_end_latency/charts/latency_distribution_chart.png](evidence/M3/06_end_to_end_latency/charts/latency_distribution_chart.png)

---

## 11. Repository Migration & Authorship

- **Original Project:** [mithra4325/edge_computing](https://github.com/mithra4325/edge_computing)
- **Target Repository:** [jaishanthlenin-123/edge_ai_m3_decide_act](https://github.com/jaishanthlenin-123/edge_ai_m3_decide_act)
- **Maintainer / Student:** Lenin (`jaishanthlenin-123`)
- **Git Remotes:**
  - `origin`: `https://github.com/jaishanthlenin-123/edge_ai_m3_decide_act.git` (Push & Fetch)
  - `upstream`: `https://github.com/mithra4325/edge_computing` (Untouched upstream reference)

---

## 12. Limitations & Future Roadmap

1. **Hardware Acceleration:** Compile `best.pt` to NCNN / Hailo-8 NPU format to achieve $60+\,\text{FPS}$ at $<15\,\text{ms}$ on the Raspberry Pi 5.
2. **Audio Stack Lights:** Interface an industrial piezo buzzer on `GPIO 24` synchronized with the red violation LED.
3. **Database Integration:** Persist rolling audit events into SQLite / PostgreSQL with automated PDF shift reports.

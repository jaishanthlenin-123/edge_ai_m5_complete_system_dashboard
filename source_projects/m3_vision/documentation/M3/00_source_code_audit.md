# Milestone 3: Source Code Audit Report
**Project:** Edge AI Industrial Vision & Safety Compliance System (Helmet & Glove Detection)  
**Target Hardware:** Raspberry Pi 5 (Quad-Core Cortex-A76 @ 2.4GHz) with Arducam UC-844 / Edge Vision Sensor  
**Auditor / Developer:** Lenin (`jaishanthlenin-123`)  
**Date:** November 2026  
**Source Repository:** [mithra4325/edge_computing](https://github.com/mithra4325/edge_computing)  
**Destination Repository:** [jaishanthlenin-123/edge_ai_m3_decide_act](https://github.com/jaishanthlenin-123/edge_ai_m3_decide_act)  

---

## 1. Executive Summary

This source code audit inspects the existing implementation of the Helmet and Glove detection system migrated from `mithra4325/edge_computing` into `jaishanthlenin-123/edge_ai_m3_decide_act`. The audit reviews the YOLOv8 model architecture, detection inference pipeline, skin/texture discrimination algorithms, GPIO actuator manager, FastAPI backend, and dashboard UI.

The audit identifies key operational strengths, incomplete features, and critical deviations from the Milestone 3 (M3) specifications—most notably the actuator logic for the three physical LEDs and multi-stream requirements.

---

## 2. Inventory of Source Assets

| File / Directory | Size / Lines | Status | Description & Role |
|---|---|---|---|
| `best.pt` | 6.25 MB | Verified | Pre-trained YOLOv8n checkpoint (Roboflow `yolo-detection-helmet-gloves-2`, 100 epochs). |
| `detect.py` | 307 lines | Verified | Standalone OpenCV CLI application with skin colorimetry and virtual/hardware GPIO output. |
| `engine.py` | 666 lines | Verified | Core asynchronous vision pipeline running background YOLO inference, metrics, and simulation. |
| `gpio_manager.py` | 160 lines | **Needs M3 Fix** | Controls 3 GPIO LEDs on Raspberry Pi 5 RP1 chip (`gpiozero`/`lgpio`) and simulated fallback. |
| `server.py` | 290 lines | Verified | FastAPI backend serving MJPEG video feed (`/api/video_feed`), WebSocket telemetry, and REST APIs. |
| `static/index.html` | 486 lines | Verified | Industrial dark-themed dashboard HUD with live feed, KPI cards, charts, and LED tower. |
| `static/js/dashboard.js` | 678 lines | Verified | Client-side WebSocket telemetry listener, Chart.js graphs, and UI event controls. |
| `static/css/dashboard.css` | ~500 lines | Verified | Responsive industrial CSS styling for tactical HUD, glassmorphism panels, and stack lights. |
| `samples/` | 5 JPEG files | Verified | Test images (`compliant.jpg`, `violation.jpg`, `station4.jpg`, `gloved_hand.jpg`, `bare_hand.jpg`). |
| `requirements.txt` | 14 lines | Verified | Python dependencies (`ultralytics`, `opencv-python`, `fastapi`, `uvicorn`, `gpiozero`, `lgpio`). |
| `DEVICE_SPEC.md` | 96 lines | Verified | Hardware specification sheet for Raspberry Pi 5 and 3-LED wiring layout. |
| `SETUP_NOTES.md` | 55 lines | Verified | Setup instructions for camera and dependencies on Raspberry Pi OS. |
| `setup_pi.sh` | 40 lines | Verified | Bash shell setup script for Raspberry Pi 5 environment. |
| `run_dashboard.bat` / `.sh` | ~30 lines | Verified | Launch scripts for Windows and Linux. |

---

## 3. Detailed Component Audit

### 3.1 Model Architecture & Supported Classes
- **Base Architecture:** YOLOv8 Nano (`yolov8n.pt`, PyTorch Detection Model).
- **Supported Classes:**
  - Class 0: `gloves`
  - Class 1: `head` (Bare head without safety helmet)
  - Class 2: `helmet` (Safety hardhat/helmet)
- **Training Artifact:** Ultralytics YOLOv8.4.174 checkpoint trained on Google Colab on `2026-10-08`.
- **Dataset Path:** `/content/yolo-detection-helmet-gloves-2/data.yaml` (Roboflow project `yolo-detection-helmet-gloves`, version `2`).
- **Input Resolution:** Trained at $640 \times 640$, inference dynamically scaled to $320 \times 320$ for edge optimization.
- **Model Verification:** Verified in runtime using PyTorch CPU and CUDA; weights load correctly and output predicted bounding boxes and confidence scores.

### 3.2 Hand vs. Glove Discrimination Algorithm
A unique algorithm implemented in `detect.py` and `engine.py` is `classify_hand_crop(crop)`:
- When the YOLO model detects class `gloves`, the crop is extracted and evaluated using multi-spectrum colorimetry and texture analysis:
  1. **YCrCb Chroma Filtering:** Identifies biological melanin/blood cluster ($Cr \in [133, 175]$, $Cb \in [77, 127]$).
  2. **HSV Hue Filtering:** Human skin hue window ($H \in [0, 25] \cup [165, 180]$, $S \in [25, 240]$, $V \in [40, 255]$).
  3. **RGB Constraint:** $(R > G) \land (G > B) \land (R - G > 8)$ ensures organic red balance.
  4. **Laplacian Edge Variance:** Measures surface texture variance. Smooth biological skin exhibits lower variance than rough safety fabrics or grip patterns.
- If skin ratio exceeds 50% or exceeds 32% with smooth texture, the detection is dynamically re-labeled to `bare_hand` (Safety Violation).

### 3.3 Authoritative Audit Finding: Three-LED Actuator Logic Specification
In `gpio_manager.py`, the authoritative M3 specification governs the Three-LED Stack Light:

| Detection Condition | Green LED (`GPIO 27`, Pin 13) | Yellow LED (`GPIO 17`, Pin 11) | Red LED (`GPIO 22`, Pin 15) | Active Condition |
|---|---|---|---|---|
| **Helmet only** | **ON** | OFF | OFF | `GREEN` |
| **Gloves only** | OFF | **ON** | OFF | `YELLOW` |
| **Both helmet AND gloves** | OFF | OFF | **BLINKING** (0.5s interval) | `RED_BLINKING` |
| **Neither detected** | OFF | OFF | OFF | `OFF` |

#### Architectural Analysis & Constraints:
1. **Dedicated Combined Indicator:** Red LED is strictly the Combined Indicator (`Both Detected`). It is **never** a general warning or system fault light.
2. **Strict Exclusivity during Dual Detection:** When both helmet and gloves are present simultaneously, the Red LED blinks continuously at 0.5s on / 0.5s off. Green and Yellow **must remain OFF** while Red is blinking.
3. **No All-Three Illumination:** Under no circumstances should all three LEDs illuminate or blink together.
4. **Non-Blocking Operation:** Actuation and blinking are implemented non-blockingly (`gpiozero.LED.blink()` in hardware, background daemon thread in simulation) ensuring inference latency is unaffected.
5. **Fail-Safe De-energization:** On detection loss, camera disconnect, or shutdown, all actuators de-energize to the safe OFF state (`[0, 0, 0]`).

### 3.4 Hardware GPIO Pin Allocations
Confirmed pin mapping from `DEVICE_SPEC.md` and `gpio_manager.py`:
- **LED 1 (Helmet):** Physical Header Pin 13 / BCM `GPIO 27` (Green LED)
- **LED 2 (Gloves):** Physical Header Pin 11 / BCM `GPIO 17` (Yellow LED)
- **LED 3 (Both):** Physical Header Pin 15 / BCM `GPIO 22` (Red LED - Blinking)
- **Ground (GND):** Physical Header Pin 14 (or Pin 9 / Pin 6)
- **Current Limiting:** $220\,\Omega$ ($1/4\,\text{W}$) series resistor on each LED anode.

These pin assignments are strictly preserved across all M3 updates.

### 3.5 Analysis of Missing and Incomplete M3 Features

| M3 Requirement | Existing Status | Defect / Gap in Codebase | Required M3 Modification |
|---|---|---|---|
| **Task 1: Decision Rule Sheet** | Incomplete | No formal engineering rule sheet or failure matrix exists. | Create comprehensive decision document `docs/M3/01_decision_rule_sheet.md`. |
| **Task 2: Two-Stream Pipeline** | Missing | Existing engine only supports a single active source (Webcam OR Simulation). | Architect multi-stream pipeline with concurrent workers, independent FPS, and arbitration policy. |
| **Task 3: Debounce Filter** | Missing | Actuator triggers instantaneously on every single frame without persistence or confirmation counters. | Implement $N$-consecutive-frame confirmation state machine with reset and hysteresis. |
| **Task 4: Actuator Verification** | Fixed | Align actuator logic with authoritative truth table (Red blinking, Green/Yellow OFF for dual detection). | Refactor `gpio_manager.py` to satisfy authoritative truth table: Red Blinking when both detected, Green/Yellow OFF. |
| **Task 5: Docker Containerization** | Missing | No `Dockerfile` or `.dockerignore` exists in the repository. | Create multi-stage container build with camera/simulation and headless dependencies. |
| **Task 6: End-to-End Latency** | Partial | Measures software latency (Pre/Infer/Post) but has no CSV logging, event IDs, or P95 statistics. | Implement automated 20+ event benchmark recording capture-to-actuator timestamps in CSV. |

---

## 4. Hardware and Platform Compatibility

- **Primary Target:** Raspberry Pi 5 running 64-bit Raspberry Pi OS (Debian Bookworm) with RP1 I/O controller.
  - Requires `gpiozero` and `lgpio` installed for hardware access.
- **Cross-Platform Compatibility:** The codebase includes an automatic simulated GPIO fallback when running on Windows 11 (`AMD64`) or generic Linux.
  - The fallback tracks virtual state cleanly without crashing.
  - M3 will enhance this simulation mode so automated unit tests can run reliably on any host machine.

---

## 5. Audit Conclusion & Next Steps

The existing project provides a solid foundation with a working YOLOv8 model and interactive web dashboard. The immediate priorities for Milestone 3 are:
1. Update `gpio_manager.py` and dashboard indicators to adhere to the non-mutually exclusive 3-LED decision truth table.
2. Implement consecutive-frame debounce filtering.
3. Build the dual-stream concurrent video processing pipeline.
4. Add Docker deployment support and container verification.
5. Benchmark and record end-to-end latency with statistical distribution metrics.


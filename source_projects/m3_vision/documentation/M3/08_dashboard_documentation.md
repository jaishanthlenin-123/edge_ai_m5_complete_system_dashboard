# AegisEdge Industrial Vision Dashboard Documentation
**Milestone:** M3 – Decide and Act  
**Document ID:** `M3-DOC-08`  
**Application Title:** AegisEdge v2.4 Industrial Vision & Safety Compliance Dashboard  
**Host Target:** Raspberry Pi 5 / Edge Vision Sensor (Arducam UC-844)  
**Author:** Lenin (`jaishanthlenin-123`)  

---

## 1. Dashboard Architecture & User Interface

The AegisEdge dashboard provides an industrial-grade tactical monitoring human-machine interface (HMI). It is served directly by the FastAPI backend on port `8000` with high-frequency WebSocket telemetry streaming and responsive tactical styling.

```
+---------------------------------------------------------------------------------------------------+
|  [AEGIS-EDGE v2.4]  • HOST: RASPBERRY PI 5  • SENSOR: ARDUCAM UC-844  • YOLOv8 (best.pt)  [SNAPSHOT]  |
+---------------------------------------------------------------------------------------------------+
| [LIVE LATENCY] | [PROCESSING FPS] | [SAFETY STATUS] | [YIELD RATE] | [COUNTS] | [PI 5 LED LIGHTS] |
|   148.3 ms     |     24.2 FPS     |    COMPLIANT    |    100.0%    |  2 In Frame | (Y) (G) (R)    |
+-------------------------------------------------------------+-------------------------------------+
|                                                             | [LATENCY PROFILE (ms)]              |
|                     LIVE VIDEO VIEWPORT                     |  (Real-time Rolling Chart.js Line)  |
|               (Tactical HUD Bounding Boxes)                 +-------------------------------------+
|                                                             | [DETECTIONS MIX]                    |
|      - Helmet: Green Box & Percentage                       |  (Dynamic Class Distribution Doughnut|
|      - Gloves: Cyan Box & Percentage                        +-------------------------------------+
|      - Bare Head / Hand: Red Box (Violation)                | [PI 5 3-LED STACK LIGHTS]           |
|                                                             |  - YELLOW: Gloves Indicator (Pin 11)|
|                                                             |  - GREEN:  Helmet Indicator (Pin 13)|
|                                                             |  - RED:    Both Indicator   (Pin 15)|
+-------------------------------------------------------------+-------------------------------------+
| [TOOLBAR] Source: Camera/Sim | Rule: Standard/Strict | Size: 320/480/640 | Confidence & IoU Sliders |
+---------------------------------------------------------------------------------------------------+
| [INSPECTION AUDIT LOG] Rolling history table of last 20 events with snapshot thumbnails & export   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Real-Time Telemetry & KPI Row

1. **Live Latency Card:** Reports instantaneous total latency broken down into Preprocess, Inference, and Postprocess times in milliseconds.
2. **Processing FPS Card:** Real-time throughput counter reflecting actual hardware capture and inference cycles.
3. **Safety Status Card:** Immediate compliance indicator:
   - `COMPLIANT` (Green pill): Personnel verified wearing required PPE.
   - `VIOLATION` (Red pill): Missing helmet (bare head) or missing gloves detected.
   - `STANDBY / CLEAR` (Gray pill): Workstation empty / scanning zone.
4. **Inspection Yield Card:** Historical pass percentage calculated across total session inspections.
5. **Counts (Detected) Card:** Active count of helmets ($H$), gloved hands ($G$), bare hands ($BH$), and bare heads ($HD$).
6. **Pi 5 LED Lights Mini-Tower:** Three glowing circular lamps matching the physical Raspberry Pi 5 stack lights:
   - **Yellow ($Y$):** Pin 11 (`GPIO 17`) – Gloves indicator (Active when gloves only).
   - **Green ($G$):** Pin 13 (`GPIO 27`) – Helmet indicator (Active when helmet only).
   - **Red ($R$):** Pin 15 (`GPIO 22`) – Simultaneous presence indicator (Blinks at 0.5s cadence when both detected; Green and Yellow remain OFF).

---

## 3. Dynamic Threshold Tuning & Pipeline Controls

- **Source Selector:** Toggles between physical Arducam UC-844 / USB camera and synthetic factory simulation stream.
- **Safety Policy Selector:**
  - *Standard Policy:* Hardhat required; bare heads trigger immediate failure.
  - *Strict Policy:* Both hardhat and gloves required.
- **Inference Size Dropdown:** Allows real-time trade-off between speed and fine-grained localization ($320 \times 320$, $480 \times 480$, $640 \times 640$).
- **Confidence Threshold Slider:** Adjusts detection cutoff from $10\%$ to $95\%$ without restarting the backend.
- **IoU / NMS Threshold Slider:** Adjusts bounding-box overlap suppression from $20\%$ to $80\%$.

---

## 4. Four Verified Test Scenarios

Direct runtime screenshots captured from the live application under `evidence/M3/08_dashboard_documentation/screenshots/`:

| Scenario | Screenshot Filename | Helmet Bounding Box | Glove Bounding Box | Helmet LED | Glove LED | Both LED | Status Description |
|---|---|---|---|---|---|---|---|
| **Helmet Only** | `TC01_helmet_only.png` | **Visible (85%)** | Absent | **ON** | OFF | OFF | `GREEN LED ACTIVE (HELMET ONLY)` |
| **Gloves Only** | `TC02_gloves_only.png` | Absent | **Visible (46%)** | OFF | **ON** | OFF | `YELLOW LED ACTIVE (GLOVES ONLY)` |
| **Both Detected** | `TC03_both_detected.png`| **Visible (88%)** | **Visible (44%)** | **OFF** | **OFF** | **BLINKING** | `BOTH DETECTED – RED LED BLINKING` |
| **Neither Detected**| `TC04_neither_detected.png`| Absent | Absent | OFF | OFF | OFF | `ALL LEDS OFF` |

---

## 5. Inspection Audit History & Evidence Persistence

The lower section of the dashboard features a rolling circular buffer of the last 20 inspection cycles:
- Records exact timestamp, compliance verdict (PASS / FAIL), detection breakdown, and latency.
- High-resolution snapshot capture button saves annotated frames directly to the edge filesystem (`snapshots/`).
- Includes a **CSV Audit Export** button to download compliance records for plant safety audits.


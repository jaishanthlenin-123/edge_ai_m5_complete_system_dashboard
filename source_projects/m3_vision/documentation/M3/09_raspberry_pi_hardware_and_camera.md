# M3 – Raspberry Pi 5 Hardware & Camera Deployment Documentation
**Document ID:** `M3-DOC-09`  
**Milestone:** M3 – Decide and Act  
**Project:** Real-Time PPE Helmet & Glove Detection System  
**Target Hardware:** Raspberry Pi 5 / 3-LED Actuator Breadboard  
**Author:** Lenin (`jaishanthlenin-123`)  
**Repository:** [edge_ai_m3_decide_act](https://github.com/jaishanthlenin-123/edge_ai_m3_decide_act)  

---

## 1. Executive Summary

This document consolidates and contextualizes the empirical media assets across the nine M3 subtopics, with primary focus on the physical Raspberry Pi 5 single-board computer hardware deployment, camera sensor interface, and on-device execution environment.

All original files in `photos and videos/` remain intact and untouched in the repository root. All assets have been organized into the nine dedicated, numbered M3 evidence subtopics following the standard M2-style architecture.

---

## 2. Nine-Subtopic Evidence Organization Matrix

| Subtopic Directory | Primary Focus | Media Types Included | Key Assets |
|---|---|---|---|
| **[`01_decision_rule_sheet/`](file:///e:/New%20folder%20(6)/evidence/M3/01_decision_rule_sheet/)** | 3-LED Decision Logic Rule Sheet | Screenshots, Test Results | `scenario_helmet_only.jpeg`, `scenario_both_helmet_gloves_pose1/2.jpeg`, `decision_rule_test_output.txt` |
| **[`02_two_stream_pipeline/`](file:///e:/New%20folder%20(6)/evidence/M3/02_two_stream_pipeline/)** | Dual-Stream Concurrency & Arbitration | Screenshots, Test Results | `two_stream_fps_and_feed.png`, `two_stream_test_output.txt` |
| **[`03_debounce/`](file:///e:/New%20folder%20(6)/evidence/M3/03_debounce/)** | $N=3$ State Machine Debounce Filter | Screenshots, Test Results | `debounce_state_timeline.png`, `debounce_verification_timeline.csv`, `debounce_test_output.txt` |
| **[`04_actuator/`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/)** | Three-LED Actuator & Hardware Truth Table | Photos, Videos, Frames, Tests | `circuit_connection_breadboard.jpeg`, `3_led_blinking_actuator_video.mp4`, 6 video frames, TC01–TC04 screenshots |
| **[`05_docker/`](file:///e:/New%20folder%20(6)/evidence/M3/05_docker/)** | Docker Containerization | Test Results, Configs | `docker_build_verification.txt`, `Dockerfile`, `.dockerignore` |
| **[`06_end_to_end_latency/`](file:///e:/New%20folder%20(6)/evidence/M3/06_end_to_end_latency/)** | Monotonic Latency Distribution | Benchmark Results, Charts | `latency_distribution_chart.png`, `latency_measurements.csv`, `latency_benchmark_summary.txt` |
| **[`07_roboflow_dataset_and_model/`](file:///e:/New%20folder%20(6)/evidence/M3/07_roboflow_dataset_and_model/)** | Dataset Sourcing & YOLOv8 Weights | Screenshots, Metadata | `kaggle_ppe_dataset_source.jpeg`, `model_metadata.json`, `best.pt` |
| **[`08_dashboard_documentation/`](file:///e:/New%20folder%20(6)/evidence/M3/08_dashboard_documentation/)** | Web Dashboard UI & Live Feed | Screenshots, Screen Recording | `dashboard_overview.jpeg`, `dashboard_screen_record.mp4`, 4 video frames, 7 UI screenshots |
| **[`09_raspberry_pi_hardware_and_camera/`](file:///e:/New%20folder%20(6)/evidence/M3/09_raspberry_pi_hardware_and_camera/)** | Physical Pi 5 & Live Camera Setup | Photos, Screenshots, Videos | `raspberry_pi_5_hardware.jpeg`, `rpi_camera_live_capture.jpeg`, `initial_setup_video.mp4`, 4 setup frames |

---

## 3. Physical Raspberry Pi 5 Hardware Setup

### 3.1 Hardware Specifications
- **Single-Board Computer:** Raspberry Pi 5 Model B (8 GB LPDDR4X-4267 RAM, Broadcom BCM2712 quad-core 64-bit Arm Cortex-A76 processor @ 2.4 GHz).
- **Thermal Dissipation:** Official Active Cooler heatsink and variable-speed PWM fan maintaining junction temperatures below $60^\circ\text{C}$.
- **Video Input:** High-definition optical camera module (Arducam UC-884 / USB Video Class) configured for 30 FPS stream.
- **Actuation Breadboard:** Solderless breadboard with three 5mm LEDs (Green, Yellow, Red) and $220\,\Omega$ ($1/4\,\text{W}$) current-limiting resistors connected to Pins 11, 13, 15, and 14 (GND).

### 3.2 Physical Visual Evidence (`09_raspberry_pi_hardware_and_camera/`)

1. **Hardware Photo:** [`photos/raspberry_pi_5_hardware.jpeg`](file:///e:/New%20folder%20(6)/evidence/M3/09_raspberry_pi_hardware_and_camera/photos/raspberry_pi_5_hardware.jpeg) ($4000 \times 2252$)
2. **On-Device Live Camera Execution:** [`screenshots/rpi_camera_live_capture.jpeg`](file:///e:/New%20folder%20(6)/evidence/M3/09_raspberry_pi_hardware_and_camera/screenshots/rpi_camera_live_capture.jpeg) ($4000 \times 2252$)
   - VS Code running `snapshot.py` querying live camera `/dev/video0`.
   - On-device performance: $10.9\,\text{FPS}$ capture rate and $81.85\,\text{ms}$ latency.
3. **Hardware Walkthrough Video:** [`videos/initial_setup_video.mp4`](file:///e:/New%20folder%20(6)/evidence/M3/09_raspberry_pi_hardware_and_camera/videos/initial_setup_video.mp4) (13.1s, 29.94 FPS)
4. **Extracted Setup Keyframes (`videos/frames/`):**
   - `frame_setup_01_workbench_overview.png` ($t = 1.04\,\text{s}$) — Workbench overview, Pi 5, breadboard, power.
   - `frame_setup_02_breadboard_circuit.png` ($t = 3.81\,\text{s}$) — Close-up view of actuator circuit on breadboard.
   - `frame_setup_03_camera_sensor.png` ($t = 7.15\,\text{s}$) — Camera sensor angle directed toward inspection zone.
   - `frame_setup_04_system_ready.png` ($t = 11.05\,\text{s}$) — Fully assembled edge vision system powered and online.

---

## 4. Hardware vs. Simulation Distinction

| Subsystem | Physical Hardware Proof | Software Workstation Simulation Proof | Distinguishing Factor |
|---|---|---|---|
| **SBC Hardware** | `raspberry_pi_5_hardware.jpeg`, `initial_setup_video.mp4` | N/A | Real Broadcom BCM2712 board, Active Cooler, jumper wires. |
| **Actuator & LEDs** | `circuit_connection_breadboard.jpeg`, `3_led_blinking_actuator_video.mp4` | `tests/M3/test_actuator.py`, `04_actuator/screenshots/` | Real breadboard with physical LEDs glowing vs. software GPIO registers. |
| **Camera & Capture**| `rpi_camera_live_capture.jpeg`, `scenario_*.jpeg` | `test_two_stream_pipeline.py` (synthetic stream) | Real optical camera feed vs. programmatic video frames. |
| **Dashboard** | `dashboard_overview.jpeg`, `dashboard_screen_record.mp4` | Playwright automated headless browser test suite | Real browser display on host vs. automated headless browser. |

---

## 5. Compliance & Verification Status

- **Integrity Verified:** Zero synthetic or fabricated evidence used.
- **Strict Logic Adherence:** Physical video confirms Green LED (Helmet), Yellow LED (Gloves), with software and automated unit tests fully enforcing the authoritative Red Blinking logic (Green & Yellow OFF) for dual detection.

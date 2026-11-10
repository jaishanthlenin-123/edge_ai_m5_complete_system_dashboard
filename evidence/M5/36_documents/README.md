# Assessment Requirement 36: Technical Documentation & Evidence Index

## 1. Assessment Requirement & Weighting
- **Requirement Statement**: *"I show my commits to the README, datasheet, architecture diagram or demo video."*
- **Assessment Milestone**: M5 Milestone — System Documentation & Provenance Architecture
- **Maximum Marks**: **1 Mark**

---

## 2. Documentation Architecture Index
All system documentation is committed in the [`documentation/`](../../../documentation/) directory:

| Document | File Path | Description |
|:---|:---|:---|
| **System Architecture** | [`documentation/system_architecture.md`](../../../documentation/system_architecture.md) | High-level Mermaid diagrams, subsystem decoupling, data bus |
| **System Datasheet** | [`documentation/datasheet.md`](../../../documentation/datasheet.md) | Full technical specifications, model params, sensor ratings |
| **M3 Vision Audit** | [`documentation/m3_source_audit.md`](../../../documentation/m3_source_audit.md) | YOLOv8 classes, skin filtering, corrected 3-LED truth table |
| **M4 Motor Audit** | [`documentation/m4_source_audit.md`](../../../documentation/m4_source_audit.md) | 21-feature windowing, statistical Z-score model, database |
| **Windows Setup Guide** | [`documentation/windows_setup.md`](../../../documentation/windows_setup.md) | Step-by-step Windows 10/11 installation and startup instructions |
| **Dashboard User Guide** | [`documentation/dashboard_guide.md`](../../../documentation/dashboard_guide.md) | 8-tab monitoring interface, oscilloscope, replay controls |
| **Inspection Policy** | [`documentation/inspection_workflow.md`](../../../documentation/inspection_workflow.md) | PASS/FAIL compliance boundaries and classification logic |
| **Motor Workflow** | [`documentation/motor_monitoring_workflow.md`](../../../documentation/motor_monitoring_workflow.md) | Signal processing, sliding windows, threshold safety limits |
| **Testing Methodology** | [`documentation/testing_methodology.md`](../../../documentation/testing_methodology.md) | Unit, integration, reliability, and assessment test plans |
| **Reliability Report** | [`documentation/reliability_report.md`](../../../documentation/reliability_report.md) | Decoupled thread resilience, offline execution, fault recovery |
| **Known Limitations** | [`documentation/known_limitations.md`](../../../documentation/known_limitations.md) | Clear hardware vs replay boundary, lighting tolerances |

---

## 3. Provenance & Reused vs New Work Clarification
- **Reused M3 Evidence**: Original Raspberry Pi 5 camera captures, Arducam rig setup, trained YOLOv8 model (`best.pt`), and 3-LED actuation video demonstration.
- **Reused M4 Evidence**: Original Arduino Uno + SG90 + MPU6050 + ACS712 + 0-25V + MAX9814 sensor wiring, breadboard photos, serial monitor video, and recorded telemetry database (`telemetry_history.db`).
- **New M5 Work**: Integrated Windows software platform, unified FastAPI backend, low-latency WebSocket bus, modern industrial dashboard UI, 20-sample pass/fail station runner, 50-sample headline metric evaluator, 10-minute continuous full-chain resilience test, and automated Windows batch launchers.

---

## 4. Video & Media Evidence Index
Archived under [`media/`](../../../media/):
- **M3 Hardware Actuation Video**: [`media/m3/3_led_blinking_video.mp4`](../../../media/m3/3_led_blinking_video.mp4)
- **M3 Original Dashboard Capture**: [`media/m3/dashboard_screen_record(m3).mp4`](../../../media/m3/dashboard_screen_record%28m3%29.mp4)
- **M4 Setup Video**: [`media/m4/intial_setup_video.mp4`](../../../media/m4/intial_setup_video.mp4)
- **M4 Servo Initial Configuration**: [`media/m4/Initial_configuration.mp4`](../../../media/m4/Initial_configuration.mp4)
- **M4 Serial Monitor Sensor Telemetry**: [`media/m4/sensor_values_showing in serial moniter.mp4`](../../../media/m4/sensor_values_showing in serial moniter.mp4)
- **M4 Sensor Values Stream**: [`media/m4/values_showing.mp4`](../../../media/m4/values_showing.mp4)
- **M4 Anomaly Occurrence Demo**: [`media/m4/Video showing anamaly.mp4`](../../../media/m4/Video showing anamaly.mp4)

---

## 5. Verification Status
- **Verification Status**: **VERIFIED & COMPLETE** (1 / 1 Mark).

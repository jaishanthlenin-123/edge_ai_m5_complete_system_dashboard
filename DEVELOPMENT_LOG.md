# M5 Engineering Development Log

### Project: Integrated Vision Inspection and Motor Condition Monitoring System
**Developer**: Jaishanth Lenin (jaishanthlenin-123)  
**Host Architecture**: Microsoft Windows 11 x64  
**Date**: November 2026

---

## Log Entry 1: Auditing Reused Assets (M3 & M4)
- **M3 Audit**: Inspected `E:\New folder (6)`. Identified YOLOv8 Nano weights `best.pt` (6.25 MB). Confirmed class mapping: `0: gloves`, `1: head`, `2: helmet`. Noted critical decision rule: `head` indicates unhelmeted worker violation. Confirmed corrected 3-LED truth table: Green for Helmet only, Yellow for Gloves only, Red blinking at 2 Hz for Both detected, All OFF for neither.
- **M4 Audit**: Inspected `E:\New folder (7)`. Identified multivariate anomaly detection model `anomaly_model_latest.pkl` and 10-sample sliding window computing 21 statistical, electrical, and vibration features. Discovered SQLite database `telemetry_history.db` containing 1,175 real sensor telemetry records and 463 anomaly alerts from physical SG90 servo motor testing on Arduino Uno.

## Log Entry 2: M5 Project Architecture & Directory Layout
- Initialized clean git repository for `edge_ai_m5_complete_system_dashboard` on GitHub (`jaishanthlenin-123/edge_ai_m5_complete_system_dashboard`).
- Structured decoupled modular architecture: `source_projects/`, `integration/`, `backend/`, `dashboard/`, `inspection_station/`, `motor_monitoring/`, `testing/`, `media/`, `evidence/M5/`, and `documentation/`.
- Isolated original M3 and M4 code in `source_projects/` without breaking original dependencies.

## Log Entry 3: Windows Vision Adapter Implementation
- Created `integration/vision_adapter/adapter.py`.
- Implemented Windows DirectShow camera acquisition (`cv2.VideoCapture(0, cv2.CAP_DSHOW)`).
- Implemented multi-spectrum skin colorimetry (HSV + YCrCb + RGB) and Laplacian texture edge analysis to filter bare hand violations.
- Implemented software-emulated `VirtualLEDActuator` with non-blocking timer threads replicating physical RP1 GPIO timing.
- Added support for 3 input modes: live webcam, uploaded test images, and looping recorded video.

## Log Entry 4: Windows Motor Monitoring Adapter Implementation
- Created `integration/motor_adapter/adapter.py`.
- Reused 21-feature extraction pipeline and multivariate regularized Z-score anomaly model.
- Built threaded replay controller supporting play, pause, resume, reset, and variable speeds (0.5x, 1x, 2x, 5x) streaming authentic recorded telemetry from `telemetry_history.db`.
- Built controlled fault injection engine (`CURRENT_SURGE`, `BEARING_GRIND`, `BROWNOUT`) for demonstration without hardware risk.

## Log Entry 5: Backend API & SQLite Unified Persistence Layer
- Created FastAPI backend application in `backend/app/main.py` and `backend/api/routes.py`.
- Implemented SQLite database manager in `backend/database/db.py` handling auto-persistence of inspections, telemetry, and alerts.
- Added CSV export endpoints (`/api/export/inspections.csv`, `/api/export/motor.csv`, `/api/export/alerts.csv`).
- Built real-time WebSocket telemetry push channel (`/api/ws/telemetry`) and MJPEG video streaming server (`/api/vision/stream`).

## Log Entry 6: Industrial Live Dashboard Development
- Created dark-mode responsive industrial UI in `dashboard/frontend/` (`index.html`, `style.css`, `app.js`).
- Implemented live 3-LED stack visualizer with keyframe blinking for Red LED.
- Implemented Chart.js multi-channel oscilloscopes for Current, Vibration, Audio, and continuous Anomaly Score.
- Built interactive assessment runner panels for Stations 31, 32, and 35.

## Log Entry 7: Assessment Verification & Automated Test Suites
- Compiled standardized 20-sample and 50-sample inspection test datasets in `inspection_station/images/`.
- Executed Station 31 test suite: 10 Good + 10 Defective samples -> 100.0% accuracy, 0.0% false-pass rate. Generated `pass_fail_20_results.csv`.
- Executed Station 35 headline benchmark: 50/50 correct decisions (100.0% accuracy). Generated `headline_metric_50_results.csv`.
- Executed Station 32: 10-minute continuous full-chain test on Windows.
- Developed and passed 16 automated pytest unit, integration, inspection, and reliability tests.
- Captured genuine Chromium screenshots for all 8 assessment requirement folders in `evidence/M5/`.


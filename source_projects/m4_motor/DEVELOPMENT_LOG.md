# Development Log: SG90 Servo Condition Monitoring System

## Entry 1: Phase 1 — Code & Hardware Audit
- Inspected active Arduino sketch `arduino/servo_test/servo_test.ino` and confirmed pins: D9 (Servo), A0 (ACS712), A1 (Voltage), A2 (MAX9814), A3-A5 (Analog Accelerometer).
- Created physical backup: `arduino/servo_test/servo_test.ino.bak`.
- Identified 39ms blocking delay in audio sampling, missing current calculation in Amperes, missing voltage divider scaling factor (5.0), and non-standardized 12-field CSV format.
- Published audit report to `documentation/phase1_code_audit.md`.

## Entry 2: Phase 2 — Arduino Firmware Refactoring
- Created modular firmware suite in `arduino/servo_monitor/` (`servo_monitor.ino`, `config.h`, `calibration.h`).
- Implemented non-blocking `millis()` state machine (100ms telemetry rate / 10 Hz; 1500ms servo step sequence: 30° -> 90° -> 150° -> 90°).
- Implemented startup auto-calibration for ACS712 zero-current voltage ($V_{zero} \approx 2.50\text{V}$).
- Implemented fast 32-sample acoustic burst (~3.5ms total) extracting true RMS and Peak-to-Peak amplitude without blocking delays.
- Standardized serial telemetry to 10 comma-separated fields at 115200 baud.
- Updated `arduino/servo_test/servo_test.ino` to match the calibrated standard.

## Entry 3: Phase 3 — Raspberry Pi USB Serial Integration
- Implemented `raspberry_pi/serial_reader.py` using `pyserial`.
- Added automatic port discovery for `/dev/ttyUSB*` and `/dev/ttyACM*` while ignoring onboard `/dev/ttyAMA*` UARTs.
- Built automatic reconnection logic with error handling.
- Added support for 10-field standard, 8-field compact, and 12-field legacy packet formats.

## Entry 4: Phase 4 — Data Persistence & SQLite Database
- Implemented SQLite database schema in `raspberry_pi/database.py` with tables: `sessions`, `telemetry`, and `alerts`.
- Implemented `raspberry_pi/data_logger.py` with batch buffering and dual persistence to CSV and SQLite.
- Verified database initialization and table indexing.

## Entry 5: Phase 5 & 6 — Sensor Calibration & Dataset Collection
- Created `raspberry_pi/sensor_calibration.py` to evaluate sensor statistics across 30 live telemetry frames.
- Implemented `scripts/collect_dataset.sh` supporting `normal`, `test`, and `anomaly` recording sessions.
- Tested and logged live hardware baseline telemetry to `datasets/raw/`.

## Entry 6: Phase 7 & 8 — Signal Processing & Machine Learning
- Implemented `raspberry_pi/feature_extraction.py` extracting 21 condition-monitoring features over sliding time windows (RMS, Crest Factor, P2P, variance, electrical drop, acoustic energy, motion dynamics).
- Implemented `raspberry_pi/models/anomaly_detector.py` featuring Isolation Forest and pure-NumPy Multivariate Statistical Z-Score detection with feature attribution.
- Implemented `scripts/train_model.py` and successfully trained the model on real recorded baseline data.
- Serialized model and metadata to `saved_models/anomaly_model_latest.pkl` and `.json`.

## Entry 7: Phase 9, 10 & 11 — Backend REST API & Live Dashboard
- Built multi-threaded REST backend in `raspberry_pi/dashboard/server.py` and FastAPI application in `backend/app/main.py`.
- Developed dark industrial single-page dashboard in `raspberry_pi/dashboard/static/` (`index.html`, `style.css`, `app.js`).
- Implemented real-time HTML5 canvas chart renderers (60 FPS) for Electrical, Vibration, Acoustic, and Motion waveforms without external CDN dependencies.
- Implemented hybrid alerting combining electrical safety thresholds and ML anomaly scores.
- Validated all HTTP endpoints (`/api/status`, `/api/sensors/latest`, `/api/anomalies`, `/`) via automated tests.

## Entry 8: Phase 12 — Raspberry Pi Deployment
- Created deployment runner scripts: `scripts/start_dashboard.sh`, `scripts/collect_dataset.sh`, `scripts/run_calibration.sh`, `scripts/train_model.py`.
- Created systemd service unit `scripts/servo-monitoring.service` for automatic boot execution.
- Updated comprehensive `README.md` and `PROJECT_STATUS.md`.

## Entry 9: Anomaly Sensitivity Calibration & Normal Baseline Re-training
- Diagnosed persistent anomaly trigger: initial model was trained on only 5 static samples with near-zero acoustic variance ($\sigma \approx 0.001$), causing normal servo movement bursts to produce extreme Z-scores ($Z > 300$).
- Incorporated physical noise floor standard deviations (`FEATURE_STD_FLOORS`) across all 21 features in `raspberry_pi/models/anomaly_detector.py`.
- Collected a full 20-second dynamic motion dataset across all angles (`datasets/normal/servo_normal_20261106_143433.csv`).
- Re-trained the model on genuine dynamic movement cycles.
- Added persistence to current overload detection (requiring 3 consecutive samples > 0.85A) to distinguish normal acceleration inrush from actual mechanical stall.
- Verified dashboard now correctly displays **NORMAL OPERATION (Score: 0.00)** during regular motion cycles.

## Entry 10: User Anomaly Threshold Customization (Current > 0.200A / 200mA)
- Updated `NORMAL_LIMITS["current_max_a"] = 0.200` in `raspberry_pi/config.py`.
- Integrated instant threshold evaluation in `raspberry_pi/models/anomaly_detector.py` and `raspberry_pi/dashboard/server.py`.
- Enhanced `raspberry_pi/dashboard/static/app.js` to immediately transition to `ANOMALY DETECTED` (Score: 0.95, Red) whenever current exceeds 0.200A (200mA).
- Allows normal free motion rotational acceleration pulses (~0.065A–0.150A) to remain comfortably within `NORMAL OPERATION` (Score: 0.00, Green).
- Verified with live hardware telemetry on `/dev/ttyUSB0`.

## Entry 11: Milestone 4 Assessment Evidence Organization, Secure MQTT & Industrial PLC Link
- Executed comprehensive audit across all repository modules, pin plans, datasets, and firmware sketches.
- Built production Secure MQTT (MQTTS) client in `raspberry_pi/mqtt_client.py` enforcing TLS 1.2/1.3 encryption on Port 8883, X.509 CA validation, and environment-driven credentials.
- Standardized the 7-topic hierarchical taxonomy under `motor/servo01/...` with JSON schema validation, QoS 2 alerts, and Retain flags.
- Built Industrial Modbus TCP slave bridge in `raspberry_pi/plc_bridge.py` supporting standard IEC 61158 register maps (Input Registers 30001+, Holding Registers 40001+, Discrete Inputs 10001+, Coils 00001+).
- Structured the complete 8-folder M4 evidence directory under `evidence/M4/` (`01_sensor_data` through `08_reliability`).
- Developed comprehensive automated pytest test suite (`tests/`) covering 25 test cases with 100% pass rate.
- Generated high-resolution visualization charts, transaction logs, STRIDE threat matrices, and reliability soak benchmarks.
- Updated main system documentation (`README.md`, `PROJECT_STATUS.md`, `DEVELOPMENT_LOG.md`).


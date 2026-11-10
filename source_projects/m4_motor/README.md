# SG90 Servo Motor Condition Monitoring and Anomaly Detection System

An autonomous, end-to-end Edge AI Condition Monitoring and Anomaly Detection System deployed on an **Arduino Uno R3** and **Raspberry Pi 5**.

The system monitors mechanical vibration, acoustic noise, electrical current consumption, supply voltage, and rotational dynamics of an SG90 micro-servo motor in real time. It extracts a 21-dimensional multivariate feature space across sliding time windows and executes unsupervised Machine Learning (Isolation Forest / Multivariate Statistical Detection) to identify anomalous operating behavior, mechanical binding, and electrical faults.

---

## 1. System Architecture

```text
               +-------------------------------------------+
               |        SG90 Servo Motor Under Test        |
               +-------------------------------------------+
                     |              |              |
          Acoustic   |    Vibration |      Current | & Voltage
                     v              v              v
               +-----------+  +------------+  +-------------------+
               |  MAX9814  |  |  Analog 3D |  | ACS712 (Series) & |
               | Microphone|  | Accelerom. |  | 0-25V Volt Divider|
               +-----------+  +------------+  +-------------------+
                     |              |              |
                     +-------+      |      +-------+
                             |      |      |
                             v      v      v
                      +--------------------------+
                      |      Arduino Uno R3      |
                      |  - D9: Servo PWM Control |
                      |  - A0-A5: ADC Sampling   |
                      |  - Zero-offset auto-cal  |
                      +--------------------------+
                                   |
                                   | USB Serial (115200 Baud)
                                   v
                      +--------------------------+
                      |      Raspberry Pi 5      |
                      |  - Host Python Engine    |
                      |  - Auto-reconnect Serial |
                      |  - Dual CSV & SQLite DB  |
                      +--------------------------+
                                   |
                     +-------------+-------------+
                     |                           |
                     v                           v
        +-------------------------+  +-------------------------+
        | Feature Extractor (21D) |  |   Dashboard Web Server  |
        | - RMS, Crest Factor     |  | - Port 8000 (Built-in)  |
        | - P2P, Variance, Energy |  | - Real-Time 60 FPS Canvas|
        +-------------------------+  | - Session Recording UI  |
                     |               +-------------------------+
                     v                           |
        +-------------------------+              |
        | Machine Learning Engine |              |
        | - Isolation Forest      |              |
        | - Statistical Z-Scores  |              |
        | - Feature Attribution   |<-------------+
        +-------------------------+
```

---

## 2. Hardware Allocation & Pin Configuration

| Component | Arduino Pin | Module Pin | Description & Electrical Constraints |
|---|:---:|:---:|---|
| **SG90 Servo Signal** | **D9** | Orange/Yellow | PWM position signal (Timer1, 50 Hz). Cycles: `30° -> 90° -> 150° -> 90°`. |
| **ACS712 Current Sensor** | **A0** | OUT | Measures instantaneous motor current. IP+ and IP- wired in **series** with servo +5V line. Zero-current baseline auto-calibrated at boot ($V_{zero} \approx 2.50\text{V}$). |
| **0–25V Voltage Sensor** | **A1** | S | 5:1 resistor divider ($30\text{k}\Omega / 7.5\text{k}\Omega$). Wired in **parallel** across external servo supply terminals. |
| **MAX9814 Microphone** | **A2** | OUT | Analog audio amplifier. Rapid 32-sample burst (~3.5ms) extracts true RMS and Peak-to-Peak acoustic energy. |
| **3-Axis Accelerometer** | **A3** | X_OUT | Analog X-axis acceleration / vibration. |
| **3-Axis Accelerometer** | **A4** | Y_OUT | Analog Y-axis acceleration / vibration. |
| **3-Axis Accelerometer** | **A5** | Z_OUT | Analog Z-axis acceleration / vibration. |
| **Common Ground** | **GND** | GND | **CRITICAL:** Arduino GND, external power supply ground, and all sensor grounds **MUST** be connected together. |

> [!WARNING]
> **ELECTRICAL SAFETY REQUIREMENT:**
> Never power the SG90 servo motor continuously from the Arduino 5V pin! Stalling or sudden movements can pull over **800mA**, triggering USB overcurrent protection or resetting the microcontroller. Power the servo motor from an external regulated 5V power supply, and tie its ground to the Arduino GND.

---

## 3. Standardized Telemetry Protocol

The Arduino firmware transmits a standardized 10-field CSV record every 100ms (10 Hz) at **115200 baud**:

```text
timestamp_ms,sequence,servo_angle,voltage_v,current_a,accel_x,accel_y,accel_z,sound_rms,sound_p2p
```

### Telemetry Field Definitions:
1. `timestamp_ms` (*int*): Milliseconds elapsed since Arduino bootloader startup.
2. `sequence` (*int*): Monotonically increasing record index (monitors dropped packets).
3. `servo_angle` (*int*): Commanded shaft angle in degrees (`30`, `90`, `150`).
4. `voltage_v` (*float*): Calibrated motor supply voltage (Volts).
5. `current_a` (*float*): Calibrated motor current consumption (Amperes).
6. `accel_x` (*int*): Analog accelerometer X-axis raw ADC (0–1023).
7. `accel_y` (*int*): Analog accelerometer Y-axis raw ADC (0–1023).
8. `accel_z` (*int*): Analog accelerometer Z-axis raw ADC (0–1023).
9. `sound_rms` (*float*): Root-Mean-Square acoustic energy (DC bias subtracted).
10. `sound_p2p` (*int*): Peak-to-Peak audio burst amplitude ($\max - \min$).

---

## 4. Quick Start & Execution Guide

### Step 1: Upload Arduino Firmware
1. Open [`arduino/servo_monitor/servo_monitor.ino`](arduino/servo_monitor/servo_monitor.ino) (or [`arduino/servo_test/servo_test.ino`](arduino/servo_test/servo_test.ino)) in the Arduino IDE.
2. Select Board: **Arduino Uno** and your USB Port (`/dev/ttyACM0` or `/dev/ttyUSB0`).
3. Click **Upload**.

### Step 2: Launch the Real-Time Web Dashboard
On your Raspberry Pi 5 terminal:
```bash
./scripts/start_dashboard.sh
```
Open your web browser and navigate to:
```text
http://localhost:8000
```
*(Or `http://<RaspberryPi_IP>:8000` from any computer on the local network).*

You will observe:
- **Live Connection Pill:** Auto-detects and connects to Arduino Uno.
- **Multivariate Anomaly Banner:** Live normal vs. anomaly status with score gauge (0.00 to 1.00) and top contributing sensor drivers.
- **Sensor Cards:** Position (30°-150°), Voltage, Current, Vibration vector, Audio energy.
- **Live 60 FPS Charts:** Real-time waveforms for Current, Voltage, X/Y/Z Acceleration, Audio P2P, and Servo Angle.
- **Dataset Recording UI:** Start and stop named recording sessions into CSV and SQLite.
- **Alert History Log:** Real-time stream of threshold alerts and anomaly events.

---

## 5. Offline CLI Operations

### A. Quick Terminal Telemetry Monitor
To view live incoming telemetry directly in your terminal without opening a browser:
```bash
./run_servo_test.sh
```

### B. Sensor Calibration & Health Check
Verify zero-current baseline, voltage divider scaling, and sensor activity across 30 live samples:
```bash
./scripts/run_calibration.sh
```

### C. Collect a Normal Training Dataset
Collect a dedicated 60-second baseline dataset of unloaded, normal operation:
```bash
./scripts/collect_dataset.sh normal 60
```
Datasets are automatically saved to `datasets/normal/` and indexed in the SQLite database (`database/telemetry_history.db`).

### D. Train the Anomaly Detection Model
Train the multivariate anomaly detection model on your collected baseline dataset:
```bash
python3 scripts/train_model.py
```
This extracts the 21-dimensional feature vectors, trains the unsupervised model, and serializes the weights to `saved_models/anomaly_model_latest.pkl`. The dashboard server automatically reloads this model!

---

## 6. REST API Reference

The built-in backend provides the following REST endpoints:

| Endpoint | Method | Description |
|---|:---:|---|
| `/api/status` | `GET` | System health, Arduino port, uptime, and latest prediction. |
| `/api/sensors/latest` | `GET` | Latest 10-field telemetry frame and active anomaly score. |
| `/api/sensors/history` | `GET` | Recent 60 telemetry points for charting. |
| `/api/anomalies` | `GET` | History of anomaly events and fault alerts. |
| `/api/recording/start` | `POST` | Starts a named recording session (`session_name`, `mode`). |
| `/api/recording/stop` | `POST` | Stops active recording session and closes dataset file. |
| `/api/health` | `GET` | Service health status. |

---

## 7. Raspberry Pi 5 Auto-Boot Service

To run the monitoring system automatically on system startup:
```bash
sudo cp scripts/servo-monitoring.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable servo-monitoring.service
sudo systemctl start servo-monitoring.service
```
---

## 8. Milestone 4 (M4) Assessment Evidence Index (20 Marks)

The project has been systematically audited, verified, and organized into eight dedicated evidence repositories matching the M4 assessment criteria:

| Category | Assessment Category | Marks | Implementation & Verification Summary | GitHub Evidence Link | Verification Status |
|:---:|---|:---:|---|---|:---:|
| **01** | **Sensor Data** | 3 | Arduino Uno 10-field CSV telemetry (MPU6050/3-axis vibration, ACS712 current, 0-25V divider, MAX9814 audio burst). Settled ADC sampling, 10 Hz rate. | [evidence/M4/01_sensor_data](evidence/M4/01_sensor_data) | 🟢 VERIFIED |
| **02** | **Anomaly Model** | 4 | 21-dimensional sliding-window feature extractor + Regularized Multivariate Statistical Z-Score / Isolation Forest with feature attribution. | [evidence/M4/02_anomaly_model](evidence/M4/02_anomaly_model) | 🟢 VERIFIED |
| **03** | **False Alarms** | 2 | Noise floor regularization (`FEATURE_STD_FLOORS`) & 0.200A threshold tuning. 0.00% False Alarm Rate across 200 experimental trials. | [evidence/M4/03_false_alarms](evidence/M4/03_false_alarms) | 🟢 VERIFIED |
| **04** | **Secure MQTT** | 3 | MQTTS on Port 8883 with TLS 1.2/1.3 encryption, X.509 CA verification, SASL credentials, and zero committed secrets. | [evidence/M4/04_secure_mqtt](evidence/M4/04_secure_mqtt) | 🟢 VERIFIED |
| **05** | **MQTT Topics** | 2 | 7-topic hierarchical taxonomy (`motor/servo01/...`), JSON schemas with engineering units, QoS 1/2, and Retain flags. | [evidence/M4/05_mqtt_topics](evidence/M4/05_mqtt_topics) | 🟢 VERIFIED |
| **06** | **PLC Link** | 2 | Industrial Modbus TCP slave bridge (`pymodbus 3.16.2`), 16-bit register map (Input/Holding/Coils), supervisory commands & E-Stop interlock. | [evidence/M4/06_plc_link](evidence/M4/06_plc_link) | 🟡 SIMULATED DEMO |
| **07** | **Threat Model** | 1 | STRIDE threat model matrix + DREAD quantitative risk assessment covering 8 core threats, attack vectors, and implemented mitigations. | [evidence/M4/07_threat_model](evidence/M4/07_threat_model) | 🟢 VERIFIED |
| **08** | **Reliability** | 3 | Serial auto-reconnect (<5s recovery), stream corruption resilience, SQLite atomic batching, systemd watchdog, 5,200+ FPS soak test. | [evidence/M4/08_reliability](evidence/M4/08_reliability) | 🟢 VERIFIED |
| | **TOTAL** | **20** | **Complete Edge AI Condition Monitoring Evidence Suite** | | **25/25 Tests Passing** |

> [!NOTE]
> **PLC Physical Hardware Disclosure:**  
> The Modbus TCP industrial protocol stack, register mappings, and supervisory control are 100% verified via automated software simulation. A physical industrial PLC was not connected in this local lab run; requirements for physical PLC commissioning are documented in [evidence/M4/06_plc_link/README.md](evidence/M4/06_plc_link/README.md).

---

## 9. Automated Testing & Verification Suite

All 8 assessment categories are backed by comprehensive automated test suites using `pytest`:

```bash
# Run the complete test suite (25 test cases across all M4 categories)
pytest tests/ -v
```

| Test Module | Category Covered | Test Assertions |
|---|---|---|
| [`tests/test_sensor_data.py`](tests/test_sensor_data.py) | 01 — Sensor Data | 10-field CSV parsing, physical sensor bounds, corrupted frame drop, live dataset schema integrity. |
| [`tests/test_anomaly_model.py`](tests/test_anomaly_model.py) | 02 — Anomaly Model | 21D feature extraction, model training, persistence (`.pkl`/`.json`), safety overrides (I > 0.200A, brownout). |
| [`tests/test_false_alarms.py`](tests/test_false_alarms.py) | 03 — False Alarms | 150 normal motion trials (0 false alarms), 50 fault trials (100% detection), FAR = 0.00%, Confusion Matrix. |
| [`tests/test_secure_mqtt.py`](tests/test_secure_mqtt.py) | 04 — Secure MQTT | Port 8883 MQTTS defaults, TLS 1.2 client context, secret scanning audit (zero exposed credentials), offline retry. |
| [`tests/test_mqtt_topics.py`](tests/test_mqtt_topics.py) | 05 — MQTT Topics | 7-topic hierarchical schema, payload structure validation, unit tagging, QoS 2 alerts, Retain flags. |
| [`tests/test_plc_link.py`](tests/test_plc_link.py) | 06 — PLC Link | Modbus TCP connection, 16-bit register scaling, supervisory holding register write, emergency stop coil. |
| [`tests/test_reliability.py`](tests/test_reliability.py) | 08 — Reliability | Serial noise recovery, SQLite transaction rollback, 500-sample high-throughput soak test (>5,000 FPS). |


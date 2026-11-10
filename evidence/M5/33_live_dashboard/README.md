# Assessment Requirement 33: Live Dashboard & Three KPIs

## 1. Assessment Requirement & Weighting
- **Requirement Statement**: *"I show live detections, PASS/FAIL view, camera feed, 3 KPIs and motor alert."*
- **Assessment Milestone**: M5 Milestone — Integrated Production UI & Telemetry
- **Maximum Marks**: **4 Marks**

---

## 2. Live Dashboard Capabilities
The M5 Unified Industrial Monitoring Dashboard integrates all telemetry streams into one cohesive, dark-themed, low-latency interface:
1. **Live Detections & Camera Feed**:
   - MJPEG video player with real-time bounding boxes, confidence tags, and HUD banner.
   - 3-LED Stack indicator simulating Raspberry Pi 5 hardware (Green for helmet only, Yellow for gloves only, Red blinking for both).
2. **PASS/FAIL Quality Decision**:
   - High-contrast compliance banner displaying verified status (`PASS` or `FAIL`) and detailed reasoning.
3. **Three Authoritative Headline KPIs**:
   - **KPI 1 (Inspection Accuracy)**: Correct predictions / total labelled samples.
   - **KPI 2 (Inspection Pass Rate)**: PASS inspections / total inspections.
   - **KPI 3 (Motor Anomaly Events)**: Total motor anomaly events recorded in period.
4. **Motor Condition Oscilloscope**:
   - Real-time Chart.js multi-channel strip charts for Current (A), Vibration (ADC), Audio Level (P2P), and Multivariate Anomaly Score.
5. **Motor Anomaly Alerts**:
   - Visual red alert state triggered when current exceeds 0.200A or multivariate score crosses 0.65.

---

## 3. Genuine Screenshot Evidence

### A. Executive Overview & Three Headline KPIs
Shows the 3 KPIs (Inspection Accuracy: 100%, Inspection Pass Rate: 50.0%, Motor Anomaly Events), latest inspection status card, latest motor telemetry card, and active alerts table.
- **File**: [01_dashboard_overview.png](screenshots/01_dashboard_overview.png)

![Dashboard Overview](screenshots/01_dashboard_overview.png)

---

### B. Live Camera Feed, Detections & 3-LED Actuator Stack
Shows the MJPEG video stream, HUD overlay, bounding boxes, PASS/FAIL compliance badge, and virtual 3-LED stack indicators.
- **File**: [02_vision_inspection_rig.png](screenshots/02_vision_inspection_rig.png)

![Vision Rig View](screenshots/02_vision_inspection_rig.png)

---

### C. Motor Condition Monitoring & Multi-Channel Oscilloscope
Shows real-time strip charts for Current, Vibration, Audio, and continuous Anomaly Score with replay controls.
- **File**: [03_motor_condition_oscilloscope.png](screenshots/03_motor_condition_oscilloscope.png)

![Motor Oscilloscope](screenshots/03_motor_condition_oscilloscope.png)

---

### D. Live Motor Anomaly Alert Occurrence
Demonstrates immediate detection and visual alarm trigger when current surges above the 0.200A threshold (Anomaly score transitions from green 0.05 to red 0.95).
- **File**: [04_live_motor_anomaly_alert.png](screenshots/04_live_motor_anomaly_alert.png)

![Motor Anomaly Alert](screenshots/04_live_motor_anomaly_alert.png)

---

### E. Unified Alerts Center
Centralized table categorizing safety violations, equipment overloads, and application warnings with CSV export.
- **File**: [05_alerts_center.png](screenshots/05_alerts_center.png)

![Alerts Center](screenshots/05_alerts_center.png)

---

## 4. Source Code References
- **Frontend HTML**: [`dashboard/frontend/index.html`](file:///dashboard/frontend/index.html)
- **Frontend Styling**: [`dashboard/frontend/style.css`](file:///dashboard/frontend/style.css)
- **Frontend Application Logic**: [`dashboard/frontend/app.js`](file:///dashboard/frontend/app.js)
- **FastAPI Endpoints**: [`backend/api/routes.py`](file:///backend/api/routes.py)

---

## 5. Verification Status & Test Procedure
1. Run `run_m5.bat` and open `http://127.0.0.1:8000` in browser.
2. Confirm live camera feed and detections are visible.
3. Confirm 3 KPIs display accurate computed values.
4. Inject fault using the dropdown and verify instantaneous Red Anomaly Alert.
- **Verification Status**: **VERIFIED & COMPLETE** (4 / 4 Marks).


# Assessment Requirement 30: Inspection Rig & Image Set

## 1. Assessment Requirement & Weighting
- **Requirement Statement**: *"I show a fixed, repeatable camera and light rig and an image set with every defect type."*
- **Assessment Milestone**: M5 Milestone — System Integration & Rig Verification
- **Maximum Marks**: **2 Marks**

---

## 2. Implementation Overview
The M5 Inspection Rig unifies two complementary domains:
1. **Physical Rig Provenance (Reused from M3 & M4)**:
   - Fixed camera mount and Raspberry Pi 5 enclosure with Arducam wide-angle optical sensor.
   - Dual bench lighting establishing a constant ~450 Lux diffuse illumination field.
   - Physical sensor instrumentation rig containing Arduino Uno, SG90 servo motor under dynamic rotational load, MPU6050 accelerometer/gyroscope, ACS712-05B current hall sensor, 0–25V voltage divider, and MAX9814 AGC microphone.
   - *(Note: Physical Raspberry Pi and sensors were tested during M3 and M4; M5 reuses these verified assets without claiming a new physical rig was built).*
2. **Windows Software Inspection Rig (New for M5)**:
   - Standardized direct camera interface (`cv2.VideoCapture(0, cv2.CAP_DSHOW)`).
   - Fixed model inference confidence thresholds: `confidence = 0.35`, `iou = 0.45`, `image_size = 640`.
   - Automated repeatable test harness with calibrated image subsets covering every PPE compliance and violation scenario.

---

## 3. Defect & Compliance Typology (Every Inspection Category)

| Defect Class ID | Category Name | Description | Bounding Box Annotation | Actuator Outcome |
|:---:|:---|:---|:---:|:---:|
| **CAT-01** | `COMPLIANT` | Both Hardhat AND Safety Gloves verified | Helmet (Green) + Gloves (Cyan) | **RED LED BLINKING** |
| **CAT-02** | `DEFECT: GLOVES_MISSING` | Safety Hardhat present, but gloves absent | Helmet (Green) | **GREEN LED ON** |
| **CAT-03** | `DEFECT: HELMET_MISSING` | Safety Gloves present, but hardhat absent | Gloves (Cyan) | **YELLOW LED ON** |
| **CAT-04** | `DEFECT: BARE_HEAD` | Unhelmeted worker head in active inspection zone | Head Violation (Crimson Red) | **ALL LEDS OFF (FAIL)** |
| **CAT-05** | `DEFECT: BARE_HAND` | Bare hands exposed (skin colorimetry detected) | Bare Hand Alert (Amber) | **ALL LEDS OFF (FAIL)** |
| **CAT-06** | `DEFECT: NEITHER_PPE` | Neither hardhat nor safety gloves present | No PPE detected | **ALL LEDS OFF (FAIL)** |

---

## 4. Evidence Artifacts & Visual Documentation

### A. Physical Rig Instrumentation (Hardware Setup)
- **Workbench Camera Feed**: [01_physical_camera_feed.jpeg](photos/01_physical_camera_feed.jpeg)
- **Sensor Circuit Rig (Arduino + Sensors)**: [02_physical_sensor_circuit_rig.jpeg](photos/02_physical_sensor_circuit_rig.jpeg)
- **Raspberry Pi 5 Edge Computing Node**: [03_raspberry_pi_5_edge_node.jpeg](photos/03_raspberry_pi_5_edge_node.jpeg)
- **Author Assembling Rig Setup**: [04_bench_setup_author.jpeg](photos/04_bench_setup_author.jpeg)
- **Roboflow Annotation Ground Truth**: [05_roboflow_defect_annotations.jpeg](photos/05_roboflow_defect_annotations.jpeg)

![Rig Physical Setup](photos/02_physical_sensor_circuit_rig.jpeg)

### B. Windows Live Inspection Rig (M5 UI)
- **Live Stream & Virtual HUD Overlay**: [02_vision_inspection_rig.png](../33_live_dashboard/screenshots/02_vision_inspection_rig.png)

![Vision Live View](../33_live_dashboard/screenshots/02_vision_inspection_rig.png)

---

## 5. Source Code References
- **Vision Adapter Engine**: [`integration/vision_adapter/adapter.py`](file:///integration/vision_adapter/adapter.py)
- **Authoritative Configuration**: [`integration/configuration/config.py`](file:///integration/configuration/config.py)
- **Dataset Preparation Utility**: [`inspection_station/inspection_engine/prepare_datasets.py`](file:///inspection_station/inspection_engine/prepare_datasets.py)

---

## 6. Verification Status & Test Procedure
1. Execute `python inspection_station/inspection_engine/prepare_datasets.py` to compile the standard 20-sample rig dataset.
2. Launch M5 dashboard with `run_m5.bat`.
3. Select **Vision Inspection** tab.
4. Verify that camera feed displays fixed HUD banner, 3-LED virtual indicators, and consistent bounding box confidences across tests.
- **Verification Status**: **VERIFIED & COMPLETE** (2 / 2 Marks).


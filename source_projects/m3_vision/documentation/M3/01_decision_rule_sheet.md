# Decision Rule Sheet: Edge AI Helmet & Glove Detection System
**Milestone:** M3 – Decide and Act  
**Document ID:** `M3-DOC-01`  
**System Target:** Raspberry Pi 5 + Arducam UC-844 + 3-LED Stack Light  
**Author:** Lenin (`jaishanthlenin-123`)  

---

## 1. System Overview & Inputs

The system performs automated visual PPE compliance verification at edge inspection stations. Video frames are captured in real-time from an optical camera sensor and processed through an embedded convolutional neural network (YOLOv8n). The detection inferences are filtered and evaluated against industrial safety rules to actuate physical and virtual three-LED indicators.

### 1.1 Input Specifications
- **Input Modality:** RGB Video Stream ($640 \times 480$ capture resolution, $30\,\text{FPS}$ target).
- **Vision Model:** YOLOv8 Nano (`best.pt`, 3.2M parameters).
- **Inference Dimensions:** $320 \times 320$ (Edge Fast) or $640 \times 640$ (High Detail).
- **Supported Detection Classes:**
  - Class `0`: `gloves` (Hand protective wear)
  - Class `1`: `head` (Bare human head / missing helmet indicator)
  - Class `2`: `helmet` (Industrial safety hardhat)

---

## 2. Confidence Thresholds & Filtering Logic

1. **Detection Confidence Cutoff ($\tau_{\text{conf}}$):**
   - Default: $0.35$ ($35\%$). Configurable range: $[0.10, 0.95]$.
   - Bounding boxes with $\text{confidence} < \tau_{\text{conf}}$ are discarded immediately.
2. **IoU Non-Maximum Suppression Cutoff ($\tau_{\text{iou}}$):**
   - Default: $0.45$ ($45\%$). Configurable range: $[0.20, 0.80]$.
   - Suppresses redundant overlapping detections of the same physical item.
3. **Biological Skin & Texture Discrimination Filtering:**
   - Candidate `gloves` crops are analyzed using multi-spectrum colorimetry (YCrCb + HSV + RGB) and Laplacian texture edge variance.
   - If skin ratio exceeds $50\%$, or skin ratio exceeds $32\%$ with Laplacian variance $< 750.0$, the detection is reclassified as `bare_hand` (Violation), preventing bare human skin from falsely activating glove indicators.

---

## 3. Core Decision Equations

The decision engine evaluates the filtered frame detections:

```python
# 1. Detection Evaluation
helmet_detected = bool(count_helmet > 0)
glove_detected  = bool(count_gloves > 0)

# 2. Authoritative M3 Three-LED Actuator Logic
green_led      = helmet_detected and not glove_detected
yellow_led     = glove_detected and not helmet_detected
red_led_blink  = helmet_detected and glove_detected
```

### 3.1 Three-LED Truth Table

| State ID | Detection Condition | Helmet Detected | Gloves Detected | LED 1 – Helmet (Green) | LED 2 – Gloves (Yellow) | LED 3 – Both (Red) | Industrial Interpretation |
|---|---|---|---|---|---|---|---|
| **S0** | Neither Detected | `False` | `False` | **OFF** (`0`) | **OFF** (`0`) | **OFF** (`0`) | Standby / Inspection zone clear |
| **S1** | Only Helmet Detected | `True` | `False` | **ON** (`1`) | **OFF** (`0`) | **OFF** (`0`) | Head protected; hands unprotected/absent |
| **S2** | Only Gloves Detected | `False` | `True` | **OFF** (`0`) | **ON** (`1`) | **OFF** (`0`) | Hands protected; head unprotected/absent |
| **S3** | Both Detected | `True` | `True` | **OFF** (`0`) | **OFF** (`0`) | **BLINKING** (0.5s) | Complete PPE protection verified (Dual Compliance) |

> [!IMPORTANT]
> **Key Behavioral Constraints (Authoritative Requirements):**  
> - **Green LED (Pin 13 / `GPIO 27`):** Illuminates **only** when a helmet is detected **without** gloves.  
> - **Yellow LED (Pin 11 / `GPIO 17`):** Illuminates **only** when gloves are detected **without** a helmet.  
> - **Red LED (Pin 15 / `GPIO 22`):** Blinks at a non-blocking 0.5s cadence **only** when **both** helmet and gloves are detected simultaneously.  
> - **Green and Yellow OFF during Dual Detection:** When Red is blinking, Green and Yellow **must remain OFF**.  
> - **No All-Three Illumination:** Under no circumstances should all three LEDs illuminate or blink together.  
> - **Non-Warning Indicator:** Red LED is strictly the Combined Detection Indicator (`Both Detected`), **never** a general warning or system fault light.  
> - **Fail-Safe OFF:** On detection loss, stale frames, or fault, all actuators return to the de-energized safe OFF state (`[0, 0, 0]`).

---

## 4. Hardware Pin Mapping & Actuation Configuration

Physical header connections on the Raspberry Pi 5 40-pin GPIO header:

| Functional Role | LED Color | Broadcom (BCM) GPIO | Physical Pin Number | Active Level | Current Limiting Resistor |
|---|---|---|---|---|---|
| **LED 1 (Helmet)** | Green | `GPIO 27` | Pin 13 | High ($3.3\,\text{V}$) | $220\,\Omega$ |
| **LED 2 (Gloves)** | Yellow | `GPIO 17` | Pin 11 | High ($3.3\,\text{V}$) | $220\,\Omega$ |
| **LED 3 (Both)** | Red | `GPIO 22` | Pin 15 | High ($3.3\,\text{V}$) | $220\,\Omega$ |
| **Common Ground** | - | `GND` | Pin 14 (or 9 / 6) | Ground ($0\,\text{V}$) | Common return rail |

---

## 5. Consecutive-Frame Debounce Requirements

To prevent actuator chatter caused by brief sensor occlusions or momentary inference flickers:
- **Confirmation Threshold ($N$):** Default $N = 3$ consecutive frames (configurable $1 \le N \le 10$).
- **State Transition Condition:**
  - An actuator state change requires $N$ consecutive matching frames before the hardware output pin is commanded.
  - A single aberrant frame immediately resets the confirmation counter, maintaining the prior stable state.
- **Debounce Hysteresis:** Avoids rapid switching across frame boundary noise.

---

## 6. Fault Handling & Fail-Safe Actuator State

In industrial safety systems, actuator behavior under error conditions must be deterministic:

```
                           +----------------------+
                           | Normal Operation     |
                           | Video Streams Active |
                           +----------+-----------+
                                      |
                           Camera / Stream Failure?
                                      |
                     +----------------v----------------+
                     | FAIL-SAFE TRIGGER ACTIVATED     |
                     | 1. De-energize all GPIO outputs |
                     | 2. LED 1 = OFF, 2 = OFF, 3 = OFF|
                     | 3. Set Dashboard: OFFLINE/ERROR |
                     | 4. Attempt Reconnect (Backoff)  |
                     +---------------------------------+
```

### 6.1 Failure Scenarios & Mitigations
1. **Camera Sensor Disconnection / Read Failure:**
   - Detects consecutive dropped frames $> 10$.
   - Transitions immediately to `SAFE_STATE`: All GPIO pins set to `LOW` (`0`).
   - Prevents stale PPE indications when camera is offline.
2. **Process Termination / Interrupt:**
   - Registered `atexit` and `signal` handlers call `gpio_controller.cleanup()`.
   - Releases pins and closes GPIO handles.
3. **Simulation Fallback:**
   - If running on a non-Pi machine or Docker container lacking `/dev/gpiomem`, the system defaults to virtual simulated mode with complete truth table emulation.


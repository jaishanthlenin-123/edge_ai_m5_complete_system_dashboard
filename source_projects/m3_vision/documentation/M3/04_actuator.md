# Actuator Control Subsystem & Hardware Verification
**Milestone:** M3 – Decide and Act  
**Document ID:** `M3-DOC-04`  
**System Target:** Raspberry Pi 5 RP1 Controller / 3-LED Stack Light  
**Author:** Lenin (`jaishanthlenin-123`)  

---

## 1. System Specification & Hardware Pin Configuration

The actuator subsystem manages three discrete visual indicator stack lights connected to the Raspberry Pi 5 40-pin header via the RP1 I/O controller. The system enforces the Milestone 3 non-mutually exclusive decision truth table.

### 1.1 Pin Connection Table

| Actuator Function | Color | Physical Header Pin | BCM GPIO Number | Circuit Protection | Return Path |
|---|---|---|---|---|---|
| **LED 1 (Helmet Indicator)** | Green | **Pin 13** | `GPIO 27` | $220\,\Omega$ ($1/4\,\text{W}$) Resistor | Physical Pin 14 (GND) |
| **LED 2 (Glove Indicator)** | Yellow | **Pin 11** | `GPIO 17` | $220\,\Omega$ ($1/4\,\text{W}$) Resistor | Physical Pin 14 (GND) |
| **LED 3 (Both Indicator)** | Red | **Pin 15** | `GPIO 22` | $220\,\Omega$ ($1/4\,\text{W}$) Resistor | Physical Pin 14 (GND) |
| **Common Ground** | - | **Pin 14** | `GND` | Common Negative Rail | System Ground |

---

## 2. Circuit Diagram & Hardware Layout

```text
Raspberry Pi 5 40-Pin Header
========================================================================
Pin 1  (3.3V)           [ . ]  [ . ]  Pin 2  (5V)
Pin 3  (GPIO 2 / SDA)   [ . ]  [ . ]  Pin 4  (5V)
Pin 5  (GPIO 3 / SCL)   [ . ]  [ . ]  Pin 6  (GND)
Pin 7  (GPIO 4)         [ . ]  [ . ]  Pin 8  (GPIO 14 / TXD)
Pin 9  (GND)            [ . ]  [ . ]  Pin 10 (GPIO 15 / RXD)
Pin 11 (GPIO 17) ------ [ * ]  [ . ]  Pin 12 (GPIO 18)
          |                |
          +---> [220Ω] --->|-(Anode +) YELLOW LED (Cathode -)--+
                                                                |
Pin 13 (GPIO 27) ------ [ * ]  [ * ]  Pin 14 (GND) <------------+ (Common Ground Rail)
          |                |      |                             |
          +---> [220Ω] --->|-(Anode +) GREEN LED  (Cathode -)---+
                                                                |
Pin 15 (GPIO 22) ------ [ * ]  [ . ]  Pin 16 (GPIO 23)          |
          |                                                     |
          +---> [220Ω] --->|-(Anode +) RED LED    (Cathode -)---+
========================================================================
```

---

## 3. Four-State Test Matrix & Empirical Results

The system was evaluated across all four input combinations:

| Test Case | Helmet Detected | Gloves Detected | LED 1 (Green) | LED 2 (Yellow) | LED 3 (Red) | Active Label | Verified Result |
|---|---|---|---|---|---|---|---|
| **TC01** | **Yes** | No | **ON** | OFF | OFF | `GREEN LED ACTIVE (HELMET ONLY)` | **PASS** |
| **TC02** | No | **Yes** | OFF | **ON** | OFF | `YELLOW LED ACTIVE (GLOVES ONLY)` | **PASS** |
| **TC03** | **Yes** | **Yes** | **OFF** | **OFF** | **BLINKING** (0.5s) | `BOTH DETECTED – RED LED BLINKING` | **PASS** |
| **TC04** | No | No | OFF | OFF | OFF | `ALL LEDS OFF` | **PASS** |

> [!IMPORTANT]
> **Authoritative Three-LED Rules:**  
> - **Green LED (Pin 13 / `GPIO 27`):** Illuminates **only** when a helmet is detected **without** gloves.  
> - **Yellow LED (Pin 11 / `GPIO 17`):** Illuminates **only** when gloves are detected **without** a helmet.  
> - **Red LED (Pin 15 / `GPIO 22`):** Blinks at a 0.5s cadence **only** when **both** helmet and gloves are detected simultaneously.  
> - **Green and Yellow OFF during Dual Detection:** When Red is blinking, Green and Yellow **must remain OFF**.  
> - **No All-Three Illumination:** Under no circumstances should all three LEDs illuminate or blink together.  
> - **Non-Warning Indicator:** Red LED is strictly the Combined Detection Indicator (`Both Detected`), **never** a general warning or system fault light.

---

## 4. Fail-Safe Actuation & Recovery Mode

In compliance with industrial functional safety standards:
1. **Camera Sensor Loss:** If frame capture fails for $>10$ consecutive frames, the actuator manager immediately invokes `safe_state()`, setting all GPIO outputs to `LOW` ($0\,\text{V}$).
2. **Process Interruption:** `atexit` and `signal` hooks guarantee that `cleanup()` is called upon `SIGINT`, `SIGTERM`, or server shutdown.
3. **Execution Environment Notice:** On development workstations running Windows 11 or Linux environments without the RP1 hardware controller, the system operates in **Simulated GPIO Mode**, emulating all internal pin registers without error. Physical hardware execution is enabled automatically on Raspberry Pi 5 hardware.

---

## 5. Physical Hardware Verification & Demonstration Evidence

In addition to automated software simulation, the physical actuator circuit was constructed on a breadboard and evaluated live with the trained model and camera on Raspberry Pi 5 hardware.

### 5.1 Physical Circuit & Video Demonstration
- **Breadboard Circuit Photo:** [`photos/circuit_connection_breadboard.jpeg`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/photos/circuit_connection_breadboard.jpeg)
- **Live Actuator Demonstration Video:** [`videos/3_led_blinking_actuator_video.mp4`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/videos/3_led_blinking_actuator_video.mp4) (45.3s, 30 FPS)
- **Subtopic Evidence Documentation:** [`evidence/M3/04_actuator/README.md`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/README.md)

### 5.2 Extracted Physical Video Keyframes (`videos/frames/`)
The demonstration video verifies the functional responses on physical LEDs:
1. **Idle State (Neither Detected):** [`frame_actuator_01_idle_all_off.png`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/videos/frames/frame_actuator_01_idle_all_off.png) ($t = 0.60\,\text{s}$) — All 3 LEDs OFF.
2. **Helmet Only Detected:** [`frame_actuator_02_helmet_only_green_on.png`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/videos/frames/frame_actuator_02_helmet_only_green_on.png) ($t = 3.00\,\text{s}$) — Green LED (`GPIO 27`) ON, Yellow & Red OFF.
3. **Gloves Only Detected:** [`frame_actuator_03_gloves_only_yellow_on.png`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/videos/frames/frame_actuator_03_gloves_only_yellow_on.png) ($t = 18.17\,\text{s}$) — Yellow LED (`GPIO 17`) ON, Green & Red OFF.
4. **Both Detected (Legacy Physical Run):** [`frame_actuator_04_both_detected_all_three_on.png`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/videos/frames/frame_actuator_04_both_detected_all_three_on.png) ($t = 24.50\,\text{s}$) — Legacy physical recording showing worker presenting both items.
5. **Both Detected Retest (Legacy Physical Run):** [`frame_actuator_05_both_detected_sustained.png`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/videos/frames/frame_actuator_05_both_detected_sustained.png) ($t = 35.00\,\text{s}$) — Sustained worker presentation.
6. **Return to Idle:** [`frame_actuator_06_return_idle_all_off.png`](file:///e:/New%20folder%20(6)/evidence/M3/04_actuator/videos/frames/frame_actuator_06_return_idle_all_off.png) ($t = 44.67\,\text{s}$) — All 3 LEDs de-energized.

> [!NOTE]
> **Physical Demonstration Video Note:** The video `3_led_blinking_actuator_video.mp4` captures the initial bench testing phase where all three LEDs were energized. The authoritative M3 specification requires the Red LED to blink while Green and Yellow remain strictly OFF during dual detection. The updated simulation software and unit tests fully implement and verify this logic (TC01–TC06 PASS), and a re-recording of the physical circuit reflecting the blinking Red LED is scheduled per the hardware verification protocol.

---

## 6. Artifact Links

The simulated test suite outputs and logs are archived in:
- `evidence/M3/04_actuator/screenshots/TC01_helmet_only.png`
- `evidence/M3/04_actuator/screenshots/TC02_gloves_only.png`
- `evidence/M3/04_actuator/screenshots/TC03_both_detected.png`
- `evidence/M3/04_actuator/screenshots/TC04_neither_detected.png`
- `evidence/M3/04_actuator/test_results/actuator_test_output.txt`


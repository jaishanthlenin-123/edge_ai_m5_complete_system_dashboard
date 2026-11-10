# Phase 1: Hardware and Software Audit Report

**Date:** November 6, 2026  
**Target:** Arduino Uno R3 + Raspberry Pi 5  
**File Audited:** `arduino/servo_test/servo_test.ino` (Backup: `arduino/servo_test/servo_test.ino.bak`)

---

## 1. Executive Summary

An audit of the active Arduino sketch `arduino/servo_test/servo_test.ino` and live USB serial output was conducted. The existing sketch successfully integrates servo positioning with 5 sensor acquisition routines across pins D9 and A0–A5, communicating at 115200 baud. However, critical sensor scaling, calibration offsets, and ADC timing issues were identified that must be addressed in Phase 2 before reliable dataset collection and machine learning feature extraction can begin.

---

## 2. Pin Assignments Verification

| Function | Arduino Pin | Sketch Pin Variable | Audit Status | Electrical Verification |
|---|:---:|:---:|:---:|---|
| **SG90 Servo PWM** | **D9** | `SERVO_PIN = 9` | 🟢 Correct | Uses `Servo.h` library on hardware Timer1 pin. |
| **ACS712 Current Sensor** | **A0** | `ACS_PIN = A0` | 🟢 Correct | Analog input connected to ACS712 OUT pin. |
| **0–25V Voltage Sensor** | **A1** | `VOLT_PIN = A1` | 🟢 Correct | Analog input connected to voltage divider signal (S). |
| **MAX9814 Microphone** | **A2** | `MIC_PIN = A2` | 🟢 Correct | Analog input connected to MAX9814 OUT pin. |
| **Accelerometer X-Axis** | **A3** | `ACC_X_PIN = A3` | 🟢 Correct | Analog 3-axis accelerometer X_OUT. |
| **Accelerometer Y-Axis** | **A4** | `ACC_Y_PIN = A4` | 🟢 Correct | Analog 3-axis accelerometer Y_OUT. |
| **Accelerometer Z-Axis** | **A5** | `ACC_Z_PIN = A5` | 🟢 Correct | Analog 3-axis accelerometer Z_OUT. |

All hardware pin definitions in code match the required physical configuration.

---

## 3. Sensor Acquisition & Scaling Audit

### 3.1. ACS712 Current Sensor (Pin A0)
- **Current Implementation:**
  ```cpp
  int acsRaw = readAverage(ACS_PIN);
  float acsVoltage = acsRaw * ADC_REF_V / 1023.0;
  ```
- **Audit Findings:**
  1. The code only calculates the sensor output voltage ($V_{out}$); it **does not calculate current in Amperes (`current_a`)**.
  2. The zero-current quiescent voltage offset ($V_{zero} \approx 2.50\text{V}$ for 5V supply) is not subtracted.
  3. The sensitivity constant is not applied. ACS712 modules come in three variants with different sensitivities:
     - 5A variant: $185\text{ mV/A}$ ($0.185\text{ V/A}$)
     - 20A variant: $100\text{ mV/A}$ ($0.100\text{ V/A}$)
     - 30A variant: $66\text{ mV/A}$ ($0.066\text{ V/A}$)
  4. Formula required:
     $$I_{\text{actual}} = \frac{V_{out} - V_{zero}}{\text{Sensitivity}}$$

### 3.2. 0–25V Voltage Sensor Module (Pin A1)
- **Current Implementation:**
  ```cpp
  int voltageRaw = readAverage(VOLT_PIN);
  float voltageSensorOutput = voltageRaw * ADC_REF_V / 1023.0;
  ```
- **Audit Findings:**
  1. The code calculates the voltage at the Arduino ADC pin ($0.0\text{V} - 5.0\text{V}$), but **fails to multiply by the voltage divider ratio (5.0)**.
  2. The module uses a $30\text{ k}\Omega$ and $7.5\text{ k}\Omega$ resistive divider:
     $$V_{\text{actual}} = V_{\text{sensor\_output}} \times \left(\frac{30\text{k}\Omega + 7.5\text{k}\Omega}{7.5\text{k}\Omega}\right) = V_{\text{sensor\_output}} \times 5.0$$
  3. Live telemetry showed raw values near $0$, indicating the sensor is either not connected across the external servo power rail or the motor supply is off.

### 3.3. Analog 3-Axis Accelerometer (Pins A3, A4, A5)
- **Current Implementation:**
  ```cpp
  int accelX = readAverage(ACC_X_PIN);
  int accelY = readAverage(ACC_Y_PIN);
  int accelZ = readAverage(ACC_Z_PIN);
  ```
- **Audit Findings:**
  1. Directly outputs raw 10-bit integer values ($0 - 1023$).
  2. No baseline zero-$g$ offset or sensitivity scaling ($mV/g$) is currently configured.
  3. Raw integer readings are preserved, which is acceptable for relative anomaly detection, but calibration will allow meaningful physical units ($g$ or $m/s^2$).

### 3.4. MAX9814 Microphone Amplifier (Pin A2)
- **Current Implementation:**
  Samples 64 values with `delayMicroseconds(500)`, computes mean, variance, RMS, and peak-to-peak.
- **Audit Findings:**
  1. Correctly removes the DC bias component by subtracting the window mean before computing RMS:
     $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (x_i - \bar{x})^2}$$
  2. Correctly determines Peak-to-Peak amplitude ($\max - \min$).
  3. Provides meaningful acoustic burst detection during motor movement.

---

## 4. Timing & Blocking Delay Analysis

1. **Microphone Acquisition Delay:**
   - In `readMicrophone()`: 64 samples $\times$ ($110\mu s$ ADC conversion + $500\mu s$ delay) $\approx$ **$39.0\text{ ms}$ of blocking execution**.
   - With `PRINT_INTERVAL = 100\text{ ms}`, the loop spends $\approx 40\%$ of its time blocked in microphone sampling.
   - The effective loop sampling rate is $\approx 6.8\text{ Hz}$ ($146\text{ ms}$ per record) rather than the intended $10\text{ Hz}$ ($100\text{ ms}$).
2. **Servo Motion Profile:**
   - `motorServo.write(currentAngle)` executes an instantaneous position step ($30^\circ \to 90^\circ \to 150^\circ$).
   - This causes maximum inrush current and gear train jerk. An optional gentle stepped interpolation mode should be considered.

---

## 5. Serial Telemetry Format Comparison

| Field Order | Existing Sketch Output | Phase 2 Master Specification | Assessment |
|:---:|---|---|---|
| 1 | `timestamp_ms` | `timestamp_ms` | 🟢 Matches |
| 2 | `sequence` | `servo_angle` | 🟡 Format discrepancy |
| 3 | `servo_angle` | `voltage_v` | 🟡 Format discrepancy |
| 4 | `accel_x` | `current_a` | 🟡 Format discrepancy |
| 5 | `accel_y` | `accel_x` | 🟡 Format discrepancy |
| 6 | `accel_z` | `accel_y` | 🟡 Format discrepancy |
| 7 | `acs_raw` | `accel_z` | 🟡 Format discrepancy |
| 8 | `acs_voltage` | `sound_raw` | 🟡 Format discrepancy |
| 9 | `voltage_raw` | *(not in spec)* | Extra raw field |
| 10 | `voltage_sensor_output_v` | *(not in spec)* | Extra uncalibrated field |
| 11 | `mic_rms` | *(not in spec)* | Extracted acoustic feature |
| 12 | `mic_peak_to_peak` | *(not in spec)* | Extracted acoustic feature |

**Conclusion:** The serial output format must be standardized so that the Raspberry Pi acquisition parser, CSV logger, feature extraction, and dashboard ingest a single, consistent protocol.

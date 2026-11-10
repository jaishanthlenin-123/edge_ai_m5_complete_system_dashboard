# System Architecture & Serial Communication Protocol

This document explains the software architecture, data flow, and serial communication protocol connecting the **Arduino Uno** and **Raspberry Pi 5**.

---

## 1. High-Level Architecture

The system splits responsibilities into two distinct tiers:
1. **Real-Time Embedded Controller (Arduino Uno):**
   - Precise PWM signal generation for SG90 servo position control.
   - Deterministic analog-to-digital conversions and I2C sensor reading.
   - Non-blocking telemetry serialization over USB UART.
2. **Edge Computing & Analytics Host (Raspberry Pi 5):**
   - High-throughput USB serial receiver and packet validation.
   - Local CSV dataset persistence and storage management.
   - Sliding-window statistical feature extraction.
   - Machine Learning inference using an unsupervised Isolation Forest model.
   - Interactive local web dashboard for live monitoring and anomaly alerts.

---

## 2. Serial Communication Protocol

### Physical Layer
- **Interface:** USB Serial (Virtual COM / CDC-ACM).
- **Default Device Path:** `/dev/ttyACM0` or `/dev/ttyUSB0` on Raspberry Pi 5.
- **Baud Rate:** `115200 bps` (8 data bits, no parity, 1 stop bit: 8-N-1).
- **Line Ending:** `\r\n` (CRLF) or `\n` (LF).

### Phase 2: Servo Test Protocol
During Phase 2, the Arduino transmits single-line comma-separated values (CSV) indicating servo movement:

```text
timestamp_ms,commanded_angle,status
```

#### Field Specifications:
- `timestamp_ms` (*unsigned long*): Milliseconds elapsed since Arduino boot.
- `commanded_angle` (*integer*): Commanded servo shaft angle in degrees (`30`, `90`, `150`).
- `status` (*string*): Motion state (`HOLD`, `MOVING_CW`, `MOVING_CCW`, `HOME`).

#### Example Output:
```text
# SYSTEM: SG90 Servo Motor Test Initialized
# FORMAT: timestamp_ms,commanded_angle,status
1500,90,HOME
2500,30,MOVING_CCW
3400,30,HOLD
4400,90,MOVING_CW
5300,90,HOLD
6300,150,MOVING_CW
7200,150,HOLD
```

Lines beginning with `#` are treated as diagnostic comments and ignored by data parsers.

---

## 3. Phase 4: Full Integrated Multi-Sensor Protocol

In Phase 4, the serial stream expands to include all sensor measurements at a fixed sampling interval (e.g., 20Hz / 50ms):

```text
timestamp_ms,sequence_number,commanded_angle,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,current,voltage,audio_rms,audio_peak_to_peak
```

### Telemetry Fields:
1. `timestamp_ms` [ms]: Microcontroller clock.
2. `sequence_number` [int]: Monotonically increasing record counter (detects dropped packets).
3. `commanded_angle` [deg]: Active servo position setpoint.
4. `accel_x` [m/s² or g]: MPU6050 X-axis acceleration.
5. `accel_y` [m/s² or g]: MPU6050 Y-axis acceleration.
6. `accel_z` [m/s² or g]: MPU6050 Z-axis acceleration.
7. `gyro_x` [deg/s]: MPU6050 X-axis angular velocity.
8. `gyro_y` [deg/s]: MPU6050 Y-axis angular velocity.
9. `gyro_z` [deg/s]: MPU6050 Z-axis angular velocity.
10. `current` [mA]: ACS712 instantaneous motor current.
11. `voltage` [V]: Motor supply rail voltage.
12. `audio_rms` [V / raw]: MAX9814 root-mean-square acoustic energy.
13. `audio_peak_to_peak` [V / raw]: MAX9814 peak-to-peak amplitude.

---

## 4. Raspberry Pi Data Pipeline

```text
[USB Port]
    │
    ▼
[serial_receiver.py] ─── (Parse, Validate, Host Timestamp)
    │
    ├──▶ [datasets/raw/*.csv] (Disk Storage)
    │
    ▼
[Feature Extractor] (Sliding Window: RMS, StdDev, Mean, P2P)
    │
    ▼
[Isolation Forest Model] (Inference: Normal vs Anomaly)
    │
    ├──▶ [Anomaly Alert Log]
    ▼
[Web Dashboard] (Real-time telemetry, charts, anomaly scores)
```

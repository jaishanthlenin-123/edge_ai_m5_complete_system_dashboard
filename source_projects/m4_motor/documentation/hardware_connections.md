# Hardware Connections and Wiring Guide

This guide details the physical electrical wiring, pin assignments, and power distribution for the SG90 Servo Condition Monitoring System.

---

## 1. Power Distribution & Safety Rules

> [!WARNING]
> **NEVER POWER THE SG90 SERVO FROM THE ARDUINO 5V PIN!**
> The SG90 micro-servo draws approximately 100mA–250mA during free motion, but during rapid acceleration, load shifts, or stall conditions, current can surge beyond **800mA**. The Arduino Uno onboard 5V linear regulator cannot sustain these surges and will either brown out (causing CPU resets) or overheat.

### Power Wiring Diagram

```text
External 5V DC Supply (+5V) --------+----------------------> SG90 Red Wire (+5V)
                                     |  (Later through ACS712)
                                     +----------------------> Voltage Sensor (+)

External 5V DC Supply (GND) --------+----------------------> SG90 Brown Wire (GND)
                                     |
                                     +----------------------> Arduino GND (COMMON GROUND)
                                     |
                                     +----------------------> Voltage Sensor (-)

Arduino Uno (D9) -------------------------------------------> SG90 Orange/Yellow Wire (Signal)

Arduino Uno USB --------------------------------------------> Raspberry Pi 5 USB Port
```

### The Common Ground Requirement
All electrical signals are measured relative to a 0V reference. Therefore:
- The **negative terminal (GND)** of the external power supply **MUST** connect to the **GND** pin of the Arduino Uno.
- Without this common ground, the D9 PWM signal will have no reference point, resulting in erratic twitching, buzzing, or failure to move.

---

## 2. Phase 2: Standalone SG90 Servo Wiring Table

For Phase 2 (Servo Testing), connect only the SG90 servo motor:

| SG90 Wire Color | Function | Connect To |
|:---:|:---:|:---|
| **Orange / Yellow** | PWM Control Signal | **Arduino Pin D9** |
| **Red** | Power (+5V) | **External 5V DC Supply (+)** |
| **Brown / Dark Brown** | Ground (0V) | **External 5V DC Supply (-) AND Arduino GND** |

---

## 3. Future Phases: Sensor Pin Allocation Summary

Once the standalone servo is verified, sensors will be added in Phase 3 & 4 one at a time:

| Component | Pin | Arduino Pin | Description |
|---|:---:|:---:|---|
| **SG90 Servo** | Signal | **D9** | PWM duty cycle (50Hz, 1ms - 2ms pulse width) |
| **ACS712** | OUT | **A0** | Analog voltage representing instantaneous current |
| | VCC | 5V | Arduino 5V supply |
| | GND | GND | Arduino GND |
| | IP+ / IP- | Series | In-line with the servo +5V supply wire |
| **0-25V Voltage Sensor** | S (Signal) | **A1** | Scaled voltage (5:1 divider: 0-25V scaled to 0-5V) |
| | - (Negative) | GND | Common Ground |
| | VCC (+) Terminal | Servo +5V | External supply positive rail |
| | GND (-) Terminal | Servo GND | External supply ground rail |
| **MAX9814 Mic** | OUT | **A2** | Analog audio envelope/signal |
| | VDD | 3.3V or 5V | Clean supply rail |
| | GND | GND | Common Ground |
| | GAIN | Float / VDD | Gain setting (Default float = 60dB) |
| **MPU6050 IMU** | VCC | 5V (or 3.3V) | Sensor power (depends on breakout onboard regulator) |
| | GND | GND | Common Ground |
| | SDA | **A4** | I2C Data bus |
| | SCL | **A5** | I2C Clock bus |

---

## 4. Pre-Power Verification Checklist

Before plugging in any power cables or turning on the external supply, verify each item:

- [ ] **Visual Check:** No stray wire strands touching adjacent pins or breadboard rows.
- [ ] **Polarity Check:** Double-check +5V (Red) vs GND (Brown/Black) on the servo connector.
- [ ] **Common Ground:** Confirm a jumper connects the external power supply GND rail to an Arduino GND pin.
- [ ] **Arduino 5V Isolation:** Confirm the servo red wire is NOT plugged into the Arduino 5V pin.
- [ ] **Free Movement:** Confirm the servo horn/arm is free to rotate without physically hitting objects or binding.

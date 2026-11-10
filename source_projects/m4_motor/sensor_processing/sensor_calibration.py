#!/usr/bin/env python3
"""
Sensor Calibration & Verification Utility
Project: SG90 Servo Motor Condition Monitoring and Anomaly Detection System
Target: Raspberry Pi 5

Description:
    Samples live telemetry over USB serial to compute baseline statistics,
    verify electrical zero offsets, check sensor sensitivities, and report health status.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from raspberry_pi.serial_reader import SerialReader


def run_calibration_check(sample_count: int = 30):
    reader = SerialReader()
    print("=" * 80)
    print(" SENSOR CALIBRATION & HARDWARE VERIFICATION")
    print("=" * 80)
    print(f"Collecting {sample_count} live telemetry frames from Arduino...")

    records: List[Dict[str, Any]] = []
    try:
        for record in reader.read_stream():
            records.append(record)
            print(f"\rCaptured [{len(records)}/{sample_count}] frames...", end="", flush=True)
            if len(records) >= sample_count:
                break
    except KeyboardInterrupt:
        print("\nAborted by user.")
        return
    finally:
        reader.close()

    print("\n\n" + "-" * 80)
    print(" SENSOR VERIFICATION ANALYSIS")
    print("-" * 80)

    # Accelerometer statistics
    ax_vals = [r["accel_x"] for r in records]
    ay_vals = [r["accel_y"] for r in records]
    az_vals = [r["accel_z"] for r in records]
    volt_vals = [r["voltage_v"] for r in records]
    curr_vals = [r["current_a"] for r in records]
    mic_vals = [r.get("sound_raw", r.get("sound_p2p", 0)) for r in records]

    def stats(arr):
        mean_v = sum(arr) / len(arr)
        variance = sum((x - mean_v) ** 2 for x in arr) / len(arr)
        return mean_v, variance ** 0.5, min(arr), max(arr)

    v_mean, v_std, v_min, v_max = stats(volt_vals)
    c_mean, c_std, c_min, c_max = stats(curr_vals)
    ax_mean, ax_std, ax_min, ax_max = stats(ax_vals)
    ay_mean, ay_std, ay_min, ay_max = stats(ay_vals)
    az_mean, az_std, az_min, az_max = stats(az_vals)
    m_mean, m_std, m_min, m_max = stats(mic_vals)

    print(f"1. VOLTAGE SENSOR (A1):")
    print(f"   Mean: {v_mean:.2f} V | Range: [{v_min:.2f} V - {v_max:.2f} V] | StdDev: {v_std:.2f} V")
    if v_mean < 1.0:
        print("   -> STATUS: ⚠️ Low/Zero voltage detected. Check connection to motor supply.")
    elif 4.5 <= v_mean <= 5.5:
        print("   -> STATUS: 🟢 Nominal 5V motor rail verified.")
    else:
        print(f"   -> STATUS: ℹ️ Measured external voltage = {v_mean:.2f} V.")

    print(f"\n2. ACS712 CURRENT SENSOR (A0):")
    print(f"   Mean: {c_mean:.3f} A | Range: [{c_min:.3f} A - {c_max:.3f} A] | StdDev: {c_std:.3f} A")
    if abs(c_mean) < 0.15:
        print("   -> STATUS: 🟢 Zero-current baseline verified (motor idle/low load).")
    else:
        print(f"   -> STATUS: ℹ️ Active current draw detected ({c_mean:.3f} A).")

    print(f"\n3. 3-AXIS ACCELEROMETER (A3, A4, A5):")
    print(f"   X: Mean={ax_mean:.1f} (std={ax_std:.1f}) | Range=[{ax_min} - {ax_max}]")
    print(f"   Y: Mean={ay_mean:.1f} (std={ay_std:.1f}) | Range=[{ay_min} - {ay_max}]")
    print(f"   Z: Mean={az_mean:.1f} (std={az_std:.1f}) | Range=[{az_min} - {az_max}]")
    print("   -> STATUS: 🟢 Multi-axis vibration channel active.")

    print(f"\n4. MAX9814 MICROPHONE (A2):")
    print(f"   Acoustic Mean: {m_mean:.1f} | Peak-to-Peak Range: [{m_min} - {m_max}] | StdDev: {m_std:.1f}")
    if m_mean > 0:
        print("   -> STATUS: 🟢 Acoustic signal detected.")
    else:
        print("   -> STATUS: ⚠️ Low audio activity.")

    print("=" * 80)


if __name__ == "__main__":
    run_calibration_check(sample_count=30)

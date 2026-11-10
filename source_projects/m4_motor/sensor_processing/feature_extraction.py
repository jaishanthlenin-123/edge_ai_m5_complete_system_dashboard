#!/usr/bin/env python3
"""
Signal Processing & Windowed Feature Extraction Engine
Project: SG90 Servo Motor Condition Monitoring and Anomaly Detection System
Target: Raspberry Pi 5

Description:
    Computes statistical, vibration, acoustic, and electrical features over
    sliding telemetry windows for machine learning anomaly detection.
    Optimized for Raspberry Pi 5 with zero required external dependencies beyond NumPy.
"""

import csv
import math
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Standard feature columns produced by the extractor
FEATURE_COLUMNS = [
    "current_mean",
    "current_peak",
    "current_std",
    "current_rms",
    "voltage_mean",
    "voltage_std",
    "voltage_min",
    "voltage_drop",
    "accel_mag_mean",
    "accel_mag_std",
    "accel_mag_rms",
    "accel_mag_p2p",
    "accel_mag_crest_factor",
    "accel_x_std",
    "accel_y_std",
    "accel_z_std",
    "sound_p2p_mean",
    "sound_p2p_max",
    "sound_rms_mean",
    "sound_energy",
    "angle_motion_rate"
]


class FeatureExtractor:
    """Extracts multivariate condition-monitoring features across sliding windows."""

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.buffer: List[Dict[str, Any]] = []

    def update(self, record: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Adds a single telemetry sample to the sliding window.
        Returns extracted feature dictionary when window is full, else None.
        """
        self.buffer.append(record)
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)

        if len(self.buffer) < self.window_size:
            return None

        return self.extract_from_window(self.buffer)

    @staticmethod
    def extract_from_window(window: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extracts statistical, physical, and dynamic features from a list of records."""
        currents = np.array([float(r.get("current_a", 0.0)) for r in window], dtype=np.float64)
        voltages = np.array([float(r.get("voltage_v", 0.0)) for r in window], dtype=np.float64)
        ax = np.array([float(r.get("accel_x", 0.0)) for r in window], dtype=np.float64)
        ay = np.array([float(r.get("accel_y", 0.0)) for r in window], dtype=np.float64)
        az = np.array([float(r.get("accel_z", 0.0)) for r in window], dtype=np.float64)
        sound_rms = np.array([float(r.get("sound_rms", 0.0)) for r in window], dtype=np.float64)
        sound_p2p = np.array([float(r.get("sound_p2p", 0.0)) for r in window], dtype=np.float64)
        angles = np.array([float(r.get("servo_angle", 0.0)) for r in window], dtype=np.float64)

        # 1. Electrical Features (Current)
        curr_mean = float(np.mean(currents))
        curr_peak = float(np.max(currents))
        curr_std = float(np.std(currents))
        curr_rms = float(np.sqrt(np.mean(currents ** 2)))

        # 2. Electrical Features (Voltage)
        volt_mean = float(np.mean(voltages))
        volt_std = float(np.std(voltages))
        volt_min = float(np.min(voltages))
        volt_drop = float(np.max(voltages) - volt_min)

        # 3. Vibration Features (3-Axis Accelerometer)
        accel_mag = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
        mag_mean = float(np.mean(accel_mag))
        mag_std = float(np.std(accel_mag))
        mag_rms = float(np.sqrt(np.mean(accel_mag ** 2)))
        mag_p2p = float(np.max(accel_mag) - np.min(accel_mag))
        crest_factor = float(np.max(accel_mag) / (mag_rms + 1e-6))

        ax_std = float(np.std(ax))
        ay_std = float(np.std(ay))
        az_std = float(np.std(az))

        # 4. Acoustic Features
        s_p2p_mean = float(np.mean(sound_p2p))
        s_p2p_max = float(np.max(sound_p2p))
        s_rms_mean = float(np.mean(sound_rms))
        s_energy = float(np.sum(sound_rms ** 2))

        # 5. Motion Dynamics
        angle_motion_rate = float(np.sum(np.abs(np.diff(angles))))

        features = {
            "current_mean": curr_mean,
            "current_peak": curr_peak,
            "current_std": curr_std,
            "current_rms": curr_rms,
            "voltage_mean": volt_mean,
            "voltage_std": volt_std,
            "voltage_min": volt_min,
            "voltage_drop": volt_drop,
            "accel_mag_mean": mag_mean,
            "accel_mag_std": mag_std,
            "accel_mag_rms": mag_rms,
            "accel_mag_p2p": mag_p2p,
            "accel_mag_crest_factor": crest_factor,
            "accel_x_std": ax_std,
            "accel_y_std": ay_std,
            "accel_z_std": az_std,
            "sound_p2p_mean": s_p2p_mean,
            "sound_p2p_max": s_p2p_max,
            "sound_rms_mean": s_rms_mean,
            "sound_energy": s_energy,
            "angle_motion_rate": angle_motion_rate
        }
        return features


def extract_features_from_csv(csv_path: str, window_size: int = 10, step_size: int = 2) -> List[Dict[str, Any]]:
    """Processes an entire recorded CSV telemetry file into a windowed feature list."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    feature_rows = []
    for i in range(0, len(records) - window_size + 1, step_size):
        sub_window = records[i:i + window_size]
        feats = FeatureExtractor.extract_from_window(sub_window)
        feats["window_start_ts"] = sub_window[0].get("host_timestamp", "")
        feats["window_end_ts"] = sub_window[-1].get("host_timestamp", "")
        feature_rows.append(feats)

    return feature_rows

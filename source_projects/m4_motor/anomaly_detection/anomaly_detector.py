#!/usr/bin/env python3
"""
Multivariate Machine Learning Anomaly Detection Engine
Project: SG90 Servo Motor Condition Monitoring and Anomaly Detection System
Target: Raspberry Pi 5

Features:
    - Calibrated normal operating envelope (accounts for normal servo motion,
      acoustic gear noise, and rotational acceleration).
    - Regularized variance to prevent division by near-zero std.
    - Robust multivariate Z-score combining electrical, vibration, and acoustic channels.
    - Smooth normalized anomaly scoring:
        * 0.00 - 0.40 : NORMAL OPERATION (Green)
        * 0.40 - 0.65 : ELEVATED / TRANSIENT (Amber)
        * 0.65 - 1.00 : CRITICAL ANOMALY (Red)
"""

import os
import json
import pickle
import datetime
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from raspberry_pi.config import SAVED_MODELS_DIR, NORMAL_LIMITS
from raspberry_pi.feature_extraction import FEATURE_COLUMNS

# Minimum standard deviation floor per feature group to prevent artificial Z-score explosion
FEATURE_STD_FLOORS = {
    "current_mean": 0.15,
    "current_peak": 0.20,
    "current_std": 0.10,
    "current_rms": 0.15,
    "voltage_mean": 0.50,
    "voltage_std": 0.20,
    "voltage_min": 0.50,
    "voltage_drop": 0.30,
    "accel_mag_mean": 40.0,
    "accel_mag_std": 30.0,
    "accel_mag_rms": 40.0,
    "accel_mag_p2p": 35.0,
    "accel_mag_crest_factor": 0.35,
    "accel_x_std": 25.0,
    "accel_y_std": 25.0,
    "accel_z_std": 25.0,
    "sound_p2p_mean": 45.0,
    "sound_p2p_max": 50.0,
    "sound_rms_mean": 15.0,
    "sound_energy": 2500.0,
    "angle_motion_rate": 15.0
}


class AnomalyDetectionModel:
    """End-to-end calibrated anomaly detector for SG90 servo monitoring."""

    def __init__(self, model_type: str = "statistical", contamination: float = 0.05):
        self.model_type = model_type
        self.contamination = contamination
        self.is_trained = False
        self.feature_names = list(FEATURE_COLUMNS)
        self.baseline_stats: Dict[str, Dict[str, float]] = {}
        self.anomaly_threshold: float = 0.65  # Normalized threshold for anomaly flag
        self.threshold: float = 0.65

        self.metadata: Dict[str, Any] = {
            "model_type": self.model_type,
            "trained_at": None,
            "sample_count": 0,
            "contamination": self.contamination,
            "feature_names": self.feature_names
        }

    def train(self, feature_matrix: np.ndarray, feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Trains the model on normal baseline operating data.
        Incorporates physical noise floors to prevent overfitting to quiet states.
        """
        if feature_names:
            self.feature_names = list(feature_names)

        X = np.asarray(feature_matrix, dtype=np.float64)
        if len(X.shape) != 2:
            raise ValueError(f"Expected 2D array, got shape {X.shape}")

        n_samples, n_features = X.shape
        self.baseline_stats = {}

        for idx, col in enumerate(self.feature_names):
            vals = X[:, idx]
            raw_mean = float(np.mean(vals))
            raw_std = float(np.std(vals))
            floor = FEATURE_STD_FLOORS.get(col, 1.0)
            # Regularized standard deviation ensures normal motion does not produce massive Z-scores
            effective_std = max(raw_std, floor)

            self.baseline_stats[col] = {
                "mean": raw_mean,
                "std": effective_std,
                "min": float(np.min(vals)),
                "max": float(np.max(vals))
            }

        self.is_trained = True
        self.metadata["trained_at"] = datetime.datetime.now().isoformat()
        self.metadata["sample_count"] = int(n_samples)
        self.metadata["model_type"] = self.model_type

        return self.metadata

    def predict_window(self, feature_dict: Dict[str, float]) -> Dict[str, Any]:
        """
        Infers anomaly status and normalized score for a single feature window.
        Distinguishes expected servo rotation from genuine mechanical/electrical faults.
        """
        if not self.is_trained:
            return self._heuristic_check(feature_dict)

        # 1. Hard physical safety overrides (Immediate faults)
        curr_mean = feature_dict.get("current_mean", 0.0)
        curr_peak = feature_dict.get("current_peak", 0.0)
        volt_min = feature_dict.get("voltage_min", 5.0)
        sound_max = feature_dict.get("sound_p2p_max", 0.0)

        critical_faults = []
        if curr_mean > NORMAL_LIMITS["current_max_a"] or curr_peak > NORMAL_LIMITS["current_max_a"]:
            val = max(curr_mean, curr_peak)
            critical_faults.append(("current_exceeded_0.200A", round(val, 3)))
        if curr_peak > 1.20:
            critical_faults.append(("severe_current_surge", round(curr_peak, 2)))
        if volt_min > 0.5 and volt_min < 3.8:
            critical_faults.append(("supply_brownout", round(volt_min, 2)))
        if sound_max > 500:
            critical_faults.append(("severe_acoustic_grinding", round(sound_max, 1)))

        if critical_faults:
            return {
                "status": "ANOMALY",
                "anomaly_score": 0.95,
                "is_anomaly": True,
                "contributing_features": critical_faults
            }

        # 2. Multivariate statistical scoring
        z_scores = []
        contributions = []

        # Distinct physical domains: Electrical, Vibration, Acoustic
        domain_deviations = {"electrical": [], "vibration": [], "acoustic": []}

        for col in self.feature_names:
            val = feature_dict.get(col, 0.0)
            stats = self.baseline_stats.get(col)
            if not stats:
                continue

            z = abs(val - stats["mean"]) / stats["std"]
            # Clip individual feature Z to avoid a single noisy sample dominating
            z_clipped = min(z, 8.0)

            if "current" in col or "voltage" in col:
                domain_deviations["electrical"].append(z_clipped)
            elif "accel" in col:
                domain_deviations["vibration"].append(z_clipped)
            elif "sound" in col:
                domain_deviations["acoustic"].append(z_clipped)

            if z > 2.5:
                contributions.append((col, round(z, 2)))

        contributions.sort(key=lambda x: x[1], reverse=True)

        # Domain composite RMS Z-scores
        elec_z = float(np.mean(domain_deviations["electrical"])) if domain_deviations["electrical"] else 0.0
        vib_z = float(np.mean(domain_deviations["vibration"])) if domain_deviations["vibration"] else 0.0
        sound_z = float(np.mean(domain_deviations["acoustic"])) if domain_deviations["acoustic"] else 0.0

        # Weighted composite score (requires cross-domain agreement or extreme single-domain divergence)
        # Normal motion causes mild single-domain sound/vibration bumps, which is NORMAL.
        composite_z = 0.5 * elec_z + 0.3 * vib_z + 0.2 * sound_z

        # Sigmoid normalization into [0.0, 1.0] centered at z = 3.0
        anomaly_score = float(1.0 / (1.0 + np.exp(-1.5 * (composite_z - 3.0))))
        anomaly_score = float(np.clip(anomaly_score, 0.0, 1.0))

        # True anomaly requires score >= threshold AND significant multi-feature departure
        is_anomaly = (anomaly_score >= self.anomaly_threshold) and (len(contributions) >= 2)

        return {
            "status": "ANOMALY" if is_anomaly else "NORMAL",
            "anomaly_score": round(anomaly_score, 2),
            "is_anomaly": is_anomaly,
            "contributing_features": contributions[:4]
        }

    def _heuristic_check(self, feature_dict: Dict[str, float]) -> Dict[str, Any]:
        """Rule-based check when untrained."""
        curr = feature_dict.get("current_mean", 0.0)
        s_p2p = feature_dict.get("sound_p2p_max", 0.0)

        is_anom = (curr > NORMAL_LIMITS["current_max_a"]) or (s_p2p > 500)
        score = 0.85 if is_anom else 0.10

        return {
            "status": "ANOMALY" if is_anom else "NORMAL",
            "anomaly_score": score,
            "is_anomaly": is_anom,
            "contributing_features": [("current_overload", curr)] if is_anom else []
        }

    def save(self, filepath: Optional[Path] = None):
        if not filepath:
            filepath = SAVED_MODELS_DIR / "anomaly_model_latest.pkl"
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model_type": self.model_type,
            "is_trained": self.is_trained,
            "baseline_stats": self.baseline_stats,
            "threshold": self.anomaly_threshold,
            "feature_names": self.feature_names,
            "metadata": self.metadata
        }
        with open(filepath, "wb") as f:
            pickle.dump(payload, f)

        meta_path = filepath.with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "AnomalyDetectionModel":
        with open(filepath, "rb") as f:
            payload = pickle.load(f)

        instance = cls(model_type=payload.get("model_type", "statistical"))
        instance.is_trained = payload.get("is_trained", False)
        instance.baseline_stats = payload.get("baseline_stats", {})
        instance.anomaly_threshold = payload.get("threshold", 0.65)
        instance.feature_names = payload.get("feature_names", list(FEATURE_COLUMNS))
        instance.metadata = payload.get("metadata", {})
        return instance

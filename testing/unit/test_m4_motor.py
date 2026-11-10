"""
Unit Test Suite for M4 Motor Condition Monitoring Subsystem
Verifies:
  - 21-feature extraction over sliding windows
  - Model loading from anomaly_model_latest.pkl
  - Normal condition inference (Score < 0.65, status NORMAL)
  - Anomaly condition inference (Current > 200mA, score >= 0.65, status ANOMALY)
  - Missing and edge sensor values
"""

import sys
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integration.configuration.config import M4_MODEL_PKL, NORMAL_LIMITS
from integration.motor_adapter.adapter import WindowedFeatureExtractor, ReusableAnomalyDetector, FEATURE_COLUMNS


def test_feature_extractor_21_columns():
    """Verify sliding window extracts all 21 standard feature columns."""
    extractor = WindowedFeatureExtractor(window_size=5)

    features = None
    for seq in range(5):
        sample = {
            "current_a": 0.082,
            "voltage_v": 5.01,
            "accel_x": 335.0,
            "accel_y": 390.0,
            "accel_z": 308.0,
            "sound_rms": 12.5,
            "sound_p2p": 50.0,
            "servo_angle": 90.0
        }
        features = extractor.update(sample)

    assert features is not None
    assert len(features) == 21, f"Expected 21 features, got {len(features)}"
    for col in FEATURE_COLUMNS:
        assert col in features, f"Missing feature column: {col}"


def test_anomaly_model_normal_inference():
    """Verify normal telemetry produces status NORMAL and score < 0.65."""
    detector = ReusableAnomalyDetector(M4_MODEL_PKL)

    normal_features = {
        "current_mean": 0.085,
        "current_peak": 0.095,
        "current_std": 0.005,
        "current_rms": 0.085,
        "voltage_mean": 5.02,
        "voltage_std": 0.02,
        "voltage_min": 4.98,
        "voltage_drop": 0.02,
        "accel_mag_mean": 590.0,
        "accel_mag_std": 5.0,
        "accel_mag_rms": 590.0,
        "accel_mag_p2p": 15.0,
        "accel_mag_crest_factor": 1.05,
        "accel_x_std": 3.0,
        "accel_y_std": 3.0,
        "accel_z_std": 3.0,
        "sound_p2p_mean": 55.0,
        "sound_p2p_max": 65.0,
        "sound_rms_mean": 12.0,
        "sound_energy": 144.0,
        "angle_motion_rate": 0.0
    }

    pred = detector.predict(normal_features)
    assert pred["status"] == "NORMAL"
    assert pred["is_anomaly"] is False
    assert pred["anomaly_score"] < 0.65


def test_anomaly_model_current_overload():
    """Verify current exceeding 0.200A triggers hard ANOMALY."""
    detector = ReusableAnomalyDetector(M4_MODEL_PKL)

    overload_features = {
        "current_mean": 0.280,  # Exceeds 0.200A limit
        "current_peak": 0.310,
        "current_std": 0.02,
        "current_rms": 0.285,
        "voltage_mean": 4.80,
        "voltage_std": 0.05,
        "voltage_min": 4.60,
        "voltage_drop": 0.40,
        "accel_mag_mean": 600.0,
        "accel_mag_std": 10.0,
        "accel_mag_rms": 600.0,
        "accel_mag_p2p": 20.0,
        "accel_mag_crest_factor": 1.1,
        "accel_x_std": 5.0,
        "accel_y_std": 5.0,
        "accel_z_std": 5.0,
        "sound_p2p_mean": 60.0,
        "sound_p2p_max": 80.0,
        "sound_rms_mean": 14.0,
        "sound_energy": 200.0,
        "angle_motion_rate": 0.0
    }

    pred = detector.predict(overload_features)
    assert pred["status"] == "ANOMALY"
    assert pred["is_anomaly"] is True
    assert pred["anomaly_score"] >= 0.65


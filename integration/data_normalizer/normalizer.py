"""
Unified Data Normalizer for M5
Standardizes incoming data packets from vision and motor modules
into validated, serializable, ISO-8601 compliant dictionaries.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional


def get_iso_timestamp() -> str:
    """Returns current UTC timestamp in ISO-8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def normalize_vision_result(
    sample_id: Optional[str] = None,
    helmet_detected: bool = False,
    gloves_detected: bool = False,
    head_detected: bool = False,
    bare_hand_detected: bool = False,
    helmet_confidence: float = 0.0,
    gloves_confidence: float = 0.0,
    inspection_status: str = "IDLE",
    inspection_reason: str = "",
    detections: Optional[List[Dict[str, Any]]] = None,
    source_mode: str = "webcam",
    processing_ms: float = 0.0,
    led_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs normalized vision inspection event dictionary.
    """
    if sample_id is None:
        sample_id = f"SMP-{uuid.uuid4().hex[:8].upper()}"

    if detections is None:
        detections = []

    if led_state is None:
        led_state = {
            "green": False,
            "yellow": False,
            "red_blinking": False,
            "active_condition": "OFF",
            "active_label": "ALL LEDS OFF"
        }

    return {
        "module": "vision",
        "sample_id": str(sample_id),
        "timestamp": get_iso_timestamp(),
        "helmet_detected": bool(helmet_detected),
        "gloves_detected": bool(gloves_detected),
        "head_detected": bool(head_detected),
        "bare_hand_detected": bool(bare_hand_detected),
        "helmet_confidence": round(float(helmet_confidence), 4),
        "gloves_confidence": round(float(gloves_confidence), 4),
        "inspection_status": str(inspection_status),  # "PASS", "FAIL", "IDLE"
        "inspection_reason": str(inspection_reason),
        "detections": detections,
        "source_mode": str(source_mode),  # "webcam", "image_upload", "recorded_video"
        "processing_ms": round(float(processing_ms), 2),
        "led_state": led_state
    }


def normalize_motor_telemetry(
    timestamp_ms: Optional[int] = None,
    sequence: int = 0,
    servo_angle: float = 0.0,
    voltage: float = 5.0,
    current: float = 0.0,
    accel_x: float = 330.0,
    accel_y: float = 390.0,
    accel_z: float = 308.0,
    sound_rms: float = 0.0,
    sound_p2p: float = 0.0,
    anomaly_status: str = "NORMAL",
    anomaly_score: float = 0.0,
    is_anomaly: bool = False,
    contributing_features: Optional[List[Any]] = None,
    source_mode: str = "RECORDED_DATA"
) -> Dict[str, Any]:
    """
    Constructs normalized motor condition monitoring telemetry dictionary.
    """
    if contributing_features is None:
        contributing_features = []

    return {
        "module": "motor",
        "timestamp": get_iso_timestamp(),
        "timestamp_ms": int(timestamp_ms) if timestamp_ms is not None else 0,
        "sequence": int(sequence),
        "servo_angle": round(float(servo_angle), 1),
        "voltage": round(float(voltage), 3),
        "current": round(float(current), 4),
        "accel_x": round(float(accel_x), 1),
        "accel_y": round(float(accel_y), 1),
        "accel_z": round(float(accel_z), 1),
        "sound_rms": round(float(sound_rms), 2),
        "sound_p2p": round(float(sound_p2p), 1),
        "anomaly_status": str(anomaly_status),  # "NORMAL", "ELEVATED", "ANOMALY"
        "anomaly_score": round(float(anomaly_score), 4),
        "is_anomaly": bool(is_anomaly),
        "contributing_features": contributing_features,
        "source_mode": str(source_mode)  # "LIVE_MQTT", "RECORDED_DATA", "CSV_REPLAY", "SIMULATED"
    }


def create_system_event(
    module: str,
    event_type: str,
    severity: str = "INFO",
    title: str = "",
    description: str = "",
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs unified system event for alert tracking and bus broadcast.
    """
    if data is None:
        data = {}

    return {
        "event_id": f"EVT-{uuid.uuid4().hex[:12].upper()}",
        "module": str(module),
        "event_type": str(event_type),
        "timestamp": get_iso_timestamp(),
        "severity": str(severity).upper(),  # "INFO", "WARNING", "CRITICAL"
        "title": str(title),
        "description": str(description),
        "data": data,
        "acknowledged": False
    }


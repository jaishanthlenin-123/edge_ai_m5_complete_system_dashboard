"""
Unified Configuration Module for M5 Integrated System
Handles Windows local paths, model locations, data replay parameters,
and communication settings.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SOURCE_PROJECTS_DIR = BASE_DIR / "source_projects"
INTEGRATION_DIR = BASE_DIR / "integration"
BACKEND_DIR = BASE_DIR / "backend"
DASHBOARD_DIR = BASE_DIR / "dashboard"
INSPECTION_STATION_DIR = BASE_DIR / "inspection_station"
MOTOR_MONITORING_DIR = BASE_DIR / "motor_monitoring"
MEDIA_DIR = BASE_DIR / "media"
EVIDENCE_DIR = BASE_DIR / "evidence"
DOCUMENTATION_DIR = BASE_DIR / "documentation"

# Database Configuration
DATABASE_DIR = BACKEND_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
M5_DATABASE_PATH = DATABASE_DIR / "m5_integrated_system.db"

# M3 Vision Configuration
M3_MODEL_PATH = SOURCE_PROJECTS_DIR / "m3_vision" / "models" / "best.pt"
M3_SAMPLES_DIR = SOURCE_PROJECTS_DIR / "m3_vision" / "samples"
DEFAULT_CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.45"))
INFERENCE_IMAGE_SIZE = int(os.getenv("INFERENCE_IMAGE_SIZE", "640"))

# Model Class Labels in best.pt
CLASS_NAMES = {
    0: "gloves",
    1: "head",
    2: "helmet"
}

# M4 Motor Monitoring Configuration
M4_MODEL_PKL = SOURCE_PROJECTS_DIR / "m4_motor" / "anomaly_detection" / "anomaly_model_latest.pkl"
M4_MODEL_JSON = SOURCE_PROJECTS_DIR / "m4_motor" / "anomaly_detection" / "anomaly_model_latest.json"
M4_RECORDED_DB = SOURCE_PROJECTS_DIR / "m4_motor" / "database" / "telemetry_history.db"
M4_NORMAL_CSV = SOURCE_PROJECTS_DIR / "m4_motor" / "datasets" / "normal" / "servo_normal_20261106_143433.csv"
M4_RAW_CSV = SOURCE_PROJECTS_DIR / "m4_motor" / "datasets" / "raw" / "servo_telemetry_20261106_133524.csv"

# Physical Operational Boundaries (SG90 Servo Rig)
NORMAL_LIMITS = {
    "voltage_min_v": 4.50,
    "voltage_max_v": 5.50,
    "current_max_a": 0.200,   # Anomaly limit: > 200mA
    "accel_min": 100,
    "accel_max": 900,
    "sound_p2p_max": 600,
    "sound_rms_max": 150.0
}
ANOMALY_THRESHOLD = 0.65

# MQTT Configuration (Optional Live Hook)
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_PREFIX = "motor/servo01"
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# Server Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1")

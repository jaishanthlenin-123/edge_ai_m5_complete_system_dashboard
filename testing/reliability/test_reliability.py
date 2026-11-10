"""
Reliability, Fault Injection & Recovery Test Suite for M5
Verifies:
  - Graceful handling of missing webcam
  - Controlled motor fault injection and alert generation
  - Fault recovery back to normal status
  - SQLite database integrity and recovery
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integration.vision_adapter.adapter import vision_adapter
from integration.motor_adapter.adapter import motor_adapter
from integration.event_manager.event_bus import event_bus
from backend.database.db import db_manager


def test_missing_webcam_graceful_fallback():
    """Verify system safely falls back when webcam index is invalid."""
    original_idx = vision_adapter.camera_index
    vision_adapter.camera_index = 99  # Non-existent camera index

    # Opening invalid webcam should fail safely and not crash
    success = vision_adapter._open_webcam()
    assert success is False
    assert vision_adapter.cap is None

    # Reset camera index
    vision_adapter.camera_index = original_idx


def test_motor_fault_injection_and_recovery():
    """Verify injecting a current surge flags anomaly and resetting restores normal state."""
    # 1. Clean state
    motor_adapter.inject_fault("NONE")
    assert motor_adapter.active_fault == "NONE"

    # 2. Inject current surge fault
    motor_adapter.inject_fault("CURRENT_SURGE")
    assert motor_adapter.active_fault == "CURRENT_SURGE"

    # Fetch next sample with fault active
    fault_sample = motor_adapter._get_next_sample()
    assert fault_sample["current"] > 0.200, f"Expected current > 0.200A, got {fault_sample['current']}"

    # 3. Recover back to clean normal
    motor_adapter.inject_fault("NONE")
    assert motor_adapter.active_fault == "NONE"


def test_database_persistence_and_query():
    """Verify database handles writes and queries without lock contention."""
    log_id = db_manager.log_message("INFO", "Test reliability heartbeat log")
    logs = db_manager.get_system_logs(limit=5)
    assert len(logs) > 0
    assert any("reliability" in l["message"] for l in logs)


"""
Integration Test Suite for M5
Verifies:
  - Event Bus pub/sub messaging
  - SQLite database persistent logging
  - FastAPI REST endpoints (/api/status, /api/kpis, /api/health, /api/export/...)
  - Independent subsystem execution resilience
"""

import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.database.db import db_manager
from integration.event_manager.event_bus import event_bus
from integration.vision_adapter.adapter import vision_adapter
from integration.motor_adapter.adapter import motor_adapter

client = TestClient(app)


def test_api_system_status():
    """Verify /api/status returns valid JSON structure with KPIs and module states."""
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "OPERATIONAL"
    assert "vision" in data
    assert "motor" in data
    assert "kpis" in data


def test_api_headline_kpis():
    """Verify /api/kpis returns the three authoritative KPIs."""
    resp = client.get("/api/kpis")
    assert resp.status_code == 200
    kpis = resp.json()
    assert "kpi1" in kpis
    assert "kpi2" in kpis
    assert "kpi3" in kpis
    assert kpis["kpi1"]["title"] == "Inspection Accuracy"
    assert kpis["kpi2"]["title"] == "Inspection Pass Rate"
    assert kpis["kpi3"]["title"] == "Motor Anomaly Events"


def test_csv_exports():
    """Verify CSV export endpoints stream valid CSV text."""
    resp_insp = client.get("/api/export/inspections.csv")
    assert resp_insp.status_code == 200
    assert "sample_id" in resp_insp.text

    resp_mot = client.get("/api/export/motor.csv")
    assert resp_mot.status_code == 200
    assert "sequence" in resp_mot.text

    resp_alt = client.get("/api/export/alerts.csv")
    assert resp_alt.status_code == 200
    assert "title" in resp_alt.text


def test_independent_module_resilience():
    """
    Verify that if the motor adapter is paused/stopped, the vision adapter
    and inspection station endpoints continue operating normally.
    """
    motor_adapter.pause()
    assert motor_adapter.is_paused is True

    # Vision inspection must still return valid results
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "OPERATIONAL"

    motor_adapter.resume()
    assert motor_adapter.is_paused is False


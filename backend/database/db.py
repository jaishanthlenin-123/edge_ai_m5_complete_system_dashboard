"""
Unified SQLite Database Service for M5
Handles schemas, automated event persistence, querying, and CSV exports.
"""

import io
import csv
import sqlite3
import threading
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from integration.configuration.config import M5_DATABASE_PATH
from integration.data_normalizer.normalizer import get_iso_timestamp

logger = logging.getLogger("m5.database")


class DatabaseManager:
    """Thread-safe SQLite database manager for M5."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or M5_DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()

            # Inspections table
            c.execute("""
                CREATE TABLE IF NOT EXISTS inspections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id TEXT,
                    timestamp TEXT NOT NULL,
                    source_mode TEXT NOT NULL,
                    helmet_detected INTEGER NOT NULL,
                    gloves_detected INTEGER NOT NULL,
                    head_detected INTEGER NOT NULL,
                    bare_hand_detected INTEGER NOT NULL,
                    helmet_confidence REAL,
                    gloves_confidence REAL,
                    inspection_status TEXT NOT NULL,
                    inspection_reason TEXT,
                    processing_ms REAL,
                    ground_truth_label TEXT,
                    is_correct INTEGER
                )
            """)

            # Motor telemetry table
            c.execute("""
                CREATE TABLE IF NOT EXISTS motor_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    timestamp_ms INTEGER,
                    sequence INTEGER,
                    servo_angle REAL,
                    voltage REAL,
                    current REAL,
                    accel_x REAL,
                    accel_y REAL,
                    accel_z REAL,
                    sound_rms REAL,
                    sound_p2p REAL,
                    anomaly_status TEXT NOT NULL,
                    anomaly_score REAL,
                    is_anomaly INTEGER NOT NULL,
                    source_mode TEXT NOT NULL
                )
            """)

            # Alerts table
            c.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE,
                    timestamp TEXT NOT NULL,
                    module TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0
                )
            """)

            # System logs table
            c.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)

            conn.commit()
            conn.close()
            logger.info(f"M5 Database initialized at {self.db_path}")

    def insert_inspection(self, data: Dict[str, Any]) -> int:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO inspections (
                    sample_id, timestamp, source_mode, helmet_detected, gloves_detected,
                    head_detected, bare_hand_detected, helmet_confidence, gloves_confidence,
                    inspection_status, inspection_reason, processing_ms, ground_truth_label, is_correct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("sample_id", ""),
                data.get("timestamp", get_iso_timestamp()),
                data.get("source_mode", "webcam"),
                1 if data.get("helmet_detected") else 0,
                1 if data.get("gloves_detected") else 0,
                1 if data.get("head_detected") else 0,
                1 if data.get("bare_hand_detected") else 0,
                float(data.get("helmet_confidence", 0.0)),
                float(data.get("gloves_confidence", 0.0)),
                data.get("inspection_status", "IDLE"),
                data.get("inspection_reason", ""),
                float(data.get("processing_ms", 0.0)),
                data.get("ground_truth_label"),
                1 if data.get("is_correct") is True else (0 if data.get("is_correct") is False else None)
            ))
            row_id = c.lastrowid
            conn.commit()
            conn.close()
            return row_id

    def insert_motor_telemetry(self, data: Dict[str, Any]) -> int:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO motor_telemetry (
                    timestamp, timestamp_ms, sequence, servo_angle, voltage,
                    current, accel_x, accel_y, accel_z, sound_rms, sound_p2p,
                    anomaly_status, anomaly_score, is_anomaly, source_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", get_iso_timestamp()),
                int(data.get("timestamp_ms", 0)),
                int(data.get("sequence", 0)),
                float(data.get("servo_angle", 0.0)),
                float(data.get("voltage", 5.0)),
                float(data.get("current", 0.0)),
                float(data.get("accel_x", 330.0)),
                float(data.get("accel_y", 390.0)),
                float(data.get("accel_z", 308.0)),
                float(data.get("sound_rms", 0.0)),
                float(data.get("sound_p2p", 0.0)),
                data.get("anomaly_status", "NORMAL"),
                float(data.get("anomaly_score", 0.0)),
                1 if data.get("is_anomaly") else 0,
                data.get("source_mode", "RECORDED_DATA")
            ))
            row_id = c.lastrowid
            conn.commit()
            conn.close()
            return row_id

    def insert_alert(self, event: Dict[str, Any]) -> int:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            try:
                c.execute("""
                    INSERT OR IGNORE INTO alerts (
                        event_id, timestamp, module, severity, title, description, acknowledged
                    ) VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (
                    event.get("event_id", ""),
                    event.get("timestamp", get_iso_timestamp()),
                    event.get("module", "system"),
                    event.get("severity", "WARNING"),
                    event.get("title", "Alert"),
                    event.get("description", ""),
                ))
                row_id = c.lastrowid
                conn.commit()
            finally:
                conn.close()
            return row_id

    def log_message(self, level: str, message: str):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO system_logs (timestamp, level, message)
                VALUES (?, ?, ?)
            """, (get_iso_timestamp(), level.upper(), message))
            conn.commit()
            conn.close()

    def get_inspections(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM inspections ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows

    def get_motor_telemetry(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM motor_telemetry ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows

    def get_alerts(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows

    def acknowledge_alert(self, alert_id: int) -> bool:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
            updated = c.rowcount > 0
            conn.commit()
            conn.close()
            return updated

    def get_system_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM system_logs ORDER BY id DESC LIMIT ?", (limit,))
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows

    def export_inspections_csv(self) -> str:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM inspections ORDER BY id ASC")
            rows = c.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([d[0] for d in c.description])
            for r in rows:
                writer.writerow(list(r))
            conn.close()
            return output.getvalue()

    def export_motor_csv(self) -> str:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM motor_telemetry ORDER BY id ASC")
            rows = c.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([d[0] for d in c.description])
            for r in rows:
                writer.writerow(list(r))
            conn.close()
            return output.getvalue()

    def export_alerts_csv(self) -> str:
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM alerts ORDER BY id ASC")
            rows = c.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([d[0] for d in c.description])
            for r in rows:
                writer.writerow(list(r))
            conn.close()
            return output.getvalue()


# Global Singleton Database Manager
db_manager = DatabaseManager()


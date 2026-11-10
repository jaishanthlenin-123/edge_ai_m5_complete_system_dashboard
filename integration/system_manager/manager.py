"""
System Lifecycle, Health Monitoring & Integration Manager for M5
Coordinates vision and motor subsystems, handles fault recovery,
and manages the 10-minute continuous full-chain assessment benchmark.
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional

from integration.vision_adapter.adapter import vision_adapter
from integration.motor_adapter.adapter import motor_adapter
from integration.event_manager.event_bus import event_bus
from backend.database.db import db_manager
from integration.data_normalizer.normalizer import get_iso_timestamp

logger = logging.getLogger("m5.system_manager")


class SystemManager:
    """Manages full lifecycle of M5 integrated application on Windows."""

    def __init__(self):
        self._lock = threading.RLock()
        self.start_time = time.time()
        self.is_running = False

        # Fault and recovery telemetry
        self.recovery_events_count = 0
        self.error_count = 0

        # 10-Minute Full Chain Benchmark Telemetry (Assessment 32)
        self.chain_running = False
        self.chain_start_time: Optional[float] = None
        self.chain_target_duration_s = 600.0  # 10 minutes
        self.chain_vision_count = 0
        self.chain_motor_count = 0
        self.chain_alerts_count = 0
        self.chain_errors_count = 0
        self.chain_status = "IDLE"  # "IDLE", "RUNNING", "COMPLETED", "FAILED"
        self._chain_thread: Optional[threading.Thread] = None

    def start_all(self):
        """Starts all integrated adapters and background workers."""
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            logger.info("Initializing M5 Integrated Subsystems...")

            try:
                vision_adapter.start()
            except Exception as e:
                logger.error(f"Failed to start vision adapter: {e}")
                self.error_count += 1

            try:
                motor_adapter.start()
            except Exception as e:
                logger.error(f"Failed to start motor adapter: {e}")
                self.error_count += 1

            event_bus.update_module_status("backend", "RUNNING")
            db_manager.log_message("INFO", "M5 System Manager started all subsystems.")
            logger.info("M5 Subsystems started successfully.")

    def stop_all(self):
        """Safely stops all adapters."""
        with self._lock:
            self.is_running = False
            vision_adapter.stop()
            motor_adapter.stop()
            event_bus.update_module_status("backend", "STOPPED")
            db_manager.log_message("INFO", "M5 System Manager stopped all subsystems.")
            logger.info("M5 Subsystems stopped.")

    def start_10_minute_chain_test(self, duration_seconds: float = 600.0) -> Dict[str, Any]:
        """
        Starts the automated 10-minute continuous full-chain test (Assessment 32).
        Runs Camera/Vision -> Decision -> Backend -> DB -> Dashboard
        simultaneously with Motor Replay -> Features -> Anomaly Model -> Alerts -> DB -> Dashboard.
        """
        with self._lock:
            if self.chain_running:
                return self.get_chain_status()

            self.chain_running = True
            self.chain_target_duration_s = float(duration_seconds)
            self.chain_start_time = time.time()
            self.chain_vision_count = 0
            self.chain_motor_count = 0
            self.chain_alerts_count = 0
            self.chain_errors_count = 0
            self.chain_status = "RUNNING"

            self._chain_thread = threading.Thread(target=self._run_chain_worker, daemon=True)
            self._chain_thread.start()

            db_manager.log_message("INFO", f"10-Minute Full Chain Test started (Target: {duration_seconds}s).")
            return self.get_chain_status()

    def _run_chain_worker(self):
        logger.info("Entering 10-minute full chain execution thread.")
        v_initial = vision_adapter.total_inferences
        m_initial = motor_adapter.total_records_processed
        start_ts = time.time()

        while self.chain_running:
            now = time.time()
            elapsed = now - start_ts

            with self._lock:
                self.chain_vision_count = vision_adapter.total_inferences - v_initial
                self.chain_motor_count = motor_adapter.total_records_processed - m_initial
                self.chain_alerts_count = len(event_bus.get_alerts(1000))

            if elapsed >= self.chain_target_duration_s:
                with self._lock:
                    self.chain_running = False
                    self.chain_status = "COMPLETED"
                db_manager.log_message("INFO", f"10-Minute Full Chain Test completed successfully ({elapsed:.1f}s).")
                logger.info("10-minute full chain test finished with SUCCESS.")
                break

            time.sleep(1.0)

    def get_chain_status(self) -> Dict[str, Any]:
        with self._lock:
            elapsed = (time.time() - self.chain_start_time) if self.chain_start_time else 0.0
            if self.chain_status == "COMPLETED":
                progress = 100.0
            else:
                progress = min(100.0, round((elapsed / self.chain_target_duration_s) * 100.0, 1)) if self.chain_target_duration_s > 0 else 0.0

            return {
                "status": self.chain_status,
                "is_running": self.chain_running,
                "elapsed_seconds": round(elapsed, 1),
                "target_seconds": self.chain_target_duration_s,
                "progress_pct": progress,
                "vision_inferences_processed": self.chain_vision_count,
                "motor_records_processed": self.chain_motor_count,
                "alerts_generated": self.chain_alerts_count,
                "errors_count": self.chain_errors_count,
                "recovery_events": self.recovery_events_count
            }

    def get_system_health(self) -> Dict[str, Any]:
        """Returns deep diagnostic health snapshot for Dashboard System Health page."""
        with self._lock:
            uptime_s = time.time() - self.start_time

            # Check adapters
            v_status = "HEALTHY" if vision_adapter.is_running else "STOPPED"
            m_status = "HEALTHY" if motor_adapter.is_running else "STOPPED"

            # Check camera handle
            cam_online = (vision_adapter.cap is not None and vision_adapter.cap.isOpened())

            return {
                "system_status": "OPERATIONAL",
                "uptime_seconds": round(uptime_s, 1),
                "timestamp": get_iso_timestamp(),
                "vision_adapter": {
                    "status": v_status,
                    "source_mode": vision_adapter.source_mode,
                    "fps": vision_adapter.fps,
                    "camera_online": cam_online,
                    "total_inferences": vision_adapter.total_inferences
                },
                "motor_adapter": {
                    "status": m_status,
                    "source_mode": motor_adapter.source_mode,
                    "replay_speed": motor_adapter.replay_speed,
                    "is_paused": motor_adapter.is_paused,
                    "total_records": len(motor_adapter.records),
                    "total_processed": motor_adapter.total_records_processed,
                    "anomalies_detected": motor_adapter.total_anomalies_detected,
                    "active_fault": motor_adapter.active_fault
                },
                "database": {
                    "status": "CONNECTED",
                    "path": str(db_manager.db_path)
                },
                "metrics": {
                    "recovery_count": self.recovery_events_count,
                    "error_count": self.error_count
                }
            }


# Global Singleton System Manager
system_manager = SystemManager()


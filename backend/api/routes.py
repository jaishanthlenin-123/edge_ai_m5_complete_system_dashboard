"""
FastAPI REST and WebSocket Routes for M5 Unified System
Provides comprehensive endpoints for dashboard telemetry, live MJPEG feeds,
historical queries, CSV exports, replay control, and assessment runners.
"""

import os
import io
import cv2
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Response, Query
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse

from integration.vision_adapter.adapter import vision_adapter
from integration.motor_adapter.adapter import motor_adapter
from integration.system_manager.manager import system_manager
from integration.event_manager.event_bus import event_bus
from backend.database.db import db_manager
from backend.services.kpi_service import kpi_service
from inspection_station.inspection_engine.runner import InspectionStationRunner

logger = logging.getLogger("m5.routes")
api_router = APIRouter()


# -----------------------------------------------------------------------------
# 1. System Overview & Status Endpoints
# -----------------------------------------------------------------------------
@api_router.get("/status")
def get_system_status():
    """Returns combined system status, latest vision, latest motor, and KPIs."""
    return {
        "status": "OPERATIONAL",
        "vision": vision_adapter.get_latest_result(),
        "motor": motor_adapter.get_latest_telemetry(),
        "kpis": kpi_service.get_headline_kpis(),
        "alerts": event_bus.get_alerts(limit=5),
        "health": system_manager.get_system_health()
    }


@api_router.get("/kpis")
def get_headline_kpis():
    """Returns the three required M5 headline KPIs."""
    return kpi_service.get_headline_kpis()


@api_router.get("/health")
def get_health_diagnostics():
    """Returns full system diagnostics and recent application logs."""
    return {
        "health": system_manager.get_system_health(),
        "logs": db_manager.get_system_logs(limit=25)
    }


# -----------------------------------------------------------------------------
# 2. Vision Inspection Endpoints & MJPEG Stream
# -----------------------------------------------------------------------------
def generate_mjpeg_stream():
    """Generates continuous multipart MJPEG video stream."""
    import time
    while True:
        frame_bytes = vision_adapter.get_latest_jpeg()
        if frame_bytes is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.04)


@api_router.get("/vision/stream")
def get_vision_stream():
    """MJPEG live video stream endpoint for dashboard video player."""
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@api_router.get("/vision/latest")
def get_latest_vision():
    """Returns latest normalized vision inspection metadata."""
    return vision_adapter.get_latest_result()


@api_router.post("/vision/mode")
def set_vision_source_mode(mode: str = Form(...), file_path: Optional[str] = Form(None)):
    """Switches vision input mode: 'webcam', 'image_upload', 'recorded_video'."""
    try:
        vision_adapter.set_source_mode(mode, file_path)
        return {"status": "success", "mode": vision_adapter.source_mode}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@api_router.post("/vision/inspect")
async def inspect_uploaded_image(file: UploadFile = File(...)):
    """Single-shot inspection on uploaded test image."""
    try:
        contents = await file.read()
        import numpy as np
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return JSONResponse(status_code=400, content={"error": "Invalid image format"})

        sample_id = f"UPLOAD-{file.filename}"
        norm_res, _ = vision_adapter.inspect_single_image(img, sample_id=sample_id)
        db_manager.insert_inspection(norm_res)
        return norm_res
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# -----------------------------------------------------------------------------
# 3. Motor Telemetry & Replay Control Endpoints
# -----------------------------------------------------------------------------
@api_router.get("/motor/latest")
def get_latest_motor():
    """Returns latest motor telemetry sample and anomaly status."""
    return motor_adapter.get_latest_telemetry()


@api_router.get("/motor/status")
def get_motor_replay_status():
    """Returns current replay status, speed, total records, and active faults."""
    return motor_adapter.get_status()


@api_router.post("/motor/replay/control")
def control_motor_replay(action: str = Form(...), value: Optional[str] = Form(None)):
    """Replay controls: 'play', 'pause', 'resume', 'speed', 'seek', 'reset'."""
    action = action.lower()
    if action == "play" or action == "resume":
        motor_adapter.resume()
    elif action == "pause":
        motor_adapter.pause()
    elif action == "speed" and value:
        motor_adapter.set_speed(float(value))
    elif action == "seek" and value:
        motor_adapter.seek(int(value))
    elif action == "reset":
        motor_adapter.seek(0)
    else:
        return JSONResponse(status_code=400, content={"error": f"Unknown action {action}"})

    return {"status": "success", "replay_state": motor_adapter.get_status()}


@api_router.post("/motor/fault_injection")
def inject_motor_fault(fault_type: str = Form(...)):
    """Injects controlled software fault: 'NONE', 'CURRENT_SURGE', 'BEARING_GRIND', 'BROWNOUT'."""
    try:
        motor_adapter.inject_fault(fault_type)
        return {"status": "success", "active_fault": motor_adapter.active_fault}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# -----------------------------------------------------------------------------
# 4. History Queries & CSV Export Endpoints
# -----------------------------------------------------------------------------
@api_router.get("/history/inspections")
def get_inspection_history(limit: int = 50, offset: int = 0):
    return {"inspections": db_manager.get_inspections(limit, offset)}


@api_router.get("/history/motor")
def get_motor_history(limit: int = 50, offset: int = 0):
    return {"telemetry": db_manager.get_motor_telemetry(limit, offset)}


@api_router.get("/history/alerts")
def get_alerts_history(limit: int = 50, offset: int = 0):
    return {"alerts": db_manager.get_alerts(limit, offset)}


@api_router.post("/alerts/acknowledge/{alert_id}")
def acknowledge_alert(alert_id: int):
    success = db_manager.acknowledge_alert(alert_id)
    return {"status": "success" if success else "not_found"}


@api_router.get("/export/inspections.csv")
def export_inspections_csv():
    csv_data = db_manager.export_inspections_csv()
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=m5_inspections.csv"}
    )


@api_router.get("/export/motor.csv")
def export_motor_csv():
    csv_data = db_manager.export_motor_csv()
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=m5_motor_telemetry.csv"}
    )


@api_router.get("/export/alerts.csv")
def export_alerts_csv():
    csv_data = db_manager.export_alerts_csv()
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=m5_alerts.csv"}
    )


# -----------------------------------------------------------------------------
# 5. Assessment Verification Endpoints (Stations 31, 32, 35)
# -----------------------------------------------------------------------------
@api_router.get("/assessment/pass_fail_20")
def run_or_get_pass_fail_station(execute: bool = False):
    """Runs or returns the 20-sample pass/fail station test."""
    runner = InspectionStationRunner()
    if execute:
        return runner.run_20_sample_station()
    else:
        # Return confusion matrix from current database
        return kpi_service.compute_confusion_matrix()


@api_router.get("/assessment/headline_50")
def run_or_get_headline_benchmark(execute: bool = False):
    """Runs or returns the 50-sample headline metric evaluation."""
    runner = InspectionStationRunner()
    if execute:
        return runner.run_50_sample_headline_benchmark()
    else:
        return kpi_service.get_headline_kpis()["kpi1"]


@api_router.post("/assessment/chain_start")
def start_full_chain_test(duration: float = Form(600.0)):
    """Starts the 10-minute continuous full-chain test (Assessment 32)."""
    return system_manager.start_10_minute_chain_test(duration)


@api_router.get("/assessment/chain_status")
def get_full_chain_status():
    """Returns status and progress of 10-minute full-chain test."""
    return system_manager.get_chain_status()


# -----------------------------------------------------------------------------
# 6. WebSocket Live Telemetry Streaming
# -----------------------------------------------------------------------------
@api_router.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """High-frequency real-time push channel for dashboard charts and indicators."""
    await websocket.accept()
    queue = asyncio.Queue(maxsize=100)
    event_bus.register_async_queue(queue)

    try:
        # Send initial snapshot
        initial_payload = {
            "type": "INITIAL_STATE",
            "vision": vision_adapter.get_latest_result(),
            "motor": motor_adapter.get_latest_telemetry(),
            "kpis": kpi_service.get_headline_kpis(),
            "alerts": event_bus.get_alerts(limit=5)
        }
        await websocket.send_text(json.dumps(initial_payload))

        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event))

    except WebSocketDisconnect:
        logger.info("WebSocket telemetry client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket telemetry error: {e}")
    finally:
        event_bus.unregister_async_queue(queue)

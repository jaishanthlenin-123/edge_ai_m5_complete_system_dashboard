"""
M5 Integrated Application Main Entrypoint (FastAPI)
Hosts Unified Industrial Monitoring Dashboard, REST APIs, and WebSocket Telemetry.
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from integration.configuration.config import DASHBOARD_DIR, SERVER_HOST, SERVER_PORT
from integration.system_manager.manager import system_manager
from integration.event_manager.event_bus import event_bus
from backend.database.db import db_manager
from backend.api.routes import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("m5.main")


# Automatically persist events from event_bus into SQLite database
def on_bus_event(event: dict):
    evt_type = event.get("event_type")
    module = event.get("module")
    data = event.get("data", {})

    if evt_type == "inspection_result" and module == "vision":
        db_manager.insert_inspection(data)
    elif evt_type == "motor_telemetry" and module == "motor":
        # Sample every 5th telemetry record for db storage to prevent excessive disk bloat
        seq = data.get("sequence", 0)
        if seq % 5 == 0 or data.get("is_anomaly"):
            db_manager.insert_motor_telemetry(data)
    elif "alert" in evt_type or event.get("severity") in ("WARNING", "CRITICAL"):
        db_manager.insert_alert(event)


event_bus.subscribe_sync("*", on_bus_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=======================================================")
    logger.info("  STARTING M5 COMPLETE INTEGRATED SYSTEM (WINDOWS)     ")
    logger.info("=======================================================")
    system_manager.start_all()
    yield
    logger.info("Shutting down M5 subsystems...")
    system_manager.stop_all()
    logger.info("M5 application shutdown complete.")


app = FastAPI(
    title="Integrated Vision Inspection & Motor Condition Monitoring System",
    description="Edge AI Milestone 5 (M5) Unified Production Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api")

# Mount Static Frontend
frontend_dir = DASHBOARD_DIR / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
def serve_dashboard():
    """Serves the unified industrial dashboard web application."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "M5 Backend Online. Frontend under construction.",
        "api_docs": "/docs",
        "system_status": "/api/status"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main.py:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)


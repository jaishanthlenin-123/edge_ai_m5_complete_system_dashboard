"""
Central Event Manager & In-Memory Message Bus for M5
Handles decoupled event routing between adapters, database, and WebSocket clients.
"""

import asyncio
import collections
import logging
import threading
from typing import Dict, Any, List, Callable, Optional, Set

from integration.data_normalizer.normalizer import create_system_event, get_iso_timestamp

logger = logging.getLogger("m5.event_bus")


class EventBus:
    """Thread-safe event dispatcher and pub/sub broker for M5."""

    def __init__(self, max_history: int = 500):
        self._lock = threading.RLock()
        self._listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = collections.defaultdict(list)
        self._async_queues: Set[asyncio.Queue] = set()

        # In-memory fast cache
        self._latest_vision: Optional[Dict[str, Any]] = None
        self._latest_motor: Optional[Dict[str, Any]] = None
        self._events_history: collections.deque = collections.deque(maxlen=max_history)
        self._alerts_history: collections.deque = collections.deque(maxlen=max_history)

        # Module health telemetry
        self._module_heartbeats: Dict[str, str] = {
            "vision": get_iso_timestamp(),
            "motor": get_iso_timestamp(),
            "backend": get_iso_timestamp()
        }
        self._module_status: Dict[str, str] = {
            "vision": "READY",
            "motor": "READY",
            "backend": "RUNNING"
        }

    def subscribe_sync(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Registers a synchronous callback for an event type or '*'."""
        with self._lock:
            self._listeners[event_type].append(handler)

    def register_async_queue(self, queue: asyncio.Queue):
        """Registers an asyncio Queue for WebSocket client streaming."""
        with self._lock:
            self._async_queues.add(queue)

    def unregister_async_queue(self, queue: asyncio.Queue):
        """Removes an asyncio Queue."""
        with self._lock:
            self._async_queues.discard(queue)

    def publish(self, event: Dict[str, Any]):
        """Dispatches an event to all registered listeners and async queues."""
        with self._lock:
            event_type = event.get("event_type", "unknown")
            module = event.get("module", "system")

            # Update heartbeats
            self._module_heartbeats[module] = event.get("timestamp", get_iso_timestamp())

            # Store in caches
            if module == "vision" and event_type == "inspection_result":
                self._latest_vision = event
            elif module == "motor" and event_type == "motor_telemetry":
                self._latest_motor = event

            # Track alerts
            if event.get("severity") in ("WARNING", "CRITICAL") or event_type in ("vision_failure", "motor_alert"):
                self._alerts_history.append(event)

            self._events_history.append(event)

            # Synchronous handlers
            handlers = self._listeners.get(event_type, []) + self._listeners.get("*", [])
            for handler in handlers:
                try:
                    handler(event)
                except Exception as ex:
                    logger.error(f"Error in sync event handler for {event_type}: {ex}")

            # Push to WebSocket async queues
            dead_queues = []
            for q in self._async_queues:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    dead_queues.append(q)
                except Exception:
                    dead_queues.append(q)

            for dq in dead_queues:
                self._async_queues.discard(dq)

    def emit_alert(self, module: str, title: str, description: str, severity: str = "WARNING", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convenience method to construct and broadcast an alert event."""
        alert_event = create_system_event(
            module=module,
            event_type=f"{module}_alert" if module in ("vision", "motor") else "system_alert",
            severity=severity,
            title=title,
            description=description,
            data=data or {}
        )
        self.publish(alert_event)
        return alert_event

    def update_module_status(self, module: str, status: str):
        with self._lock:
            self._module_status[module] = status
            self._module_heartbeats[module] = get_iso_timestamp()

    def get_latest_vision(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._latest_vision

    def get_latest_motor(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._latest_motor

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._alerts_history)[-limit:]

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events_history)[-limit:]

    def get_health(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "timestamp": get_iso_timestamp(),
                "modules": dict(self._module_status),
                "heartbeats": dict(self._module_heartbeats),
                "connected_clients": len(self._async_queues)
            }


# Global Singleton Event Bus
event_bus = EventBus()


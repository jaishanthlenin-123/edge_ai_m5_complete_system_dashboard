#!/usr/bin/env python3
"""
Secure MQTT (MQTTS) Publisher & Subscriber Subsystem
Project: SG90 Servo Motor Condition Monitoring and Anomaly Detection System
Target: Raspberry Pi 5

Features:
    - Industry-standard TLS 1.2 / TLS 1.3 encryption (Port 8883)
    - X.509 Certificate verification (Server authentication and optional mutual TLS)
    - Username & Password credential authentication from environment variables
    - Hierarchical M4 MQTT topic publisher:
        * motor/servo01/sensors/imu
        * motor/servo01/sensors/current
        * motor/servo01/sensors/voltage
        * motor/servo01/sensors/audio
        * motor/servo01/status
        * motor/servo01/alerts
        * motor/servo01/health
    - Automatic reconnection handling with exponential backoff
    - Payload validation, ISO 8601 timestamps, QoS 1 delivery guarantee
"""

import os
import ssl
import sys
import json
import time
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False

from raspberry_pi.config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT_TLS,
    MQTT_BROKER_PORT_PLAIN,
    MQTT_USE_TLS,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_CA_CERT,
    MQTT_CLIENT_CERT,
    MQTT_CLIENT_KEY,
    MQTT_TLS_INSECURE,
    MQTT_CLIENT_ID,
    MQTT_KEEPALIVE_S,
    MQTT_DEFAULT_QOS,
    MQTT_TOPICS
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SecureMQTT")


class SecureMQTTClient:
    """Enterprise Secure MQTT Client supporting TLS 1.2/1.3 and Topic Routing."""

    def __init__(
        self,
        broker_host: str = MQTT_BROKER_HOST,
        broker_port: Optional[int] = None,
        use_tls: bool = MQTT_USE_TLS,
        username: Optional[str] = MQTT_USERNAME,
        password: Optional[str] = MQTT_PASSWORD,
        ca_cert: Optional[str] = MQTT_CA_CERT,
        client_cert: Optional[str] = MQTT_CLIENT_CERT,
        client_key: Optional[str] = MQTT_CLIENT_KEY,
        tls_insecure: bool = MQTT_TLS_INSECURE,
        client_id: str = MQTT_CLIENT_ID,
        default_qos: int = MQTT_DEFAULT_QOS
    ):
        if not PAHO_AVAILABLE:
            raise ImportError("paho-mqtt is required. Run: pip install paho-mqtt")

        self.broker_host = broker_host
        self.use_tls = use_tls
        self.broker_port = broker_port or (MQTT_BROKER_PORT_TLS if use_tls else MQTT_BROKER_PORT_PLAIN)
        self.username = username
        self.password = password
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.tls_insecure = tls_insecure
        self.client_id = client_id
        self.default_qos = default_qos

        self.is_connected = False
        self.connection_error: Optional[str] = None
        self.published_messages_count = 0
        self.delivery_acks = 0

        # Custom callbacks
        self.on_message_callback: Optional[Callable] = None
        self.on_connect_callback: Optional[Callable] = None

        # Initialize Paho Client (supporting both v1 and v2 API signatures)
        try:
            # Paho MQTT v2.x
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id
            )
        except AttributeError:
            # Fallback for Paho MQTT v1.x
            self.client = mqtt.Client(client_id=self.client_id)

        self._configure_callbacks()
        self._configure_security()

    def _configure_callbacks(self):
        """Attaches core connection and diagnostic callbacks."""
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        self.client.on_message = self._on_message

    def _configure_security(self):
        """Configures TLS encryption context and credential authentication."""
        # 1. Username / Password Authentication
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
            logger.info("Configured username/password authentication for user: %s", self.username)
        elif self.username:
            self.client.username_pw_set(self.username)

        # 2. TLS Configuration
        if self.use_tls:
            tls_kwargs: Dict[str, Any] = {}
            if self.ca_cert and Path(self.ca_cert).exists():
                tls_kwargs["ca_certs"] = str(self.ca_cert)
                logger.info("Using custom CA certificate: %s", self.ca_cert)
            else:
                # Use default system trust store
                tls_kwargs["ca_certs"] = None
                logger.info("Using system default CA certificate store for TLS verification")

            # Mutual TLS (mTLS) client certificate verification if provided
            if (
                self.client_cert
                and Path(self.client_cert).exists()
                and self.client_key
                and Path(self.client_key).exists()
            ):
                tls_kwargs["certfile"] = str(self.client_cert)
                tls_kwargs["keyfile"] = str(self.client_key)
                logger.info("Configured Mutual TLS (mTLS) client certificate: %s", self.client_cert)

            try:
                # Modern TLS protocol client
                tls_kwargs["tls_version"] = ssl.PROTOCOL_TLS_CLIENT
                self.client.tls_set(**tls_kwargs)
                self.client.tls_insecure_set(self.tls_insecure)
                logger.info("TLS configuration complete (Insecure mode: %s)", self.tls_insecure)
            except Exception as e:
                logger.error("Failed to initialize TLS context: %s", e)
                raise

    def connect(self, timeout_s: float = 5.0) -> bool:
        """Establishes connection to the MQTT broker."""
        try:
            logger.info(
                "Connecting to MQTT broker at %s:%d (TLS: %s)...",
                self.broker_host,
                self.broker_port,
                self.use_tls
            )
            self.client.connect(self.broker_host, self.broker_port, keepalive=MQTT_KEEPALIVE_S)
            self.client.loop_start()

            # Wait for connection confirmation
            start = time.time()
            while not self.is_connected and (time.time() - start) < timeout_s:
                time.sleep(0.05)

            if not self.is_connected:
                logger.warning("Connection timeout after %.1fs", timeout_s)
                return False

            logger.info("Successfully connected to Secure MQTT Broker")
            return True
        except Exception as e:
            self.connection_error = str(e)
            logger.error("Failed to connect to broker: %s", e)
            return False

    def disconnect(self):
        """Cleanly disconnects from the MQTT broker."""
        self.is_connected = False
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Cleanly disconnected from MQTT broker")
        except Exception:
            pass

    # =========================================================================
    # INTERNAL EVENT CALLBACKS
    # =========================================================================
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        # Handle both Paho v1 (rc int) and v2 (reason_code object)
        rc = getattr(reason_code, "value", reason_code)
        if rc == 0:
            self.is_connected = True
            self.connection_error = None
            logger.info("MQTT Broker connection established (rc=0)")
            if self.on_connect_callback:
                self.on_connect_callback(client, userdata, flags, reason_code)
        else:
            self.is_connected = False
            self.connection_error = f"Connection failed with reason code: {rc}"
            logger.error("MQTT connection rejected: %s", self.connection_error)

    def _on_disconnect(self, client, userdata, *args):
        self.is_connected = False
        logger.warning("MQTT Broker disconnected")

    def _on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        self.delivery_acks += 1

    def _on_message(self, client, userdata, message):
        if self.on_message_callback:
            self.on_message_callback(message.topic, message.payload.decode("utf-8"))

    # =========================================================================
    # TOPIC-SPECIFIC PUBLISHING IMPLEMENTATION (M4 REQUIREMENT)
    # =========================================================================
    def publish_json(self, topic: str, payload: Dict[str, Any], qos: Optional[int] = None, retain: bool = False) -> bool:
        """Publishes a structured dictionary as a JSON string to a specific topic."""
        qos = qos if qos is not None else self.default_qos
        try:
            payload_str = json.dumps(payload, separators=(",", ":"))
            info = self.client.publish(topic, payload_str, qos=qos, retain=retain)
            self.published_messages_count += 1
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error("Publish error on topic %s: %s", topic, e)
            return False

    def publish_imu(self, ax: int, ay: int, az: int, timestamp_ms: int, host_ts: Optional[str] = None) -> bool:
        """Publishes accelerometer / IMU vibration data."""
        mag = round((ax**2 + ay**2 + az**2) ** 0.5, 2)
        payload = {
            "timestamp": host_ts or datetime.datetime.now().isoformat(),
            "timestamp_ms": timestamp_ms,
            "sensor": "MPU6050_or_Analog3Axis",
            "accel_x": ax,
            "accel_y": ay,
            "accel_z": az,
            "magnitude": mag,
            "unit": "raw_adc_10bit"
        }
        return self.publish_json(MQTT_TOPICS["imu"], payload)

    def publish_current(self, current_a: float, timestamp_ms: int, host_ts: Optional[str] = None) -> bool:
        """Publishes ACS712 motor current telemetry."""
        status = "NORMAL"
        if current_a > 0.85:
            status = "CRITICAL_OVERCURRENT"
        elif current_a > 0.200:
            status = "ELEVATED_ANOMALY"

        payload = {
            "timestamp": host_ts or datetime.datetime.now().isoformat(),
            "timestamp_ms": timestamp_ms,
            "sensor": "ACS712_5A",
            "current_a": round(current_a, 3),
            "unit": "A",
            "status": status,
            "threshold_a": 0.200
        }
        return self.publish_json(MQTT_TOPICS["current"], payload)

    def publish_voltage(self, voltage_v: float, timestamp_ms: int, host_ts: Optional[str] = None) -> bool:
        """Publishes 0-25V divider supply voltage telemetry."""
        status = "NOMINAL"
        if voltage_v > 0.5 and voltage_v < 4.5:
            status = "BROWNOUT_WARNING"
        elif voltage_v == 0.0:
            status = "DISCONNECTED"

        payload = {
            "timestamp": host_ts or datetime.datetime.now().isoformat(),
            "timestamp_ms": timestamp_ms,
            "sensor": "VOLTAGE_DIVIDER_5TO1",
            "voltage_v": round(voltage_v, 2),
            "unit": "V",
            "status": status,
            "nominal_v": 5.0
        }
        return self.publish_json(MQTT_TOPICS["voltage"], payload)

    def publish_audio(self, sound_rms: float, sound_p2p: int, timestamp_ms: int, host_ts: Optional[str] = None) -> bool:
        """Publishes MAX9814 microphone acoustic noise metrics."""
        payload = {
            "timestamp": host_ts or datetime.datetime.now().isoformat(),
            "timestamp_ms": timestamp_ms,
            "sensor": "MAX9814_MIC",
            "sound_rms": round(sound_rms, 2),
            "sound_p2p": sound_p2p,
            "acoustic_status": "HIGH_NOISE" if sound_p2p > 400 else "NORMAL"
        }
        return self.publish_json(MQTT_TOPICS["audio"], payload)

    def publish_servo_status(
        self,
        servo_angle: int,
        operational_state: str = "CYCLING",
        anomaly_score: float = 0.0,
        is_anomaly: bool = False,
        host_ts: Optional[str] = None
    ) -> bool:
        """Publishes overall servo actuation and health status."""
        payload = {
            "timestamp": host_ts or datetime.datetime.now().isoformat(),
            "servo_id": "servo01",
            "servo_angle": servo_angle,
            "state": operational_state,
            "anomaly_score": round(anomaly_score, 2),
            "condition": "FAULT" if is_anomaly else "NORMAL",
            "command_sequence": [30, 90, 150, 90]
        }
        return self.publish_json(MQTT_TOPICS["status"], payload, retain=True)

    def publish_alert(
        self,
        severity: str,
        channel: str,
        message: str,
        metric_value: float,
        threshold: float,
        host_ts: Optional[str] = None
    ) -> bool:
        """Publishes critical condition alerts to the dedicated alerts topic."""
        payload = {
            "timestamp": host_ts or datetime.datetime.now().isoformat(),
            "severity": severity,
            "channel": channel,
            "message": message,
            "metric_value": metric_value,
            "threshold": threshold,
            "device": "rpi5-servo-edge-node01"
        }
        return self.publish_json(MQTT_TOPICS["alerts"], payload, qos=2)

    def publish_health(
        self,
        uptime_s: float,
        total_packets: int,
        arduino_connected: bool,
        database_healthy: bool = True,
        host_ts: Optional[str] = None
    ) -> bool:
        """Publishes heartbeat health telemetry to the health topic."""
        payload = {
            "timestamp": host_ts or datetime.datetime.now().isoformat(),
            "node": "Raspberry Pi 5",
            "uptime_seconds": round(uptime_s, 1),
            "total_telemetry_packets": total_packets,
            "arduino_connected": arduino_connected,
            "database_healthy": database_healthy,
            "mqtt_client_active": True
        }
        return self.publish_json(MQTT_TOPICS["health"], payload, retain=True)

    def publish_telemetry_frame(self, record: Dict[str, Any], prediction: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        Takes a full 10-field telemetry record and distributes it across all
        hierarchical MQTT topics.
        """
        ts_ms = record.get("timestamp_ms", 0)
        host_ts = record.get("host_timestamp") or datetime.datetime.now().isoformat()
        pred = prediction or {"status": "NORMAL", "anomaly_score": 0.0, "is_anomaly": False}

        results = {
            "imu": self.publish_imu(
                record.get("accel_x", 0),
                record.get("accel_y", 0),
                record.get("accel_z", 0),
                ts_ms,
                host_ts
            ),
            "current": self.publish_current(
                record.get("current_a", 0.0),
                ts_ms,
                host_ts
            ),
            "voltage": self.publish_voltage(
                record.get("voltage_v", 0.0),
                ts_ms,
                host_ts
            ),
            "audio": self.publish_audio(
                record.get("sound_rms", 0.0),
                record.get("sound_p2p", 0),
                ts_ms,
                host_ts
            ),
            "status": self.publish_servo_status(
                record.get("servo_angle", 90),
                operational_state="NORMAL" if not pred.get("is_anomaly") else "ANOMALY",
                anomaly_score=pred.get("anomaly_score", 0.0),
                is_anomaly=pred.get("is_anomaly", False),
                host_ts=host_ts
            )
        }

        # If prediction is an anomaly, publish to alerts topic as well
        if pred.get("is_anomaly"):
            results["alert"] = self.publish_alert(
                severity="WARNING",
                channel="ANOMALY_DETECTOR",
                message=f"Multivariate anomaly detected (Score: {pred.get('anomaly_score', 0.0):.2f})",
                metric_value=pred.get("anomaly_score", 0.0),
                threshold=0.65,
                host_ts=host_ts
            )

        return results


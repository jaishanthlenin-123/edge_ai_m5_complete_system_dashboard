"""
Windows-Compatible Vision Adapter for M3 YOLOv8 Inspection Subsystem
Preserves exact model classes:
    0: 'gloves', 1: 'head', 2: 'helmet'
Preserves skin colorimetry bare hand filtering.
Preserves authoritative 3-LED indicator truth table:
    - Helmet Only: Green ON
    - Gloves Only: Yellow ON
    - Both Helmet & Gloves: Red Blinking (Green & Yellow OFF)
    - Neither: All OFF
Supports Webcam, Image Upload, and Recorded Video input modes.
"""

import os
import sys
import time
import threading
import logging
from collections import deque
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from integration.configuration.config import (
    M3_MODEL_PATH,
    M3_SAMPLES_DIR,
    DEFAULT_CAMERA_INDEX,
    CONFIDENCE_THRESHOLD,
    IOU_THRESHOLD,
    INFERENCE_IMAGE_SIZE
)
from integration.data_normalizer.normalizer import normalize_vision_result, create_system_event
from integration.event_manager.event_bus import event_bus

logger = logging.getLogger("m5.vision_adapter")

# UI Visual Colors (BGR)
COLOR_HELMET = (50, 220, 70)       # Vibrant Emerald Green
COLOR_GLOVES = (255, 180, 0)       # Electric Cyan-Blue
COLOR_HEAD_VIOLATION = (40, 40, 240) # Bright Crimson Red
COLOR_BARE_HAND = (30, 110, 255)   # Amber Alert


def classify_hand_crop(crop: np.ndarray, skin_threshold: float = 0.32, laplacian_threshold: float = 750.0) -> Tuple[bool, float, float]:
    """
    Multi-spectrum skin colorimetry (YCrCb + HSV + RGB) combined with
    Laplacian texture variance to identify bare hand violations within glove candidates.
    """
    if crop is None or crop.size == 0:
        return False, 0.0, 0.0

    h, w = crop.shape[:2]
    pad_y = max(1, int(h * 0.1))
    pad_x = max(1, int(w * 0.1))
    inner = crop[pad_y:h - pad_y, pad_x:w - pad_x] if (h > 20 and w > 20) else crop

    # 1. Multi-Space Skin Color Analysis
    ycrcb = cv2.cvtColor(inner, cv2.COLOR_BGR2YCrCb)
    hsv = cv2.cvtColor(inner, cv2.COLOR_BGR2HSV)

    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 175, 127], dtype=np.uint8))
    mask_hsv1 = cv2.inRange(hsv, np.array([0, 25, 40], dtype=np.uint8), np.array([25, 240, 255], dtype=np.uint8))
    mask_hsv2 = cv2.inRange(hsv, np.array([165, 25, 40], dtype=np.uint8), np.array([180, 240, 255], dtype=np.uint8))
    mask_hsv = cv2.bitwise_or(mask_hsv1, mask_hsv2)

    b, g, r = cv2.split(inner)
    mask_rgb = (r > g) & (g > b) & ((r - g) > 8)

    skin_mask = cv2.bitwise_and(mask_ycrcb, mask_hsv)
    skin_mask = cv2.bitwise_and(skin_mask, skin_mask, mask=mask_rgb.astype(np.uint8) * 255)

    skin_pixels = cv2.countNonZero(skin_mask)
    total_pixels = inner.shape[0] * inner.shape[1]
    skin_ratio = skin_pixels / total_pixels if total_pixels > 0 else 0.0

    # 2. Surface Texture / Edge Variance
    gray = cv2.cvtColor(inner, cv2.COLOR_BGR2GRAY)
    texture_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 3. Classification Decision
    if skin_ratio >= 0.50:
        is_bare = True
    elif skin_ratio >= skin_threshold and texture_var < laplacian_threshold:
        is_bare = True
    else:
        is_bare = False

    return is_bare, skin_ratio, texture_var


class VirtualLEDActuator:
    """
    Simulates physical Raspberry Pi 5 3-LED stack on Windows.
    Truth Table:
      - Helmet Only            -> Green ON, Yellow & Red OFF
      - Gloves Only            -> Yellow ON, Green & Red OFF
      - Both Helmet AND Gloves -> RED BLINKING (Green & Yellow OFF)
      - Neither                -> All OFF
    """
    def __init__(self, blink_hz: float = 2.0):
        self.state_green = False
        self.state_yellow = False
        self.state_red = False
        self.is_blinking = False
        self.active_condition = "OFF"
        self.blink_interval = 1.0 / (2.0 * blink_hz)
        self._stop_event = threading.Event()
        self._blink_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def update(self, has_helmet: bool, has_gloves: bool) -> Dict[str, Any]:
        with self._lock:
            h = bool(has_helmet)
            g = bool(has_gloves)

            if h and g:
                self.state_green = False
                self.state_yellow = False
                self.active_condition = "RED_BLINKING"
                if not self.is_blinking:
                    self.is_blinking = True
                    self._stop_event.clear()
                    self._blink_thread = threading.Thread(target=self._blink_worker, daemon=True)
                    self._blink_thread.start()
            elif h and not g:
                self._stop_blink()
                self.state_green = True
                self.state_yellow = False
                self.active_condition = "GREEN"
            elif g and not h:
                self._stop_blink()
                self.state_green = False
                self.state_yellow = True
                self.active_condition = "YELLOW"
            else:
                self._stop_blink()
                self.state_green = False
                self.state_yellow = False
                self.active_condition = "OFF"

            return self.get_state()

    def _stop_blink(self):
        if self.is_blinking:
            self.is_blinking = False
            self._stop_event.set()
        self.state_red = False

    def _blink_worker(self):
        while not self._stop_event.is_set() and self.is_blinking:
            self.state_red = not self.state_red
            self._stop_event.wait(self.blink_interval)
        self.state_red = False

    def get_state(self) -> Dict[str, Any]:
        if self.active_condition == "RED_BLINKING":
            label = "BOTH DETECTED — RED LED BLINKING"
        elif self.active_condition == "GREEN":
            label = "GREEN LED ACTIVE (HELMET ONLY)"
        elif self.active_condition == "YELLOW":
            label = "YELLOW LED ACTIVE (GLOVES ONLY)"
        else:
            label = "ALL LEDS OFF (NO PPE DETECTED)"

        return {
            "green": {
                "active": self.state_green,
                "pin_bcm": 27,
                "pin_physical": 13,
                "label": "Helmet Indicator"
            },
            "yellow": {
                "active": self.state_yellow,
                "pin_bcm": 17,
                "pin_physical": 11,
                "label": "Gloves Indicator"
            },
            "red": {
                "active": self.state_red or self.is_blinking,
                "blinking": self.is_blinking,
                "pin_bcm": 22,
                "pin_physical": 15,
                "label": "Combined Both Indicator (Blinks)"
            },
            "active_condition": self.active_condition,
            "active_label": label,
            "mode": "Windows Emulated Hardware Actuator"
        }


class WindowsVisionAdapter:
    """
    High-performance Windows interface for M3 YOLO vision inspection.
    """
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = Path(model_path or M3_MODEL_PATH)
        self.lock = threading.RLock()
        self.actuator = VirtualLEDActuator()

        # Engine parameters
        self.source_mode = "webcam"  # 'webcam', 'image_upload', 'recorded_video'
        self.camera_index = DEFAULT_CAMERA_INDEX
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        self.iou_threshold = IOU_THRESHOLD
        self.inference_size = INFERENCE_IMAGE_SIZE

        # Threads and state
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.uploaded_image: Optional[np.ndarray] = None
        self.video_path: Optional[Path] = None

        # Frame buffers
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_jpeg_bytes: Optional[bytes] = None
        self.latest_result: Dict[str, Any] = {}

        # Performance telemetry
        self.fps = 0.0
        self.fps_window = deque(maxlen=20)
        self.latency_ms = 0.0
        self.total_inferences = 0

        # Load YOLO model
        logger.info(f"Loading YOLOv8 model from {self.model_path}...")
        self.model = YOLO(str(self.model_path))
        # Warmup
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        self.model.predict(dummy, imgsz=320, device="cpu", verbose=False)
        logger.info("YOLOv8 vision engine initialized and warmed up.")

    def start(self):
        """Starts background continuous capture and inspection worker."""
        with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            event_bus.update_module_status("vision", "RUNNING")
            logger.info("Vision adapter worker thread started.")

    def stop(self):
        """Stops background inspection worker and releases camera resources."""
        with self.lock:
            self.is_running = False
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
            event_bus.update_module_status("vision", "STOPPED")
            logger.info("Vision adapter stopped.")

    def set_source_mode(self, mode: str, file_path: Optional[str] = None):
        """Switches between 'webcam', 'image_upload', and 'recorded_video'."""
        with self.lock:
            mode = mode.lower()
            if mode not in ("webcam", "image_upload", "recorded_video"):
                raise ValueError(f"Unknown source mode: {mode}")

            self.source_mode = mode

            # Reset hardware capture
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

            if mode == "image_upload" and file_path:
                img = cv2.imread(file_path)
                if img is not None:
                    self.uploaded_image = img
            elif mode == "recorded_video" and file_path:
                self.video_path = Path(file_path)
                self.cap = cv2.VideoCapture(str(self.video_path))
            elif mode == "webcam":
                self._open_webcam()

            logger.info(f"Vision source mode set to: {self.source_mode}")

    def _open_webcam(self) -> bool:
        """Attempts to open Windows DirectShow webcam or standard OpenCV camera."""
        try:
            # Try DirectShow first on Windows for faster startup
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_index)

            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                logger.info(f"Webcam {self.camera_index} opened successfully.")
                return True
            else:
                logger.warning(f"Could not open webcam index {self.camera_index}. Falling back to sample image.")
                self.cap = None
                return False
        except Exception as e:
            logger.error(f"Error opening webcam: {e}")
            self.cap = None
            return False

    def inspect_single_image(self, image: np.ndarray, sample_id: Optional[str] = None) -> Tuple[Dict[str, Any], np.ndarray]:
        """
        Runs single-shot YOLO inference, skin analysis, compliance decision,
        and actuator emulation on an image.
        """
        t0 = time.perf_counter()
        h, w = image.shape[:2]

        # 1. YOLO Inference
        res = self.model.predict(
            image,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.inference_size,
            device="cpu",
            verbose=False
        )[0]

        counts = {"helmet": 0, "gloves": 0, "head": 0, "bare_hand": 0}
        detections = []
        max_helmet_conf = 0.0
        max_gloves_conf = 0.0

        for box in res.boxes:
            cls_id = int(box.cls)
            cls_name = self.model.names.get(cls_id, f"class_{cls_id}")
            conf = float(box.conf)
            xyxy = [int(v) for v in box.xyxy[0].tolist()]

            # Skin colorimetry check on glove candidates
            if cls_name == "gloves":
                x1, y1 = max(0, xyxy[0]), max(0, xyxy[1])
                x2, y2 = min(w, xyxy[2]), min(h, xyxy[3])
                crop = image[y1:y2, x1:x2]
                is_bare, skin_ratio, _ = classify_hand_crop(crop)
                if is_bare:
                    cls_name = "bare_hand"

            counts[cls_name] = counts.get(cls_name, 0) + 1

            if cls_name == "helmet":
                max_helmet_conf = max(max_helmet_conf, conf)
            elif cls_name == "gloves":
                max_gloves_conf = max(max_gloves_conf, conf)

            detections.append({
                "class": cls_name,
                "confidence": round(conf, 4),
                "bbox": xyxy
            })

        # 2. Decision Policy:
        # PASS: Helmet >= 1 AND Gloves >= 1 AND head == 0 AND bare_hand == 0
        # FAIL: Missing helmet or missing gloves or both missing or bare head/hand detected
        has_helmet = (counts.get("helmet", 0) > 0)
        has_gloves = (counts.get("gloves", 0) > 0)
        has_head = (counts.get("head", 0) > 0)
        has_bare_hand = (counts.get("bare_hand", 0) > 0)

        if has_helmet and has_gloves and not has_head and not has_bare_hand:
            status = "PASS"
            reason = "COMPLIANT: Hardhat and Safety Gloves Verified"
        elif has_head or has_bare_hand:
            violations = []
            if has_head: violations.append("Missing Helmet (Bare Head Detected)")
            if has_bare_hand: violations.append("Missing Gloves (Bare Hand Detected)")
            status = "FAIL"
            reason = f"PPE VIOLATION: {', '.join(violations)}"
        elif has_helmet and not has_gloves:
            status = "FAIL"
            reason = "PPE VIOLATION: Safety Gloves Missing"
        elif has_gloves and not has_helmet:
            status = "FAIL"
            reason = "PPE VIOLATION: Safety Helmet Missing"
        else:
            status = "FAIL"
            reason = "PPE VIOLATION: Both Helmet and Gloves Missing"

        # 3. Update Actuator
        led_state = self.actuator.update(has_helmet, has_gloves)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        # 4. Render Annotations
        annotated = self._render_hud(image.copy(), detections, status, reason, latency_ms, led_state)

        # 5. Build Normalized Result
        normalized = normalize_vision_result(
            sample_id=sample_id,
            helmet_detected=has_helmet,
            gloves_detected=has_gloves,
            head_detected=has_head,
            bare_hand_detected=has_bare_hand,
            helmet_confidence=max_helmet_conf,
            gloves_confidence=max_gloves_conf,
            inspection_status=status,
            inspection_reason=reason,
            detections=detections,
            source_mode=self.source_mode,
            processing_ms=latency_ms,
            led_state=led_state
        )

        return normalized, annotated

    def _render_hud(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        status: str,
        reason: str,
        latency_ms: float,
        led_state: Dict[str, Any]
    ) -> np.ndarray:
        """Renders high-tech industrial HUD banner, bounding boxes, and virtual LED indicators."""
        h, w = frame.shape[:2]

        # Draw bounding boxes
        for det in detections:
            cls_name = det["class"]
            conf = det["confidence"]
            x1, y1, x2, y2 = det["bbox"]

            if cls_name == "helmet":
                color = COLOR_HELMET
                badge = f"HELMET {int(conf * 100)}%"
            elif cls_name == "gloves":
                color = COLOR_GLOVES
                badge = f"GLOVES {int(conf * 100)}%"
            elif cls_name == "head":
                color = COLOR_HEAD_VIOLATION
                badge = f"! NO HELMET {int(conf * 100)}%"
            else:  # bare_hand
                color = COLOR_BARE_HAND
                badge = f"! BARE HAND {int(conf * 100)}%"

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Badge background and label
            (tw, th), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - 20)), (x1 + tw + 10, max(20, y1)), color, -1)
            text_color = (0, 0, 0) if cls_name in ("helmet", "gloves") else (255, 255, 255)
            cv2.putText(frame, badge, (x1 + 5, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, text_color, 1, cv2.LINE_AA)

        # Top Banner Overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 40), (15, 20, 28), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Status badge color
        if status == "PASS":
            status_color = (60, 220, 60)
            status_text = "[ PASS ] COMPLIANT"
        elif status == "FAIL":
            status_color = (40, 40, 240)
            status_text = "[ FAIL ] VIOLATION"
        else:
            status_color = (180, 180, 180)
            status_text = "[ IDLE ] CLEAR ZONE"

        cv2.putText(frame, status_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"Latency: {latency_ms:.1f}ms | Source: {self.source_mode.upper()}", (w - 320, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 210, 220), 1, cv2.LINE_AA)

        # Bottom Virtual Stack LEDs
        cv2.rectangle(frame, (0, h - 30), (w, h), (15, 20, 28), -1)
        # LED circles: Green (Pin 13), Yellow (Pin 11), Red (Pin 15)
        # Green
        g_on = led_state.get("green", {}).get("active", False)
        g_col = (0, 230, 0) if g_on else (20, 60, 20)
        cv2.circle(frame, (25, h - 15), 8, g_col, -1)
        cv2.putText(frame, "HELMET (G)", (40, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1)

        # Yellow
        y_on = led_state.get("yellow", {}).get("active", False)
        y_col = (0, 215, 255) if y_on else (25, 55, 65)
        cv2.circle(frame, (145, h - 15), 8, y_col, -1)
        cv2.putText(frame, "GLOVES (Y)", (160, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1)

        # Red
        r_on = led_state.get("red", {}).get("active", False)
        r_col = (40, 40, 255) if r_on else (30, 20, 60)
        cv2.circle(frame, (265, h - 15), 8, r_col, -1)
        r_txt = "BOTH (R BLINK)" if led_state.get("red", {}).get("blinking", False) else "BOTH (R)"
        cv2.putText(frame, r_txt, (280, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1)

        # Actuator Active Condition Text
        cond_label = led_state.get("active_label", "ALL LEDS OFF")
        cv2.putText(frame, f"Actuator: {cond_label}", (w - 380, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 200, 255), 1)

        return frame

    def _worker_loop(self):
        """Continuous background inference loop."""
        logger.info("Entering vision worker loop.")
        fps_t0 = time.perf_counter()

        # Fallback test image if camera fails
        default_sample = None
        for candidate in ["compliant.jpg", "tc03_both.jpg", "tc01_helmet_only.jpg"]:
            path = M3_SAMPLES_DIR / candidate
            if path.exists():
                default_sample = cv2.imread(str(path))
                if default_sample is not None:
                    break

        if default_sample is None:
            default_sample = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(default_sample, "M5 Vision Standby", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        while self.is_running:
            try:
                frame = None
                with self.lock:
                    if self.source_mode == "webcam":
                        if self.cap is None or not self.cap.isOpened():
                            self._open_webcam()

                        if self.cap is not None and self.cap.isOpened():
                            ret, raw = self.cap.read()
                            if ret and raw is not None:
                                frame = raw
                        if frame is None:
                            frame = default_sample.copy()

                    elif self.source_mode == "image_upload":
                        if self.uploaded_image is not None:
                            frame = self.uploaded_image.copy()
                        else:
                            frame = default_sample.copy()

                    elif self.source_mode == "recorded_video":
                        if self.cap is not None and self.cap.isOpened():
                            ret, raw = self.cap.read()
                            if ret and raw is not None:
                                frame = raw
                            else:
                                # Loop video
                                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                ret, raw = self.cap.read()
                                if ret: frame = raw
                        if frame is None:
                            frame = default_sample.copy()

                if frame is not None:
                    norm_result, annotated = self.inspect_single_image(frame)

                    with self.lock:
                        self.latest_raw_frame = frame
                        self.latest_annotated_frame = annotated
                        self.latest_result = norm_result
                        self.total_inferences += 1

                        # JPEG encoding for MJPEG feed
                        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        self.latest_jpeg_bytes = buf.tobytes()

                        # FPS calc
                        now = time.perf_counter()
                        dt = now - fps_t0
                        fps_t0 = now
                        if dt > 0:
                            self.fps_window.append(1.0 / dt)
                            self.fps = round(sum(self.fps_window) / len(self.fps_window), 1)

                    # Publish inspection event to bus
                    event_bus.publish({
                        "event_type": "inspection_result",
                        "module": "vision",
                        "data": norm_result,
                        "timestamp": norm_result["timestamp"],
                        "severity": "WARNING" if norm_result["inspection_status"] == "FAIL" else "INFO"
                    })

                time.sleep(0.04)  # ~25 FPS pacing

            except Exception as e:
                logger.error(f"Error in vision worker loop: {e}")
                time.sleep(0.5)

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg_bytes

    def get_latest_result(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.latest_result)


# Global Singleton Vision Adapter
vision_adapter = WindowsVisionAdapter()

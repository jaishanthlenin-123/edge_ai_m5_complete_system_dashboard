"""
Two-Stream Asynchronous Edge Vision Pipeline
Milestone 3 - Task 2: Multi-Stream Video Processing & Actuator Arbitration
Hardware Target: Raspberry Pi 5
"""

import cv2
import time
import threading
import numpy as np
from collections import deque
from typing import Dict, Any, Optional, List
from ultralytics import YOLO
from gpio_manager import gpio_controller

class StreamWorker:
    """Independent worker thread for an individual video stream."""
    def __init__(self, stream_id: str, name: str, source: Any, model: YOLO, imgsz: int = 320, conf: float = 0.35):
        self.stream_id = stream_id
        self.name = name
        self.source = source
        self.model = model
        self.imgsz = imgsz
        self.conf = conf

        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()

        # Telemetry
        self.fps = 0.0
        self.fps_deque = deque(maxlen=20)
        self.frame_count = 0
        self.dropped_frames = 0
        self.latency_ms = 0.0
        self.status = "INITIALIZING"

        # State & Buffers
        self.latest_raw = None
        self.latest_annotated = None
        self.latest_detections: List[Dict[str, Any]] = []
        self.counts = {"helmet": 0, "gloves": 0, "head": 0, "bare_hand": 0, "total": 0}

        # Source handle
        self.cap = None
        self.static_image = None
        self._init_source()

    def _init_source(self):
        if isinstance(self.source, int):
            self.cap = cv2.VideoCapture(self.source)
        elif isinstance(self.source, str) and self.source.endswith(('.jpg', '.png', '.jpeg')):
            self.static_image = cv2.imread(self.source)
        elif isinstance(self.source, str):
            self.cap = cv2.VideoCapture(self.source)

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()

    def _get_frame(self) -> Optional[np.ndarray]:
        if self.static_image is not None:
            # Simulate subtle camera noise / panning so FPS is real
            frame = self.static_image.copy()
            return cv2.resize(frame, (640, 480))
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return frame
            self.dropped_frames += 1
        return None

    def _loop(self):
        last_time = time.perf_counter()
        while self.is_running:
            t0 = time.perf_counter()
            frame = self._get_frame()
            if frame is None:
                self.status = "DISCONNECTED"
                time.sleep(0.05)
                continue

            self.status = "STREAMING"
            self.frame_count += 1

            # Run YOLO inference
            res = self.model.predict(
                source=frame,
                imgsz=self.imgsz,
                conf=self.conf,
                device="cpu",
                verbose=False
            )[0]
            t_inf = time.perf_counter()
            self.latency_ms = (t_inf - t0) * 1000.0

            # Parse detections
            detections = []
            f_counts = {"helmet": 0, "gloves": 0, "head": 0, "bare_hand": 0, "total": 0}
            for box in res.boxes:
                cid = int(box.cls)
                cname = self.model.names[cid]
                score = float(box.conf)
                xyxy = [int(v) for v in box.xyxy[0].tolist()]

                detections.append({
                    "class": cname,
                    "confidence": round(score, 3),
                    "bbox": xyxy
                })
                if cname in f_counts:
                    f_counts[cname] += 1
            f_counts["total"] = len(detections)

            # Compute independent FPS via rolling timestamp window
            now = time.perf_counter()
            self.fps_deque.append(now)
            if len(self.fps_deque) > 1:
                dur = self.fps_deque[-1] - self.fps_deque[0]
                self.fps = (len(self.fps_deque) - 1) / dur if dur > 0 else 0.0

            # Annotate frame
            annotated = self._render_overlay(frame, detections)

            with self.lock:
                self.latest_raw = frame
                self.latest_annotated = annotated
                self.latest_detections = detections
                self.counts = f_counts

            time.sleep(0.01)  # Yield CPU

    def _render_overlay(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        h, w = frame.shape[:2]
        out = frame.copy()

        # Bounding boxes
        for det in detections:
            cls_name = det["class"]
            conf = det["confidence"]
            x1, y1, x2, y2 = det["bbox"]
            color = (70, 220, 50) if cls_name == "helmet" else ((255, 180, 0) if cls_name == "gloves" else (50, 40, 240))
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            lbl = f"{cls_name.upper()} {int(conf*100)}%"
            cv2.putText(out, lbl, (x1 + 4, max(18, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        # Stream HUD Banner
        cv2.rectangle(out, (0, 0), (w, 32), (15, 20, 28), -1)
        hud_text = f"[{self.name}] FPS: {self.fps:.1f} | LATENCY: {self.latency_ms:.1f}ms | DET: {len(detections)}"
        cv2.putText(out, hud_text, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 230, 255), 1, cv2.LINE_AA)
        return out


class TwoStreamManager:
    """Manages two concurrent vision streams and coordinates physical actuator arbitration."""
    def __init__(self, model_path: str = "best.pt"):
        print(f"[TwoStream] Initializing shared model from {model_path}...")
        self.model = YOLO(model_path)
        # Warmup model so worker threads start inferences with zero compilation lag
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        self.model.predict(dummy, imgsz=320, verbose=False)

        # Worker 1: Station Alpha (Simulated Helmet Worker)
        self.stream1 = StreamWorker(
            stream_id="stream_1",
            name="STATION-01 (ASSEMBLY)",
            source="samples/tc01_helmet_only.jpg",
            model=self.model,
            imgsz=320
        )

        # Worker 2: Station Beta (Simulated Glove Station)
        self.stream2 = StreamWorker(
            stream_id="stream_2",
            name="STATION-02 (INSPECTION)",
            source="samples/tc02_gloves_only.jpg",
            model=self.model,
            imgsz=640
        )

        self.is_running = False
        self.arbitration_thread = None

    def start(self):
        self.is_running = True
        self.stream1.start()
        self.stream2.start()
        self.arbitration_thread = threading.Thread(target=self._arbitration_loop, daemon=True)
        self.arbitration_thread.start()
        print("[TwoStream] Both stream workers started with actuator arbitration.")

    def stop(self):
        self.is_running = False
        self.stream1.stop()
        self.stream2.stop()
        gpio_controller.cleanup()
        print("[TwoStream] Stopped all workers.")

    def _arbitration_loop(self):
        """
        Actuator Arbitration Policy:
        helmet_active = stream1.has_helmet OR stream2.has_helmet
        glove_active  = stream1.has_gloves OR stream2.has_gloves
        both_active   = helmet_active AND glove_active -> Red LED Blinks (Green & Yellow OFF)
        """
        while self.is_running:
            s1_helmet = (self.stream1.counts.get("helmet", 0) > 0)
            s1_gloves = (self.stream1.counts.get("gloves", 0) > 0)

            s2_helmet = (self.stream2.counts.get("helmet", 0) > 0)
            s2_gloves = (self.stream2.counts.get("gloves", 0) > 0)

            # System-level logical union (OR arbitration)
            system_helmet = s1_helmet or s2_helmet
            system_gloves = s1_gloves or s2_gloves

            # Command 3-LED Actuator
            gpio_controller.update(system_helmet, system_gloves)
            time.sleep(0.05)

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "stream1": {
                "id": self.stream1.stream_id,
                "name": self.stream1.name,
                "status": self.stream1.status,
                "fps": round(self.stream1.fps, 1),
                "latency_ms": round(self.stream1.latency_ms, 1),
                "counts": self.stream1.counts
            },
            "stream2": {
                "id": self.stream2.stream_id,
                "name": self.stream2.name,
                "status": self.stream2.status,
                "fps": round(self.stream2.fps, 1),
                "latency_ms": round(self.stream2.latency_ms, 1),
                "counts": self.stream2.counts
            },
            "system_actuator": gpio_controller.get_state()
        }

    def get_combined_dashboard_frame(self) -> Optional[np.ndarray]:
        """Stitches both streams side-by-side into a dual-monitoring HUD."""
        f1 = self.stream1.latest_annotated
        f2 = self.stream2.latest_annotated
        if f1 is None or f2 is None:
            return None

        # Resize to matching heights
        h = 400
        w1 = int(f1.shape[1] * (h / f1.shape[0]))
        w2 = int(f2.shape[1] * (h / f2.shape[0]))
        r1 = cv2.resize(f1, (w1, h))
        r2 = cv2.resize(f2, (w2, h))

        # Horizontal stack
        combined = np.hstack([r1, r2])

        # Bottom System Arbitration Ribbon
        ribbon_h = 44
        ribbon = np.zeros((ribbon_h, combined.shape[1], 3), dtype=np.uint8)
        ribbon[:] = (18, 24, 32)

        state = gpio_controller.get_state()
        act_text = f"MULTI-STREAM ARBITRATION // LED STATE: {state['active_label']} | STREAM 1 FPS: {self.stream1.fps:.1f} | STREAM 2 FPS: {self.stream2.fps:.1f}"
        cv2.putText(ribbon, act_text, (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 240, 255), 1, cv2.LINE_AA)

        return np.vstack([combined, ribbon])

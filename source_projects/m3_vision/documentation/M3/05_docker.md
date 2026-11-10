# Containerized Deployment with Docker
**Milestone:** M3 – Decide and Act  
**Document ID:** `M3-DOC-05`  
**System Target:** Edge Container Runtime / Raspberry Pi 5 / Linux / Windows  
**Author:** Lenin (`jaishanthlenin-123`)  

---

## 1. Overview & Objectives

Task 5 implements container-based deployment for the Helmet and Glove Detection System. Containerization ensures reproducible execution across both host development environments (Windows 11 / x86_64) and edge production targets (Raspberry Pi 5 / aarch64), isolating dependencies, OpenCV system packages, and PyTorch runtimes.

---

## 2. Docker Architecture & File Specifications

### 2.1 `Dockerfile`
The Docker image is built on `python:3.11-slim-bookworm` with system dependencies for OpenCV and video capture:

```dockerfile
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY best.pt .
COPY engine.py .
COPY gpio_manager.py .
COPY debounce_filter.py .
COPY pipeline_two_stream.py .
COPY server.py .
COPY samples/ ./samples/
COPY static/ ./static/

RUN mkdir -p /app/snapshots
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/config || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 `.dockerignore`
Excludes large git histories, virtual environments, unit test outputs, and evidence directories to minimize image build size and layer cache invalidation:
```text
.git
.github
__pycache__
*.pyc
tests/
evidence/
docs/
snapshots/
scratch/
```

---

## 3. Step-by-Step Deployment Instructions

### 3.1 Build the Docker Image
```bash
docker build -t edge-ai-ppe-m3:latest .
```

### 3.2 Run Container in Simulation Mode (Host Development)
When running on development machines without physical Raspberry Pi 5 GPIO pins or cameras:
```bash
docker run -d \
  --name aegis_edge_m3 \
  -p 8000:8000 \
  --restart unless-stopped \
  edge-ai-ppe-m3:latest
```
The application automatically starts in **Simulated GPIO Mode**, executing full YOLOv8 inferences on factory station images and emulating the Three-LED decision logic.

### 3.3 Run Container on Raspberry Pi 5 with Hardware Camera & GPIO
To mount physical V4L2 cameras and access the Raspberry Pi 5 RP1 GPIO controller:
```bash
docker run -d \
  --name aegis_edge_m3_hardware \
  -p 8000:8000 \
  --device /dev/video0:/dev/video0 \
  --device /dev/gpiomem:/dev/gpiomem \
  --privileged \
  --restart always \
  edge-ai-ppe-m3:latest
```

---

## 4. Verification & Testing Procedure

1. **Verify Container Running:**
   ```bash
   docker ps -f name=aegis_edge_m3
   ```
2. **Verify Model Loading & Logs:**
   ```bash
   docker logs --tail 30 aegis_edge_m3
   ```
   *Expected Output:*
   ```text
   [Server] Starting Edge Vision Engine...
   [Engine] Loading YOLO model from best.pt...
   [Engine] Warmup complete.
   [GPIO] Running in Virtual/Simulated Mode for live dashboard.
   INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```
3. **Verify Dashboard Accessibility:**
   Open browser at `http://localhost:8000` or curl:
   ```bash
   curl -I http://localhost:8000/
   ```
4. **Verify Healthcheck:**
   ```bash
   docker inspect --format='{{json .State.Health.Status}}' aegis_edge_m3
   # Output: "healthy"
   ```
5. **Clean Container Restart Test:**
   ```bash
   docker restart aegis_edge_m3
   docker logs --tail 10 aegis_edge_m3
   ```


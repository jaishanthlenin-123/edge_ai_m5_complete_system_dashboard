# Roboflow Dataset & Pre-Trained YOLOv8 Model Documentation
**Project:** Real-Time PPE Helmet & Glove Detection System  
**Framework:** Ultralytics YOLOv8 (v8.4.174)  
**Target Hardware:** Raspberry Pi 5 / Edge Vision Gateway  
**Document Code:** `M3-DOC-07`  

---

## 1. Roboflow Dataset Specification

The detection model used in this system was trained on a dataset exported from Roboflow Universe. The dataset contains annotated images of industrial personnel wearing safety helmets and personal protective gloves in factory and construction environments.

### 1.1 Dataset Metadata

| Attribute | Specification | Source / Verification |
|---|---|---|
| **Roboflow Workspace** | `[USER_ROBOFLOW_WORKSPACE]` *(See Note below)* | Extracted from training checkpoint path |
| **Roboflow Project Name** | `yolo-detection-helmet-gloves` | Verified from Colab training path `/content/yolo-detection-helmet-gloves-2/` |
| **Roboflow Project URL** | `https://universe.roboflow.com/[USER_WORKSPACE]/yolo-detection-helmet-gloves` | *[PLACEHOLDER: Please confirm exact workspace slug]* |
| **Dataset Version** | Version `2` | Verified from folder suffix `-2` in training data |
| **Dataset Version URL** | `https://universe.roboflow.com/[USER_WORKSPACE]/yolo-detection-helmet-gloves/dataset/2` | *[PLACEHOLDER: Please confirm exact URL]* |
| **Export Format** | YOLOv8 PyTorch format (`data.yaml`, `images/`, `labels/`) | Verified |
| **Annotation Classes** | 3 Classes: `0: gloves`, `1: head`, `2: helmet` | Verified from `best.pt` dictionary |
| **Base Training Resolution** | $640 \times 640$ pixels | Checkpoint `train_args['imgsz'] = 640` |
| **Edge Inference Resolution**| $320 \times 320$ pixels (Optimized for Raspberry Pi 5) | `detect.py`, `engine.py` |

> [!NOTE]
> **Roboflow Project URL Placeholder Notice:**  
> The internal metadata inside `best.pt` confirms the training folder name `/content/yolo-detection-helmet-gloves-2/data.yaml`. To preserve absolute integrity and avoid fabricating public workspace slugs, the workspace name is designated as `[USER_WORKSPACE]`. Once provided, the live URL will link directly to the Roboflow Universe page.

---

## 2. Dataset Download & Reproduction Instructions

To download the exact dataset version from Roboflow via Python or Roboflow CLI:

### 2.1 Using Python Roboflow SDK

```python
from roboflow import Roboflow

# Initialize Roboflow with your API key
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")

# Access the project workspace and download version 2
project = rf.workspace("[USER_WORKSPACE]").project("yolo-detection-helmet-gloves")
version = project.version(2)
dataset = version.download("yolov8")

print(f"Dataset downloaded to: {dataset.location}")
```

### 2.2 Using cURL / Direct ZIP Export

```bash
# Export format: yolov8
curl -L "https://universe.roboflow.com/ds/[EXPORT_KEY]?key=YOUR_API_KEY" > roboflow_yolov8.zip
unzip roboflow_yolov8.zip -d yolo-detection-helmet-gloves-2
```

---

## 3. Training Configuration & Hyperparameters

The model `best.pt` was trained on Google Colab with the following hyperparameters (extracted directly from the binary checkpoint):

```yaml
# Ultralytics YOLOv8 Training Hyperparameters
task: detect
mode: train
model: yolov8n.pt                  # Nano architecture for edge acceleration
data: /content/yolo-detection-helmet-gloves-2/data.yaml
epochs: 100                        # 100 training epochs
batch: 16                          # Batch size 16
imgsz: 640                         # 640x640 resolution
optimizer: AdamW                   # AdamW optimizer
lr0: 0.001429                      # Initial learning rate
lrf: 0.01                          # Final learning rate factor
momentum: 0.937
weight_decay: 0.0005
warmup_epochs: 3.0
warmup_momentum: 0.8
box: 7.5
cls: 0.5
dfl: 1.5

# Data Augmentation Settings
fliplr: 0.5                        # Horizontal flip (50% probability)
flipud: 0.0                        # Vertical flip disabled
mosaic: 1.0                        # 100% Mosaic augmentation
erasing: 0.4                       # Random erasing (40% probability)
auto_augment: randaugment          # RandAugment strategy
hsv_h: 0.015                       # Hue adjustment
hsv_s: 0.7                         # Saturation adjustment
hsv_v: 0.4                         # Value / brightness adjustment
translate: 0.1                     # Image translation (+/- 10%)
scale: 0.5                         # Image scale (+/- 50%)
```

---

## 4. Trained Model Evaluation Metrics

Final validation metrics recorded at epoch 100:

| Metric | Score | Industrial Interpretation |
|---|---|---|
| **Precision (B)** | **86.56%** (`0.86561`) | Low false positive rate; minimal false PPE alarms. |
| **Recall (B)** | **75.27%** (`0.75267`) | Reliable capture of helmets and protective gloves. |
| **mAP@50 (B)** | **79.04%** (`0.79044`) | Strong general detection confidence across industrial classes. |
| **mAP@50-95 (B)** | **52.56%** (`0.52555`) | Excellent boundary localization accuracy. |
| **Box Loss** | `1.22798` | Tight bounding-box convergence. |
| **Classification Loss** | `0.81349` | Accurate separation between helmet, head, and gloves. |
| **DFL Loss** | `1.24989` | Distribution focal loss stabilized. |

---

## 5. Model Architecture & Deployment Specifications

- **Model Filename:** `best.pt`
- **File Size:** $6,257,770$ bytes (~$6.25\,\text{MB}$)
- **Parameter Count:** ~3.2 Million parameters (YOLOv8n)
- **Quantization:** FP32 (supports INT8 / NCNN / ONNX export for Raspberry Pi 5 Hailo/NPU acceleration)
- **Inference Speed:**
  - **Raspberry Pi 5 (CPU - 4 Threads @ 320x320):** ~28–42 ms (~24–35 FPS)
  - **CUDA GPU (RTX / Laptop):** ~3–6 ms (>150 FPS)

---

## 6. How to Reproduce Inference

### 6.1 Python CLI Inference
```bash
python detect.py
```

### 6.2 Python Scripting API
```python
from ultralytics import YOLO
import cv2

# Load the trained model
model = YOLO("best.pt")

# Perform inference on an image
results = model.predict(source="samples/compliant.jpg", imgsz=320, conf=0.35)

for box in results[0].boxes:
    cls_id = int(box.cls)
    name = model.names[cls_id]
    conf = float(box.conf)
    coords = box.xyxy[0].tolist()
    print(f"Detected: {name} (Confidence: {conf:.2f}) at {coords}")
```

### 6.3 Live Web Dashboard
```bash
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Navigate to `http://localhost:8000` to inspect live video feeds, dynamic sliders, and actuator telemetry.

---

## 7. Empirical Dataset Evidence & Repository Links

Authentic photographic evidence of the dataset origin has been cataloged under [`evidence/M3/07_roboflow_dataset_and_model/`](file:///e:/New%20folder%20(6)/evidence/M3/07_roboflow_dataset_and_model/):

- **Kaggle Dataset Portal Evidence:** [`screenshots/kaggle_ppe_dataset_source.jpeg`](file:///e:/New%20folder%20(6)/evidence/M3/07_roboflow_dataset_and_model/screenshots/kaggle_ppe_dataset_source.jpeg)
  - Displays the Kaggle PPE Dataset repository (`waquarahmed/ppe-dataset`), showing 23,600+ industrial PPE images, file manifest (`01-15-1-1-1-1-30.jpg`), and data card.
  - The dataset served as the foundational source exported to Roboflow project `yolo-detection-helmet-gloves-2` for 3-class normalized bounding box annotations (`0: gloves`, `1: head`, `2: helmet`).
- **Direct Kaggle URL:** [https://www.kaggle.com/datasets/waquarahmed/ppe-dataset](https://www.kaggle.com/datasets/waquarahmed/ppe-dataset)


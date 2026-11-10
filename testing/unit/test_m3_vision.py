"""
Unit Test Suite for M3 YOLOv8 Vision & Actuator Subsystem
Verifies:
  - Model weight loading
  - Class mapping integrity ({0: 'gloves', 1: 'head', 2: 'helmet'})
  - Bare hand skin colorimetry filtering
  - Authoritative 3-LED actuator truth table
  - Inspection decision logic
"""

import sys
import numpy as np
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integration.configuration.config import M3_MODEL_PATH, CLASS_NAMES
from integration.vision_adapter.adapter import WindowsVisionAdapter, VirtualLEDActuator, classify_hand_crop


def test_model_loading_and_classes():
    """Verify YOLOv8 best.pt exists, loads, and preserves exact class mapping."""
    adapter = WindowsVisionAdapter(M3_MODEL_PATH)
    assert adapter.model is not None

    names = adapter.model.names
    assert names[0] == "gloves", f"Class 0 should be 'gloves', got {names.get(0)}"
    assert names[1] == "head", f"Class 1 should be 'head' (violation), got {names.get(1)}"
    assert names[2] == "helmet", f"Class 2 should be 'helmet', got {names.get(2)}"


def test_skin_colorimetry_filter():
    """Verify bare hand detector discriminates exposed skin from covered gloves."""
    # Synthetic skin-tone crop (RGB high in Red, moderate Green, low Blue)
    skin_crop = np.zeros((60, 60, 3), dtype=np.uint8)
    skin_crop[:, :] = (130, 160, 220)  # BGR order: B=130, G=160, R=220

    is_bare, ratio, var = classify_hand_crop(skin_crop)
    assert is_bare is True, f"Expected skin crop to be classified as bare hand, got {is_bare}"
    assert ratio > 0.40

    # Synthetic industrial glove crop (High blue/cyan, low red)
    glove_crop = np.zeros((60, 60, 3), dtype=np.uint8)
    glove_crop[:, :] = (220, 180, 20)  # BGR: B=220, G=180, R=20 (Electric Cyan)

    is_bare_glove, ratio_glove, _ = classify_hand_crop(glove_crop)
    assert is_bare_glove is False, f"Expected cyan glove to be classified as protected, got {is_bare_glove}"


def test_authoritative_led_truth_table():
    """
    Verifies corrected M3 Actuator Truth Table:
    1. Helmet ONLY            -> Green ON, Yellow OFF, Red OFF
    2. Gloves ONLY            -> Yellow ON, Green OFF, Red OFF
    3. Both Helmet AND Gloves -> RED BLINKING (Green & Yellow OFF)
    4. Neither                -> All LEDs OFF
    """
    actuator = VirtualLEDActuator()

    # Case 1: Helmet Only
    st1 = actuator.update(has_helmet=True, has_gloves=False)
    assert st1["green"]["active"] is True
    assert st1["yellow"]["active"] is False
    assert st1["red"]["blinking"] is False
    assert st1["active_condition"] == "GREEN"

    # Case 2: Gloves Only
    st2 = actuator.update(has_helmet=False, has_gloves=True)
    assert st2["green"]["active"] is False
    assert st2["yellow"]["active"] is True
    assert st2["red"]["blinking"] is False
    assert st2["active_condition"] == "YELLOW"

    # Case 3: Both Helmet AND Gloves -> RED BLINKING
    st3 = actuator.update(has_helmet=True, has_gloves=True)
    assert st3["green"]["active"] is False
    assert st3["yellow"]["active"] is False
    assert st3["red"]["blinking"] is True
    assert st3["active_condition"] == "RED_BLINKING"

    # Case 4: Neither Detected -> ALL OFF
    st4 = actuator.update(has_helmet=False, has_gloves=False)
    assert st4["green"]["active"] is False
    assert st4["yellow"]["active"] is False
    assert st4["red"]["blinking"] is False
    assert st4["active_condition"] == "OFF"


def test_inspection_decision_rules():
    """Verify PASS only when helmet and gloves are verified, FAIL on missing or violation."""
    adapter = WindowsVisionAdapter(M3_MODEL_PATH)

    # Empty dummy image
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    norm_res, _ = adapter.inspect_single_image(blank)
    assert norm_res["inspection_status"] == "FAIL"
    assert "Missing" in norm_res["inspection_reason"]


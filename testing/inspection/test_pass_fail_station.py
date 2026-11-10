"""
Pass/Fail Station & Headline Metric Verification Test Suite
Verifies:
  - Automated 20-sample Pass/Fail execution (Assessment 31)
  - Confusion matrix calculations (TP, TN, FP, FN)
  - Pass rate, accuracy, and false-pass rate metrics
  - 50-sample headline metric execution (Assessment 35)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inspection_station.inspection_engine.runner import InspectionStationRunner
from backend.services.kpi_service import kpi_service


def test_20_sample_station_execution():
    """Verify 20-sample station test runs and outputs valid confusion metrics."""
    runner = InspectionStationRunner()
    summary = runner.run_20_sample_station()

    assert summary["total"] == 20
    assert summary["tp"] + summary["fn"] == 10  # 10 Compliant samples
    assert summary["tn"] + summary["fp"] == 10  # 10 Non-compliant samples
    assert summary["accuracy"] >= 90.0, f"Expected high accuracy, got {summary['accuracy']}%"
    assert summary["false_pass_rate"] <= 5.0, f"False-pass rate should be near zero, got {summary['false_pass_rate']}%"


def test_50_sample_headline_metric():
    """Verify 50-sample headline benchmark runs and computes verified accuracy."""
    runner = InspectionStationRunner()
    bench = runner.run_50_sample_headline_benchmark()

    assert bench["total_samples"] == 50
    assert bench["correct_results"] >= 45, f"Expected at least 45/50 correct, got {bench['correct_results']}"
    assert bench["accuracy_pct"] >= 90.0


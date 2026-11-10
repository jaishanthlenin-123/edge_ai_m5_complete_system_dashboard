"""
Headline KPI Calculation & Assessment Metric Service for M5
Computes the three authoritative live dashboard KPIs and assessment statistics:
    - KPI 1: Inspection Accuracy (Correct predictions / Total labelled samples * 100)
    - KPI 2: Inspection Pass Rate (PASS inspections / Total inspections * 100)
    - KPI 3: Motor Anomaly Events (Total motor anomaly alert events in time window)
"""

import sqlite3
from typing import Dict, Any, Optional

from backend.database.db import db_manager


class KPIService:
    """Computes verified live metrics directly from backend database records."""

    def __init__(self, db=None):
        self.db = db or db_manager

    def get_headline_kpis(self) -> Dict[str, Any]:
        """
        Computes the three headline KPIs required by the M5 assessment.
        Returns genuine numbers or 'N/A' when insufficient data is available.
        """
        conn = self.db._get_connection()
        c = conn.cursor()

        # KPI 1: Inspection Accuracy on Labelled Ground-Truth Samples
        c.execute("""
            SELECT 
                COUNT(*) as total_labelled,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count
            FROM inspections
            WHERE ground_truth_label IS NOT NULL
        """)
        row_acc = c.fetchone()
        total_labelled = row_acc[0] if row_acc else 0
        correct_count = row_acc[1] if (row_acc and row_acc[1] is not None) else 0

        if total_labelled > 0:
            kpi1_value = round((correct_count / total_labelled) * 100.0, 1)
            kpi1_display = f"{kpi1_value}%"
            kpi1_detail = f"{correct_count} / {total_labelled} labelled tests"
        else:
            kpi1_value = None
            kpi1_display = "N/A"
            kpi1_detail = "Awaiting labelled sample evaluation"

        # KPI 2: Inspection Pass Rate
        c.execute("""
            SELECT 
                COUNT(*) as total_inspections,
                SUM(CASE WHEN inspection_status = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN inspection_status = 'FAIL' THEN 1 ELSE 0 END) as fail_count
            FROM inspections
            WHERE inspection_status IN ('PASS', 'FAIL')
        """)
        row_pass = c.fetchone()
        total_inspections = row_pass[0] if row_pass else 0
        pass_count = row_pass[1] if (row_pass and row_pass[1] is not None) else 0
        fail_count = row_pass[2] if (row_pass and row_pass[2] is not None) else 0

        if total_inspections > 0:
            kpi2_value = round((pass_count / total_inspections) * 100.0, 1)
            kpi2_display = f"{kpi2_value}%"
            kpi2_detail = f"{pass_count} PASS / {fail_count} FAIL ({total_inspections} total)"
        else:
            kpi2_value = None
            kpi2_display = "N/A"
            kpi2_detail = "No inspection records completed"

        # KPI 3: Motor Anomaly Events
        c.execute("""
            SELECT COUNT(*) 
            FROM alerts 
            WHERE module = 'motor'
        """)
        row_alerts = c.fetchone()
        motor_anomalies_count = row_alerts[0] if row_alerts else 0

        c.execute("SELECT COUNT(*) FROM motor_telemetry WHERE is_anomaly = 1")
        row_telem_anom = c.fetchone()
        telemetry_anomalies = row_telem_anom[0] if row_telem_anom else 0

        conn.close()

        return {
            "kpi1": {
                "id": "kpi_inspection_accuracy",
                "title": "Inspection Accuracy",
                "value": kpi1_value,
                "display": kpi1_display,
                "detail": kpi1_detail,
                "formula": "Correct Predictions / Total Labelled Samples * 100",
                "status": "HEALTHY" if (kpi1_value is not None and kpi1_value >= 85.0) else "NORMAL"
            },
            "kpi2": {
                "id": "kpi_inspection_pass_rate",
                "title": "Inspection Pass Rate",
                "value": kpi2_value,
                "display": kpi2_display,
                "detail": kpi2_detail,
                "formula": "PASS Inspections / Total Inspections * 100",
                "status": "HEALTHY" if (kpi2_value is not None and kpi2_value > 0) else "STANDBY"
            },
            "kpi3": {
                "id": "kpi_motor_anomaly_events",
                "title": "Motor Anomaly Events",
                "value": motor_anomalies_count,
                "display": str(motor_anomalies_count),
                "detail": f"{motor_anomalies_count} critical alerts ({telemetry_anomalies} anomaly frames)",
                "formula": "Total Motor Anomaly Events Logged in Period",
                "status": "CRITICAL" if motor_anomalies_count > 0 else "NORMAL"
            }
        }

    def compute_confusion_matrix(self) -> Dict[str, Any]:
        """
        Computes full confusion matrix for labelled inspection ground truth.
        Compliant ground truth: Both helmet and gloves expected.
        Non-compliant ground truth: Missing helmet or missing gloves.
        """
        conn = self.db._get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT ground_truth_label, inspection_status
            FROM inspections
            WHERE ground_truth_label IN ('COMPLIANT', 'NON_COMPLIANT')
        """)
        rows = c.fetchall()
        conn.close()

        tp = 0  # Expected COMPLIANT, Predicted PASS
        fn = 0  # Expected COMPLIANT, Predicted FAIL
        tn = 0  # Expected NON_COMPLIANT, Predicted FAIL
        fp = 0  # Expected NON_COMPLIANT, Predicted PASS (False Pass)

        for r in rows:
            gt = r[0]
            pred = r[1]
            if gt == "COMPLIANT":
                if pred == "PASS":
                    tp += 1
                else:
                    fn += 1
            elif gt == "NON_COMPLIANT":
                if pred == "FAIL":
                    tn += 1
                else:
                    fp += 1

        total = tp + tn + fp + fn
        accuracy = round(((tp + tn) / total) * 100.0, 2) if total > 0 else 0.0
        pass_rate = round(((tp + fp) / total) * 100.0, 2) if total > 0 else 0.0
        false_pass_rate = round((fp / (fp + tn)) * 100.0, 2) if (fp + tn) > 0 else 0.0
        precision = round((tp / (tp + fp)) * 100.0, 2) if (tp + fp) > 0 else 0.0
        recall = round((tp / (tp + fn)) * 100.0, 2) if (tp + fn) > 0 else 0.0

        return {
            "total_samples": total,
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "accuracy_pct": accuracy,
            "pass_rate_pct": pass_rate,
            "false_pass_rate_pct": false_pass_rate,
            "precision_pct": precision,
            "recall_pct": recall
        }


# Global KPI Service Instance
kpi_service = KPIService()


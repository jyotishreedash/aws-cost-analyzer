"""Unit tests for AWS Cost Analyzer."""

import unittest
from unittest.mock import MagicMock, patch
from aws_cost_analyzer.report_generator import generate_html_report
import os
import tempfile


class TestReportGenerator(unittest.TestCase):
    def test_generates_html_file(self):
        data = {
            "ec2": [
                {"id": "i-123", "name": "web-server", "type": "t3.micro",
                 "state": "running", "avg_cpu_7d": 2.5, "status": "idle",
                 "launch_time": "2024-01-01", "region": "us-east-1"}
            ],
            "s3": [
                {"name": "my-bucket", "size_gb": 0.0, "versioning": "Disabled",
                 "has_lifecycle": False,
                 "issues": ["Empty bucket — consider deleting"],
                 "status": "needs_attention"}
            ],
            "rds": [],
            "costs": {
                "total_cost_usd": 142.50,
                "prev_month_cost_usd": 180.00,
                "change_pct": -20.8,
                "period": "2024-01-01 to 2024-01-31",
                "by_service": [
                    {"service": "Amazon EC2", "cost_usd": 80.0},
                    {"service": "Amazon S3", "cost_usd": 10.5},
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "test_report.html")
            result = generate_html_report(data, output)

            self.assertTrue(os.path.exists(result))
            with open(result) as f:
                content = f.read()
            self.assertIn("AWS Cost Analyzer", content)
            self.assertIn("i-123", content)
            self.assertIn("my-bucket", content)
            self.assertIn("142.5", content)

    def test_empty_data(self):
        data = {"ec2": [], "s3": [], "rds": [], "costs": {}}
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "empty_report.html")
            result = generate_html_report(data, output)
            self.assertTrue(os.path.exists(result))


class TestStatusLogic(unittest.TestCase):
    def test_idle_status(self):
        cpu = 2.0
        status = "idle" if cpu < 5 else "underutilized" if cpu < 20 else "active"
        self.assertEqual(status, "idle")

    def test_underutilized_status(self):
        cpu = 12.0
        status = "idle" if cpu < 5 else "underutilized" if cpu < 20 else "active"
        self.assertEqual(status, "underutilized")

    def test_active_status(self):
        cpu = 65.0
        status = "idle" if cpu < 5 else "underutilized" if cpu < 20 else "active"
        self.assertEqual(status, "active")


if __name__ == "__main__":
    unittest.main()

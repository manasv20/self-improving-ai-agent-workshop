"""Regression checks for the participant-facing workshop reset contract."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from parcelco.data_io import BASELINE_LEARNINGS, load_tickets, suite_info
from parcelco.graphs.outer import _min_delta, _part_b_tol
from parcelco.paths import EXPECTED_DIR, LEARNINGS_PATH, ROOT


class WorkshopContractTests(unittest.TestCase):
    def test_example_gate_thresholds_match_runtime_defaults(self):
        example = dotenv_values(ROOT / ".env.example")
        self.assertEqual(example["PARCELCO_MIN_DELTA"], "0.05")
        self.assertEqual(example["PARCELCO_PART_B_TOLERANCE"], "0.05")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_min_delta(), 0.05)
            self.assertEqual(_part_b_tol(), 0.05)

    def test_tracked_learnings_are_the_reset_baseline(self):
        expected = BASELINE_LEARNINGS.strip() + "\n"
        self.assertEqual(LEARNINGS_PATH.read_text(), expected)
        self.assertNotIn("## Autonomous lesson", LEARNINGS_PATH.read_text())

    def test_demo_and_full_dataset_counts(self):
        with patch.dict(os.environ, {"PARCELCO_SUITE": "demo"}):
            demo = suite_info()
            self.assertEqual(
                (demo["active_total"], demo["active_improve"], demo["active_holdout"]),
                (47, 28, 19),
            )
        with patch.dict(os.environ, {"PARCELCO_SUITE": "full"}):
            full = suite_info()
            self.assertEqual(
                (full["active_total"], full["active_improve"], full["active_holdout"]),
                (1000, 700, 300),
            )

        ticket_ids = {ticket.id for ticket in load_tickets(respect_suite=False)}
        expected_ids = {path.stem for path in Path(EXPECTED_DIR).glob("*.json")}
        self.assertEqual(expected_ids, ticket_ids)


if __name__ == "__main__":
    unittest.main()

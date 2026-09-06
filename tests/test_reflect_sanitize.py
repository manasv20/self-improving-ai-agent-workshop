"""Reflect must keep only safe, checklist-derived policy lessons."""
from __future__ import annotations

import unittest

from parcelco.graphs.outer import _lesson_from_single, _sanitize_lesson_block
from parcelco.models import ChecklistResult, TicketRunResult


def _result(**kwargs) -> TicketRunResult:
    base = dict(
        ticket_id="T",
        split="improve",
        draft="x",
        passed=False,
        heal_count=2,
        checklist=ChecklistResult(
            passed=False,
            action_ok=False,
            missing=["30-day"],
            forbidden_hits=[],
            detected_action="escalate",
            score=0.0,
            details="fail",
        ),
        attempts=[],
    )
    base.update(kwargs)
    return TicketRunResult(**base)


class TestReflectSanitize(unittest.TestCase):
    def test_drops_device_repair_poison(self):
        poisoned = (
            "- The device has been evaluated against the policy checklist.\n"
            "- The repair was not successful. The device is now in a failed state.\n"
            "- When denying a late refund, cite the 30-day window.\n"
        )
        cleaned = _sanitize_lesson_block(poisoned)
        self.assertNotIn("device", cleaned.lower())
        self.assertNotIn("repair", cleaned.lower())
        self.assertIn("30-day", cleaned)

    def test_missing_action_uses_template_lesson(self):
        result = _result(
            ticket_id="A18",
            draft="…\nACTION: inform",
            passed=True,
            heal_count=1,
            checklist=ChecklistResult(
                passed=True,
                action_ok=True,
                missing=[],
                forbidden_hits=[],
                detected_action="inform",
                score=1.0,
                details="ok",
            ),
            attempts=[
                {
                    "passed": False,
                    "detected_action": None,
                    "expected_action": "inform",
                    "missing": [],
                    "forbidden_hits": [],
                },
                {
                    "passed": True,
                    "detected_action": "inform",
                    "expected_action": "inform",
                    "missing": [],
                    "forbidden_hits": [],
                },
            ],
        )
        lesson = _lesson_from_single(result)
        self.assertIn("ACTION: inform", lesson)
        self.assertNotIn("heal", lesson.lower())

    def test_a02_deny_missing_30_day_is_policy_template(self):
        result = _result(
            ticket_id="A02",
            attempts=[
                {
                    "passed": False,
                    "detected_action": "escalate",
                    "expected_action": "deny",
                    "missing": ["30-day"],
                    "forbidden_hits": [],
                },
                {
                    "passed": False,
                    "detected_action": "escalate",
                    "expected_action": "deny",
                    "missing": ["30-day"],
                    "forbidden_hits": [],
                },
            ],
        )
        lesson = _lesson_from_single(result)
        self.assertIn("ACTION: deny", lesson)
        self.assertIn("30-day", lesson)
        self.assertNotIn("device", lesson.lower())
        self.assertNotIn("repair", lesson.lower())
        self.assertNotIn("checklist", lesson.lower())


if __name__ == "__main__":
    unittest.main()

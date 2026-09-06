"""Reflect must not poison learnings with harness / recovery jargon."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from parcelco.graphs.outer import _lesson_from_single, _sanitize_lesson_block
from parcelco.models import ChecklistResult, TicketRunResult


class TestReflectSanitize(unittest.TestCase):
    def test_drops_automatic_recovery_lessons(self):
        poisoned = (
            "- Heal succeeded after checklist failure: tell the customer.\n"
            "- Use the phrase \"The system automatically recovered your account\".\n"
            "- Always end with ACTION: inform when cancellation is denied in transit.\n"
        )
        cleaned = _sanitize_lesson_block(poisoned)
        self.assertNotIn("Heal succeeded", cleaned)
        self.assertNotIn("automatically recovered", cleaned.lower())
        self.assertIn("ACTION: inform", cleaned)

    def test_missing_action_uses_template_lesson(self):
        result = TicketRunResult(
            ticket_id="A18",
            split="improve",
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
        self.assertNotIn("automatic", lesson.lower())


if __name__ == "__main__":
    unittest.main()

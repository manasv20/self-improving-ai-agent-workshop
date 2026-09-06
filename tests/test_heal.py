"""Structured heal repair brief — typed checklist failures + prior draft."""
from __future__ import annotations

import unittest

from parcelco.heal import build_heal_repair_brief


class TestStructuredHeal(unittest.TestCase):
    def test_heal_brief_includes_prior_draft_and_fixes(self):
        checklist = {
            "passed": False,
            "action_ok": False,
            "detected_action": "inform",
            "missing": ["30-day"],
            "forbidden_hits": ["482.17"],
            "details": "action='inform' expected='escalate'; missing=['30-day']; forbidden=['482.17']",
        }
        draft = "Sorry about that. ACTION: inform"
        brief = build_heal_repair_brief(
            checklist=checklist,
            prior_draft=draft,
            expected_action="escalate",
            heal_n=1,
        )
        self.assertIn("STRUCTURED HEAL", brief)
        self.assertIn("HEAL #1", brief)
        self.assertIn("Sorry about that", brief)
        self.assertIn("ACTION: inform", brief)
        self.assertIn("30-day", brief)
        self.assertIn("482.17", brief)
        self.assertIn("escalate", brief.lower())
        self.assertTrue("must NOT" in brief or "Remove" in brief)
        self.assertIn("Rewrite the full customer reply", brief)
        self.assertIn("NEVER mention heals", brief)

    def test_heal_brief_strips_thinking_from_prior_draft(self):
        checklist = {
            "passed": False,
            "action_ok": True,
            "detected_action": "deny",
            "missing": ["30-day"],
            "forbidden_hits": [],
            "details": "missing 30-day",
        }
        draft = "<think>planning</think>\nOutside the window. ACTION: deny"
        brief = build_heal_repair_brief(
            checklist=checklist,
            prior_draft=draft,
            expected_action="deny",
            heal_n=2,
        )
        self.assertNotIn("<think>", brief)
        self.assertIn("Outside the window", brief)
        self.assertTrue(
            "Include these phrases" in brief or "must include" in brief.lower()
        )

    def test_heal_brief_empty_without_checklist(self):
        self.assertEqual(
            build_heal_repair_brief(
                checklist={}, prior_draft="x", expected_action="inform", heal_n=1
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()

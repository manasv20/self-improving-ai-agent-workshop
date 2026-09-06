"""Checklist must reject harness jargon in customer replies."""
from __future__ import annotations

import unittest

from parcelco.eval.checklist import score_draft
from parcelco.models import Expected


class TestMetaLeak(unittest.TestCase):
    def test_rejects_heal_jargon(self):
        expected = Expected(
            ticket_id="T",
            action="escalate",
            must_include=["30-day", "1 business day"],
            must_not=[],
            notes="test",
        )
        bad = (
            "This ticket failed after 2 heals, so I need to escalate it.\n"
            "A specialist will follow up within 1 business day. Mention 30-day window.\n"
            "ACTION: escalate"
        )
        r = score_draft(bad, expected)
        self.assertFalse(r.passed)
        self.assertTrue(any("heal" in f.lower() or "failed after" in f.lower() for f in r.forbidden_hits))

    def test_clean_escalate_ok(self):
        expected = Expected(
            ticket_id="T",
            action="escalate",
            must_include=["30-day", "1 business day"],
            must_not=[],
            notes="test",
        )
        good = (
            "I can't waive the 30-day refund window for VIP requests.\n"
            "I've escalated this to a specialist who will follow up within 1 business day.\n"
            "ACTION: escalate"
        )
        r = score_draft(good, expected)
        self.assertTrue(r.passed)


if __name__ == "__main__":
    unittest.main()

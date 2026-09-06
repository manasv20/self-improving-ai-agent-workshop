"""Checklist supports OR-groups for non-deterministic paraphrases."""
from __future__ import annotations

import unittest

from parcelco.eval.checklist import score_draft
from parcelco.models import Expected


class TestIncludeAny(unittest.TestCase):
    def test_any_group_passes_with_paraphrase(self):
        expected = Expected(
            ticket_id="A91",
            action="deny",
            must_include_any=[["30-day", "30 day", "30 days"]],
            difficulty="ambiguous",
        )
        draft = (
            "I understand this is outside our 30 day refund window, so I can't refund.\n"
            "ACTION: deny"
        )
        r = score_draft(draft, expected)
        self.assertTrue(r.passed)

    def test_any_group_fails_when_none_match(self):
        expected = Expected(
            ticket_id="A91",
            action="deny",
            must_include_any=[["30-day", "30 day"]],
        )
        draft = "Too late for a refund.\nACTION: deny"
        r = score_draft(draft, expected)
        self.assertFalse(r.passed)
        self.assertTrue(any("30" in m for m in r.missing))


if __name__ == "__main__":
    unittest.main()

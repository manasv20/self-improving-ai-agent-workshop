"""Tests for the evaluation layer (Python rules + optional SLM gate)."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from parcelco.eval.evaluate import evaluate_draft
from parcelco.eval.slm_judge import judge_draft, rules_rubric
from parcelco.models import Expected


class SlmJudgeTests(unittest.TestCase):
    def test_rules_rubric_mirrors_expected(self):
        expected = Expected(
            ticket_id="A01",
            action="refund",
            must_include=["30-day"],
            must_include_any=[["sorry", "apologize"]],
            must_not=["VIP exception"],
            notes="damaged",
        )
        rubric = rules_rubric(expected)
        self.assertEqual(rubric["required_action"], "refund")
        self.assertEqual(rubric["must_include_all"], ["30-day"])
        self.assertEqual(rubric["must_include_any_groups"], [["sorry", "apologize"]])
        self.assertIn("heal", rubric["never_mention_harness_jargon"])

    def test_disabled_when_no_eval_model(self):
        with patch.dict("os.environ", {"PARCELCO_EVAL_MODEL": ""}, clear=False):
            out = judge_draft("hi\nACTION: inform", Expected(ticket_id="X", action="inform"))
        self.assertFalse(out["enabled"])


class EvaluateLayerTests(unittest.TestCase):
    def test_python_only_gate_without_eval_model(self):
        expected = Expected(ticket_id="A01", action="refund", must_include=["30-day"])
        draft = "Refund within the 30-day window.\nACTION: refund"
        with patch.dict("os.environ", {"PARCELCO_EVAL_MODEL": ""}, clear=False):
            bundle = evaluate_draft(draft, expected)
        self.assertEqual(bundle["eval_source"], "python")
        self.assertTrue(bundle["passed"])
        self.assertTrue(bundle["checklist"].passed)

    def test_slm_verdict_is_the_gate(self):
        expected = Expected(ticket_id="A01", action="refund", must_include=["30-day"])
        # Python would PASS; SLM says FAIL → gate must FAIL and heal should see signal.
        draft = "Refund within the 30-day window.\nACTION: refund"
        fake = SimpleNamespace(
            content=(
                '{"passed": false, "action_ok": true, "missing": ["30-day"], '
                '"forbidden_hits": [], "rationale": "SLM did not see the phrase."}'
            )
        )
        with patch.dict("os.environ", {"PARCELCO_EVAL_MODEL": "qwen2.5-1.5b-instruct"}):
            with patch("parcelco.llm.eval_chat_model") as mock_model:
                with patch("parcelco.tracing.get_callbacks", return_value=[]):
                    mock_model.return_value.invoke.return_value = fake
                    bundle = evaluate_draft(draft, expected)
        self.assertEqual(bundle["eval_source"], "slm")
        self.assertFalse(bundle["passed"])
        self.assertTrue(bundle["checklist"].passed or bundle["slm_judge"]["passed"] is False)
        self.assertFalse(bundle["slm_judge"]["passed"])

    def test_slm_error_falls_back_to_python(self):
        expected = Expected(ticket_id="A01", action="refund", must_include=["30-day"])
        draft = "Refund within the 30-day window.\nACTION: refund"
        with patch.dict("os.environ", {"PARCELCO_EVAL_MODEL": "qwen2.5-1.5b-instruct"}):
            with patch("parcelco.llm.eval_chat_model") as mock_model:
                with patch("parcelco.tracing.get_callbacks", return_value=[]):
                    mock_model.return_value.invoke.side_effect = RuntimeError("down")
                    bundle = evaluate_draft(draft, expected)
        self.assertEqual(bundle["eval_source"], "python_fallback")
        self.assertTrue(bundle["passed"])
        self.assertTrue(bundle["checklist"].passed)


if __name__ == "__main__":
    unittest.main()

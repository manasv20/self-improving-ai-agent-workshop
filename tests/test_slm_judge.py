"""Tests for the evaluation layer (Python gate + advisory SLM → Reflect)."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from parcelco.eval.checklist import looks_like_option_menu, score_draft
from parcelco.eval.evaluate import evaluate_draft
from parcelco.eval.slm_judge import judge_draft, rules_rubric
from parcelco.graphs.outer import _template_lesson
from parcelco.heal import build_heal_repair_brief
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
        self.assertIn("refund", rubric["acceptable_actions"])
        self.assertIn("heal", rubric["never_mention_harness_jargon"])

    def test_grounds_or_group_and_keeps_suggestions(self):
        expected = Expected(
            ticket_id="A91",
            action="deny",
            must_include_any=[["30-day", "30 day", "30 days"]],
        )
        draft = (
            "Sorry — this is outside our 30-day refund window, so I must deny the refund.\n"
            "ACTION: deny"
        )
        fake = SimpleNamespace(
            content=(
                '{"passed": false, "action_ok": true, '
                '"missing": ["30-day", "30 day", "30 days"], '
                '"forbidden_hits": ["heal"], '
                '"tone_ok": false, "clarity_ok": true, "policy_coherence": true, '
                '"soft_ok": false, '
                '"suggestions": ["Acknowledge the customer frustration in one short sentence."], '
                '"rationale": "rules ok but tone flat"}'
            )
        )
        with patch.dict("os.environ", {"PARCELCO_EVAL_MODEL": "qwen2.5-1.5b-instruct"}):
            with patch("parcelco.llm.eval_chat_model") as mock_model:
                with patch("parcelco.tracing.get_callbacks", return_value=[]):
                    mock_model.return_value.invoke.return_value = fake
                    out = judge_draft(draft, expected)
        self.assertTrue(out["rules_passed"])
        self.assertFalse(out["soft_ok"])
        self.assertEqual(out["missing"], [])
        self.assertIn("Acknowledge", out["suggestions"][0])

    def test_slm_insight_does_not_override_python_gate(self):
        """Assist mode: SLM may note inform+options, but Python remains the heal gate."""
        expected = Expected(
            ticket_id="X01",
            action="refund",
            must_include=["30-day"],
            notes="customer asked for options",
        )
        draft = (
            "Within our 30-day window you can: (1) get a refund or (2) request a replacement. "
            "Which do you prefer?\n"
            "ACTION: inform"
        )
        self.assertTrue(looks_like_option_menu(draft))
        fake = SimpleNamespace(
            content=(
                '{"passed": true, "action_ok": true, "missing": [], "forbidden_hits": [], '
                '"tone_ok": true, "clarity_ok": true, "policy_coherence": true, '
                '"soft_ok": true, "suggestions": [], '
                '"rationale": "listed two options so inform is correct"}'
            )
        )
        with patch.dict(
            "os.environ",
            {
                "PARCELCO_EVAL_MODEL": "qwen2.5-1.5b-instruct",
                "PARCELCO_EVAL_MODE": "assist",
            },
        ):
            with patch("parcelco.llm.eval_chat_model") as mock_model:
                with patch("parcelco.tracing.get_callbacks", return_value=[]):
                    mock_model.return_value.invoke.return_value = fake
                    out = judge_draft(draft, expected)
                    bundle = evaluate_draft(draft, expected)
        self.assertTrue(out["action_ok"])
        self.assertEqual(out.get("action_intelligence"), "inform_options")
        self.assertFalse(bundle["checklist"].passed)
        self.assertFalse(bundle["passed"])  # Python gate — learn via Reflect, not override
        self.assertFalse(bundle["soft_heal"])
        self.assertIn("insight=inform_options", bundle["details"])


class EvaluateLayerTests(unittest.TestCase):
    def test_a20_label_allows_inform_without_slm(self):
        expected = Expected(
            ticket_id="A20",
            action="refund",
            acceptable_actions=["refund", "inform"],
            must_include=["30-day"],
        )
        draft = (
            "You have two options within the 30-day window: refund or replacement.\n"
            "ACTION: inform"
        )
        r = score_draft(draft, expected)
        self.assertTrue(r.action_ok)
        self.assertTrue(r.passed)

    def test_assist_does_not_soft_heal(self):
        expected = Expected(ticket_id="A01", action="refund", must_include=["30-day"])
        draft = "Refund within the 30-day window.\nACTION: refund"
        fake = SimpleNamespace(
            content=(
                '{"passed": false, "action_ok": true, "missing": [], "forbidden_hits": [], '
                '"tone_ok": false, "clarity_ok": true, "policy_coherence": true, '
                '"soft_ok": false, '
                '"suggestions": ["Open with empathy before stating the refund."], '
                '"rationale": "cold tone"}'
            )
        )
        with patch.dict(
            "os.environ",
            {
                "PARCELCO_EVAL_MODEL": "qwen2.5-1.5b-instruct",
                "PARCELCO_EVAL_MODE": "assist",
            },
        ):
            with patch("parcelco.llm.eval_chat_model") as mock_model:
                with patch("parcelco.tracing.get_callbacks", return_value=[]):
                    mock_model.return_value.invoke.return_value = fake
                    bundle = evaluate_draft(draft, expected)
        self.assertTrue(bundle["checklist"].passed)
        self.assertTrue(bundle["passed"])  # soft notes do not force heal
        self.assertFalse(bundle["soft_heal"])

    def test_heal_brief_is_checklist_only(self):
        brief = build_heal_repair_brief(
            checklist={
                "passed": False,
                "missing": ["30-day"],
                "forbidden_hits": [],
                "detected_action": "inform",
            },
            prior_draft="Here are options.\nACTION: inform",
            expected_action="refund",
            heal_n=1,
            slm_judge={
                "enabled": True,
                "soft_ok": False,
                "suggestions": ["Add a one-line apology."],
                "rationale": "tone is abrupt",
            },
            allowed_actions=["refund", "inform"],
        )
        self.assertIn("30-day", brief)
        self.assertNotIn("SLM suggestion", brief)
        self.assertNotIn("Add a one-line apology", brief)

    def test_reflect_turns_slm_insight_into_lesson(self):
        lesson = _template_lesson(
            expected_action="refund",
            missing=[],
            forbidden=[],
            detected0="inform",
            passed=True,
            slm_judge={
                "enabled": True,
                "action_intelligence": "inform_options",
                "suggestions": [],
                "rationale": "option menu",
            },
            allowed_actions=["refund"],
        )
        self.assertIn("ACTION: inform", lesson)
        self.assertIn("options", lesson.lower())
        self.assertNotIn("do not use `inform`", lesson)


if __name__ == "__main__":
    unittest.main()

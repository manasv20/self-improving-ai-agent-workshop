"""Unified evaluation: Python Expected rules + optional SLM gate.

When ``PARCELCO_EVAL_MODEL`` is set, the eval SLM applies those rules and its
verdict drives heal/PASS. The deterministic checklist always runs for evidence
and concrete heal briefs; it is the gate only when the SLM is off or errors.
"""
from __future__ import annotations

from typing import Any

from parcelco.eval.checklist import score_draft
from parcelco.eval.slm_judge import eval_model_enabled, judge_draft
from parcelco.models import ChecklistResult, Expected


def evaluate_draft(
    draft: str,
    expected: Expected,
    *,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Return checklist + slm_judge + the gate used for heal."""
    checklist = score_draft(draft, expected)
    slm_judge = judge_draft(draft, expected, trace_id=trace_id)
    source = "python"
    gate_passed = bool(checklist.passed)
    gate_details = checklist.details

    if eval_model_enabled():
        if slm_judge.get("error") or slm_judge.get("passed") is None:
            source = "python_fallback"
            slm_judge = {
                **slm_judge,
                "gate_fallback": True,
                "gate_reason": slm_judge.get("error") or "judge_no_verdict",
            }
        else:
            source = "slm"
            gate_passed = bool(slm_judge.get("passed"))
            miss = slm_judge.get("missing") or []
            forbid = slm_judge.get("forbidden_hits") or []
            rationale = slm_judge.get("rationale") or ""
            gate_details = (
                f"SLM({slm_judge.get('model')}): "
                f"passed={gate_passed}; missing={miss}; forbidden={forbid}"
                + (f"; {rationale}" if rationale else "")
            )
            # Prefer concrete Python phrase lists for heal when available;
            # otherwise carry SLM lists so heal has something actionable.
            if not gate_passed and not checklist.missing and not checklist.forbidden_hits:
                checklist = ChecklistResult(
                    passed=False,
                    action_ok=bool(slm_judge.get("action_ok", False)),
                    missing=[str(x) for x in miss],
                    forbidden_hits=[str(x) for x in forbid],
                    detected_action=checklist.detected_action,
                    score=0.0 if not gate_passed else checklist.score,
                    details=gate_details,
                )

    return {
        "checklist": checklist,
        "slm_judge": slm_judge,
        "passed": gate_passed,
        "eval_source": source,
        "details": gate_details,
    }

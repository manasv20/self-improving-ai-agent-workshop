"""Unified evaluation: Python Expected hard gate + advisory SLM.

Modes (``PARCELCO_EVAL_MODE``):
- ``assist`` (default): Python checklist is the heal/PASS gate. The SLM still runs
  as a scored second opinion (Langfuse + Reflect), but does **not** force heals or
  override ACTION — durable improvement comes from Reflect → learnings.md.
- ``gate``: SLM overall verdict is the heal/PASS gate (Python fallback on judge error).
  Heal phrase lists always come from Python Expected.
"""
from __future__ import annotations

import os
from typing import Any

from parcelco.eval.checklist import score_draft
from parcelco.eval.slm_judge import eval_model_enabled, judge_draft
from parcelco.models import Expected


def eval_mode() -> str:
    raw = (os.getenv("PARCELCO_EVAL_MODE") or "").strip().lower()
    if raw in {"assist", "gate", "off"}:
        return raw
    if eval_model_enabled():
        return "assist"
    return "off"


def evaluate_draft(
    draft: str,
    expected: Expected,
    *,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Return checklist + slm_judge + the gate used for heal."""
    checklist = score_draft(draft, expected)
    mode = eval_mode()
    slm_judge: dict[str, Any] = {"enabled": False, "model": "", "error": None}
    if mode in {"assist", "gate"} and eval_model_enabled():
        slm_judge = judge_draft(draft, expected, trace_id=trace_id)

    source = "python"
    gate_passed = bool(checklist.passed)
    gate_details = checklist.details

    if mode == "gate" and eval_model_enabled():
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
                f"passed={gate_passed}; rules={slm_judge.get('rules_passed')}; "
                f"soft={slm_judge.get('soft_ok')}; missing={miss}; forbidden={forbid}"
                + (f"; {rationale}" if rationale else "")
            )
    elif mode == "assist" and slm_judge.get("enabled") and not slm_judge.get("error"):
        source = "python+slm"
        soft_ok = slm_judge.get("soft_ok")
        agree = (
            bool(slm_judge.get("rules_passed", slm_judge.get("passed")))
            == bool(checklist.passed)
        )
        gate_details = (
            f"{checklist.details} · SLM observe "
            f"{'agree' if agree else 'differ'} · soft="
            f"{'ok' if soft_ok else 'note'} ({slm_judge.get('model')})"
        )
        if slm_judge.get("action_intelligence"):
            gate_details += f" · insight={slm_judge.get('action_intelligence')}"
        # Advisory only: gate stays on Python. Insights flow to Reflect → learnings.

    return {
        "checklist": checklist,
        "slm_judge": slm_judge,
        "passed": gate_passed,
        "eval_source": source,
        "eval_mode": mode,
        "details": gate_details,
        "soft_heal": False,
    }

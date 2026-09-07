"""Eval SLM — grades drafts using the Python Expected rule pack as the rubric.

When ``PARCELCO_EVAL_MODEL`` is set, ``evaluate_draft`` uses this verdict as the
heal/PASS gate (with Python checklist as fallback on judge failure).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from parcelco.eval.checklist import META_FORBIDDEN, strip_reasoning
from parcelco.models import Expected

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def eval_model_enabled() -> bool:
    return bool(os.getenv("PARCELCO_EVAL_MODEL", "").strip())


def eval_model_name() -> str:
    return os.getenv("PARCELCO_EVAL_MODEL", "").strip()


def rules_rubric(expected: Expected) -> dict[str, Any]:
    """Serialize Python Expected (+ global meta bans) for the SLM prompt."""
    return {
        "required_action": expected.action,
        "must_include_all": list(expected.must_include or []),
        "must_include_any_groups": list(expected.must_include_any or []),
        "must_not": list(expected.must_not or []),
        "never_mention_harness_jargon": list(META_FORBIDDEN),
        "notes": expected.notes or "",
    }


def _parse_judge_json(raw: str) -> dict[str, Any] | None:
    text = strip_reasoning(raw or "")
    match = _JSON_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _coerce_result(data: dict[str, Any], *, raw: str) -> dict[str, Any]:
    passed = bool(data.get("passed"))
    missing = [str(x) for x in (data.get("missing") or []) if str(x).strip()]
    forbidden = [str(x) for x in (data.get("forbidden_hits") or []) if str(x).strip()]
    action_ok = data.get("action_ok")
    if action_ok is None:
        action_ok = passed and not missing
    return {
        "enabled": True,
        "model": eval_model_name(),
        "passed": passed,
        "action_ok": bool(action_ok),
        "missing": missing,
        "forbidden_hits": forbidden,
        "rationale": str(data.get("rationale") or "")[:600],
        "raw": (raw or "")[:800],
        "error": None,
    }


def judge_draft(draft: str, expected: Expected, *, trace_id: str | None = None) -> dict[str, Any]:
    """Ask the eval SLM to apply the Python rule pack to a customer reply."""
    if not eval_model_enabled():
        return {"enabled": False, "model": "", "error": None}

    from parcelco.llm import eval_chat_model
    from parcelco.tracing import get_callbacks

    rubric = rules_rubric(expected)
    customer = strip_reasoning(draft)

    prompt = (
        "You are ParcelCo's evaluation layer. Grade the customer reply using ONLY "
        "the RULES JSON (exported from Python Expected labels).\n\n"
        "Matching rules:\n"
        "- Case-insensitive substring checks for must_include / must_not / jargon.\n"
        "- must_include_any_groups: each group needs at least one alternative present.\n"
        "- required_action must match the final ACTION: refund|deny|escalate|inform line.\n"
        "- Do not invent extra requirements beyond RULES.\n"
        "- passed=true only if action matches AND all must_include_all are present AND "
        "every any-group is satisfied AND no must_not/jargon hits.\n\n"
        f"RULES:\n{json.dumps(rubric, indent=2)}\n\n"
        f"CUSTOMER REPLY:\n{customer}\n\n"
        "Return ONLY one JSON object:\n"
        '{"passed": boolean, "action_ok": boolean, "missing": string[], '
        '"forbidden_hits": string[], "rationale": short string}\n'
    )

    try:
        callbacks = get_callbacks(trace_id=trace_id)
        msg = eval_chat_model().invoke(
            prompt,
            config={"callbacks": callbacks} if callbacks else {},
        )
        raw = getattr(msg, "content", None) or str(msg)
        data = _parse_judge_json(raw)
        if not data:
            return {
                "enabled": True,
                "model": eval_model_name(),
                "passed": None,
                "error": "judge_parse_failed",
                "raw": (raw or "")[:800],
            }
        return _coerce_result(data, raw=raw)
    except Exception as exc:  # noqa: BLE001 — fall back to Python gate upstream
        return {
            "enabled": True,
            "model": eval_model_name(),
            "passed": None,
            "error": str(exc)[:240],
        }

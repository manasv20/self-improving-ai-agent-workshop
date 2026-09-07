"""Eval SLM — hard Expected-rule check + soft intelligence for heal/Reflect."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from parcelco.eval.checklist import (
    META_FORBIDDEN,
    allowed_actions,
    looks_like_option_menu,
    parse_action,
    strip_reasoning,
)
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
        "acceptable_actions": allowed_actions(expected),
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


def _ground_hard_claims(data: dict[str, Any], draft: str, expected: Expected) -> dict[str, Any]:
    """Ground hard rule claims; keep soft intelligence fields from the model."""
    lower = strip_reasoning(draft).lower()
    missing_claimed = [str(x) for x in (data.get("missing") or []) if str(x).strip()]
    or_present: set[str] = set()
    for group in expected.must_include_any or []:
        alts = [str(a) for a in group if str(a).strip()]
        if any(a.lower() in lower for a in alts):
            or_present.update(a.lower() for a in alts)
    missing: list[str] = []
    for m in missing_claimed:
        ml = m.lower()
        if ml in or_present or ml in lower:
            continue
        if " | " in m:
            alts = [p.strip() for p in m.split("|") if p.strip()]
            if any(a.lower() in lower for a in alts):
                continue
        missing.append(m)
    for req in expected.must_include or []:
        if req.lower() not in lower and req not in missing:
            missing.append(req)
    for group in expected.must_include_any or []:
        alts = [str(a) for a in group if str(a).strip()]
        if alts and not any(a.lower() in lower for a in alts):
            label = " | ".join(alts)
            if label not in missing:
                missing.append(label)

    forbid_claimed = [str(x) for x in (data.get("forbidden_hits") or []) if str(x).strip()]
    allowed_forbid = {f.lower() for f in (expected.must_not or [])} | {m.lower() for m in META_FORBIDDEN}
    forbidden = [
        f for f in forbid_claimed
        if f.lower() in lower and f.lower() in allowed_forbid
    ]

    detected = parse_action(draft)
    allowed = set(allowed_actions(expected))
    phrase_ok = not missing and not forbidden
    labeled_ok = bool(detected and detected in allowed)
    # SLM intelligence: option menus may use ACTION: inform even when preferred
    # disposition is refund/deny/escalate — only when the model claims action_ok
    # and the draft actually lists multiple customer choices.
    slm_claims_action = data.get("action_ok")
    inform_options_ok = (
        detected == "inform"
        and phrase_ok
        and looks_like_option_menu(draft)
        and (slm_claims_action is True or "inform" in allowed or "option" in (expected.notes or "").lower())
    )
    action_ok = labeled_ok or inform_options_ok
    rules_passed = action_ok and phrase_ok
    action_intelligence = "inform_options" if (inform_options_ok and not labeled_ok) else None

    suggestions = []
    for s in data.get("suggestions") or []:
        text = str(s).strip()
        if text and text not in suggestions:
            suggestions.append(text[:240])
    suggestions = suggestions[:5]

    tone_ok = data.get("tone_ok")
    clarity_ok = data.get("clarity_ok")
    policy_ok = data.get("policy_coherence")
    soft_flags = [x for x in (tone_ok, clarity_ok, policy_ok) if x is not None]
    soft_ok = all(bool(x) for x in soft_flags) if soft_flags else bool(data.get("soft_ok", True))
    if suggestions and data.get("soft_ok") is False:
        soft_ok = False

    rationale = str(data.get("rationale") or "")[:600]
    if action_intelligence and "option" not in rationale.lower():
        rationale = (rationale + " · SLM: inform OK for option menu").strip(" ·")

    return {
        "passed": rules_passed and soft_ok,
        "rules_passed": rules_passed,
        "soft_ok": soft_ok,
        "action_ok": action_ok,
        "action_intelligence": action_intelligence,
        "missing": missing,
        "forbidden_hits": forbidden,
        "tone_ok": None if tone_ok is None else bool(tone_ok),
        "clarity_ok": None if clarity_ok is None else bool(clarity_ok),
        "policy_coherence": None if policy_ok is None else bool(policy_ok),
        "suggestions": suggestions,
        "rationale": rationale,
    }


def _coerce_result(data: dict[str, Any], *, raw: str, draft: str, expected: Expected) -> dict[str, Any]:
    grounded = _ground_hard_claims(data, draft, expected)
    return {
        "enabled": True,
        "model": eval_model_name(),
        **grounded,
        "raw": (raw or "")[:800],
        "error": None,
    }


def judge_draft(draft: str, expected: Expected, *, trace_id: str | None = None) -> dict[str, Any]:
    """Ask the eval SLM for hard-rule grading plus soft coaching intelligence."""
    if not eval_model_enabled():
        return {"enabled": False, "model": "", "error": None}

    from parcelco.llm import eval_chat_model
    from parcelco.tracing import get_callbacks

    rubric = rules_rubric(expected)
    customer = strip_reasoning(draft)
    ticket_notes = expected.notes or ""

    prompt = (
        "You are ParcelCo's evaluation SLM. Do two jobs:\n"
        "1) HARD RULES — apply ONLY the RULES JSON (Python Expected labels).\n"
        "2) SOFT INTELLIGENCE — coach the reply for tone, clarity, and policy fit.\n\n"
        "Hard matching:\n"
        "- Case-insensitive substrings.\n"
        "- must_include_all: every phrase must appear.\n"
        "- must_include_any_groups: OR groups — only one alternative per group is required.\n"
        "- must_not / jargon: only flag phrases that actually appear.\n"
        "- ACTION line: prefer required_action, but any tag in acceptable_actions is OK.\n"
        "- ACTION intelligence: if the reply lists ≥2 concrete customer choices "
        "(refund vs replace, refuse vs redirect, etc.) and ends with ACTION: inform, "
        "set action_ok=true — presenting options is inform, not a fail.\n"
        "- Do not invent extra hard requirements.\n\n"
        "Soft intelligence:\n"
        "- Be concrete and actionable in suggestions (max 5).\n"
        "- Do not suggest VIP exceptions, invented dollar amounts, or harness jargon.\n"
        "- soft_ok=false only when a real customer-facing quality issue exists "
        "even if hard rules pass.\n"
        "- Do NOT soft-fail solely because ACTION is inform when an option menu is present.\n\n"
        f"RULES:\n{json.dumps(rubric, indent=2)}\n\n"
        f"TICKET NOTES: {ticket_notes or '(none)'}\n\n"
        f"CUSTOMER REPLY:\n{customer}\n\n"
        "Return ONLY one JSON object with keys:\n"
        '{"passed": boolean, "action_ok": boolean, "missing": string[], '
        '"forbidden_hits": string[], "tone_ok": boolean, "clarity_ok": boolean, '
        '"policy_coherence": boolean, "soft_ok": boolean, '
        '"suggestions": string[], "rationale": short string}\n'
        "`passed` should be true only when hard rules and soft_ok are both good.\n"
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
        return _coerce_result(data, raw=raw, draft=draft, expected=expected)
    except Exception as exc:  # noqa: BLE001 — fall back upstream
        return {
            "enabled": True,
            "model": eval_model_name(),
            "passed": None,
            "error": str(exc)[:240],
        }

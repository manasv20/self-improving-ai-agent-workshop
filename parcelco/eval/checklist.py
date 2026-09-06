from __future__ import annotations

import re

from parcelco.models import ChecklistResult, Expected

_ACTION_RE = re.compile(
    r"^\s*ACTION\s*:\s*(refund|deny|escalate|inform)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# DeepSeek-R1 (and similar) emit chain-of-thought before the customer reply
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

# Never allowed in customer-facing replies (harness jargon leakage)
META_FORBIDDEN = (
    "failed after",
    "heal",
    "heals",
    "checklist",
    "learnings.md",
    "structured heal",
    "attempt 1",
    "attempt 2",
    "attempt 3",
)


def strip_reasoning(draft: str) -> str:
    """Drop R1-style thinking blocks so checklist grades the customer-facing reply."""
    text = _THINK_RE.sub("", draft or "")
    # orphaned open think (truncated generation)
    text = re.sub(r"<think>[\s\S]*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def parse_action(draft: str) -> str | None:
    matches = _ACTION_RE.findall(strip_reasoning(draft))
    if not matches:
        return None
    return matches[-1].lower()


def _missing_any_groups(lower: str, groups: list[list[str]]) -> list[str]:
    """Return labels for OR-groups where none of the alternatives appear."""
    missing: list[str] = []
    for group in groups:
        alts = [str(a) for a in group if str(a).strip()]
        if not alts:
            continue
        if not any(a.lower() in lower for a in alts):
            missing.append(" | ".join(alts))
    return missing


def score_draft(draft: str, expected: Expected) -> ChecklistResult:
    text = strip_reasoning(draft)
    lower = text.lower()
    detected = parse_action(text)

    missing = [m for m in expected.must_include if m.lower() not in lower]
    missing += _missing_any_groups(lower, expected.must_include_any or [])
    forbidden_hits = [f for f in expected.must_not if f.lower() in lower]
    for meta in META_FORBIDDEN:
        if meta in lower and meta not in [x.lower() for x in forbidden_hits]:
            forbidden_hits.append(meta)
    action_ok = detected == expected.action

    checks: list[bool] = [action_ok]
    if expected.must_include or expected.must_include_any:
        checks.append(not missing)
    if forbidden_hits:
        checks.append(len(forbidden_hits) == 0)

    score = sum(1 for ok in checks if ok) / max(len(checks), 1)
    passed = action_ok and not missing and not forbidden_hits

    return ChecklistResult(
        passed=passed,
        action_ok=action_ok,
        missing=missing,
        forbidden_hits=forbidden_hits,
        detected_action=detected,
        score=score,
        details=(
            f"action={detected!r} expected={expected.action!r}; "
            f"missing={missing}; forbidden={forbidden_hits}"
        ),
    )

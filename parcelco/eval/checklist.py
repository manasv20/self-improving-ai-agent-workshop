from __future__ import annotations

import re

from parcelco.models import ChecklistResult, Expected

_ACTION_RE = re.compile(
    r"^\s*ACTION\s*:\s*(refund|deny|escalate|inform)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# DeepSeek-R1 (and similar) emit chain-of-thought before the customer reply
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
_BULLET_CHOICE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+\S", re.MULTILINE)

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


def allowed_actions(expected: Expected) -> list[str]:
    """Primary action plus any labeled alternates (deduped, lowercased)."""
    out: list[str] = [expected.action]
    for raw in expected.acceptable_actions or []:
        a = str(raw).strip().lower()
        if a in {"refund", "deny", "escalate", "inform"} and a not in out:
            out.append(a)
    return out


def looks_like_option_menu(draft: str) -> bool:
    """True when the reply presents the customer with multiple concrete choices."""
    text = strip_reasoning(draft or "")
    if not text:
        return False
    body = "\n".join(
        ln for ln in text.splitlines() if not _ACTION_RE.match(ln.strip())
    )
    lower = body.lower()
    bullets = len(_BULLET_CHOICE_RE.findall(body))
    if bullets >= 2:
        return True
    if "option" in lower or "you can" in lower or "either" in lower:
        choice_words = (
            "refund",
            "replace",
            "replacement",
            "exchange",
            "repair",
            "credit",
            "redirect",
            "refuse",
            "return",
            "reship",
        )
        hits = sum(1 for w in choice_words if w in lower)
        if hits >= 2:
            return True
        if " or " in lower and hits >= 1:
            return True
    return False


def action_matches(detected: str | None, expected: Expected, draft: str = "") -> bool:
    """Hard ACTION match against primary + labeled acceptable_actions."""
    del draft  # draft semantics belong to the eval SLM, not the phrase checklist
    if not detected:
        return False
    return detected.lower() in set(allowed_actions(expected))


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
    allowed = allowed_actions(expected)
    action_ok = action_matches(detected, expected, text)

    checks: list[bool] = [action_ok]
    if expected.must_include or expected.must_include_any:
        checks.append(not missing)
    if forbidden_hits:
        checks.append(len(forbidden_hits) == 0)

    score = sum(1 for ok in checks if ok) / max(len(checks), 1)
    passed = action_ok and not missing and not forbidden_hits
    allowed_bit = (
        f" allowed={allowed}" if allowed != [expected.action] or action_ok and detected != expected.action else ""
    )

    return ChecklistResult(
        passed=passed,
        action_ok=action_ok,
        missing=missing,
        forbidden_hits=forbidden_hits,
        detected_action=detected,
        score=score,
        details=(
            f"action={detected!r} expected={expected.action!r}{allowed_bit}; "
            f"missing={missing}; forbidden={forbidden_hits}"
        ),
    )

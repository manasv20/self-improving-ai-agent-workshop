"""Structured heal — turn checklist failures into an explicit repair brief."""
from __future__ import annotations

from typing import Any

from parcelco.eval.checklist import strip_reasoning


def build_heal_repair_brief(
    *,
    checklist: dict[str, Any],
    prior_draft: str,
    expected_action: str | None,
    heal_n: int,
) -> str:
    """Build a typed repair package for Generate after a checklist FAIL.

    Includes the previous customer-facing draft and concrete fix instructions
    (ACTION, must-include, must-not) so the model repairs instead of guessing.
    """
    if not checklist:
        return ""

    missing = [str(x) for x in (checklist.get("missing") or [])]
    forbidden = [str(x) for x in (checklist.get("forbidden_hits") or [])]
    detected = checklist.get("detected_action")
    want = (expected_action or checklist.get("expected_action") or "").strip() or "?"
    prior = strip_reasoning(prior_draft or "").strip() or "(empty draft)"

    fixes: list[str] = []
    if want and want != "?" and (detected or "").lower() != want.lower():
        fixes.append(
            f"- ACTION line must be exactly: ACTION: {want}  "
            f"(you used: {detected or 'none'})"
        )
    elif want and want != "?":
        fixes.append(f"- Keep ACTION: {want} on its own last line")

    if missing:
        fixes.append(
            "- Include these phrases exactly (case-insensitive ok): "
            + ", ".join(repr(m) for m in missing)
        )
    if forbidden:
        fixes.append(
            "- Remove / must NOT mention: " + ", ".join(repr(f) for f in forbidden)
        )
        fixes.append("- Do not invent dollar amounts or grant VIP exceptions in text")

    if not fixes:
        details = checklist.get("details") or "checklist failed"
        fixes.append(f"- Fix checklist failure: {details}")

    fix_block = "\n".join(fixes)
    return (
        f"\n=== STRUCTURED HEAL #{heal_n} (internal repair — customer never sees this block) ===\n"
        f"Your previous reply failed the harness checklist.\n\n"
        f"PREVIOUS DRAFT:\n---\n{prior}\n---\n\n"
        f"REQUIRED FIXES:\n{fix_block}\n"
        f"- Write ONLY a normal customer-facing ParcelCo support reply.\n"
        f"- NEVER mention heals, retries, checklist, attempts, harness, or internal failures.\n"
        f"- Do not say things like \"failed after 2 heals\" — the customer must not see that.\n\n"
        f"Rewrite the full customer reply from scratch incorporating every fix.\n"
        f"End with a single line: ACTION: refund|deny|escalate|inform\n"
        f"=== END STRUCTURED HEAL ===\n"
    )

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
    slm_judge: dict[str, Any] | None = None,
    allowed_actions: list[str] | None = None,
) -> str:
    """Build a typed repair package for Generate after an eval FAIL.

    Uses Python Expected phrase/ACTION fixes only. SLM insights belong in
    Reflect → learnings.md (cross-ticket self-improvement), not every heal.
    """
    del slm_judge  # advisory / Reflect only
    if not checklist:
        return ""

    checklist = checklist or {}
    missing = [str(x) for x in (checklist.get("missing") or [])]
    forbidden = [str(x) for x in (checklist.get("forbidden_hits") or [])]
    detected = checklist.get("detected_action")
    want = (expected_action or checklist.get("expected_action") or "").strip() or "?"
    allowed = [a.lower() for a in (allowed_actions or []) if str(a).strip()]
    if want and want != "?" and want.lower() not in allowed:
        allowed = [want.lower(), *allowed]
    prior = strip_reasoning(prior_draft or "").strip() or "(empty draft)"

    fixes: list[str] = []
    det_l = (detected or "").lower()
    if allowed and det_l and det_l in allowed:
        fixes.append(
            f"- Keep ACTION as one of: {', '.join(allowed)} "
            f"(current {det_l} is already acceptable)"
        )
    elif allowed and (not det_l or det_l not in allowed):
        fixes.append(
            f"- ACTION line must be one of: {', '.join(f'ACTION: {a}' for a in allowed)}  "
            f"(you used: {detected or 'none'})"
        )
    elif want and want != "?" and det_l != want.lower():
        fixes.append(
            f"- ACTION line must be exactly: ACTION: {want}  "
            f"(you used: {detected or 'none'})"
        )
    elif want and want != "?":
        fixes.append(f"- Keep ACTION: {want} on its own last line")

    if missing:
        fixes.append(
            "- Include these phrases EXACTLY in the customer message body "
            "(copy/paste these substrings verbatim, case-insensitive ok). "
            "If a fix shows alternatives separated by |, include at least ONE: "
            + ", ".join(repr(m) for m in missing)
        )
        fixes.append(
            "- Do not paraphrase them away — the harness searches for these strings "
            "(or one alternative from an OR-group)."
        )
    if forbidden:
        fixes.append(
            "- Remove / must NOT mention: " + ", ".join(repr(f) for f in forbidden)
        )
        fixes.append("- Do not invent dollar amounts or grant VIP exceptions in text")

    if not fixes:
        details = checklist.get("details") or "evaluation failed"
        fixes.append(f"- Fix evaluation failure: {details}")

    fix_block = "\n".join(fixes)
    return (
        f"\n=== STRUCTURED HEAL #{heal_n} (internal repair — customer never sees this block) ===\n"
        f"Your previous reply failed the harness checklist.\n\n"
        f"PREVIOUS DRAFT:\n---\n{prior}\n---\n\n"
        f"REQUIRED FIXES:\n{fix_block}\n"
        f"- Write ONLY a normal customer-facing ParcelCo support reply.\n"
        f"- NEVER mention heals, retries, checklist, attempts, harness, SLM, or internal failures.\n"
        f"- Do not say things like \"failed after 2 heals\" — the customer must not see that.\n\n"
        f"Rewrite the full customer reply from scratch incorporating every fix.\n"
        f"End with a single line: ACTION: refund|deny|escalate|inform\n"
        f"=== END STRUCTURED HEAL ===\n"
    )

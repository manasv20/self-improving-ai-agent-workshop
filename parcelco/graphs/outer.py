from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timezone

from parcelco import history
from parcelco.data_io import (
    load_tickets,
    read_learnings,
    read_prompt,
    reset_memory_files,
    suite_info,
    write_learnings,
    write_prompt,
)
from parcelco.events import publish
from parcelco.graphs.inner import run_ticket
from parcelco.llm import chat_model
from parcelco.models import RoundRecord, TicketRunResult


def _min_delta() -> float:
    return float(os.getenv("PARCELCO_MIN_DELTA", "0.05"))


def _part_b_tol() -> float:
    return float(os.getenv("PARCELCO_PART_B_TOLERANCE", "0.05"))


def _max_rounds() -> int:
    return int(os.getenv("PARCELCO_MAX_OUTER_ROUNDS", "5"))


def run_suite(
    split: str, *, prompt: str | None = None, learnings: str | None = None
) -> tuple[float, list[TicketRunResult]]:
    tickets = load_tickets(split)
    results: list[TicketRunResult] = []
    for t in tickets:
        publish({"type": "suite_ticket", "split": split, "ticket_id": t.id, "node": "suite"})
        results.append(run_ticket(t, prompt=prompt, learnings=learnings))
    rate = sum(1 for r in results if r.passed) / max(len(results), 1)
    return rate, results


def baseline() -> dict:
    info = suite_info()
    publish(
        {
            "type": "status",
            "status": "baseline",
            "node": "baseline",
            "stack": "langgraph",
            "stack_detail": (
                f"Suite mode={info['mode']}: {info['active_improve']} Part A + "
                f"{info['active_holdout']} Part B "
                f"(catalog {info['catalog_total']})"
            ),
            "suite": info,
        }
    )
    prompt = read_prompt()
    learnings = read_learnings()
    a_rate, a_results = run_suite("improve", prompt=prompt, learnings=learnings)
    b_rate, b_results = run_suite("holdout", prompt=prompt, learnings=learnings)
    record = RoundRecord(
        round=0,
        part_a_rate=a_rate,
        part_b_rate=b_rate,
        kept=True,
        lesson_summary="baseline (no mutation)",
        prompt_version="baseline",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    history.append_round(
        record,
        payload={
            "a_failed": [r.ticket_id for r in a_results if not r.passed],
            "b_failed": [r.ticket_id for r in b_results if not r.passed],
            "kind": "baseline",
        },
    )
    publish(
        {
            "type": "round",
            "round": 0,
            "part_a_rate": a_rate,
            "part_b_rate": b_rate,
            "kept": True,
            "status": "baseline_done",
            "node": "idle",
            "stack_detail": f"Baseline logged — A {a_rate:.0%} / B {b_rate:.0%} (where it was)",
            "before_after": history.before_after(),
        }
    )
    return {
        "round": 0,
        "part_a_rate": a_rate,
        "part_b_rate": b_rate,
        "a_results": [r.model_dump() for r in a_results],
        "b_results": [r.model_dump() for r in b_results],
    }


def _cluster_lessons(failed: list[TicketRunResult]) -> str:
    """Lessons from Part A failures only — never mention holdout ticket ids."""
    if not failed:
        return "No Part A failures this round."

    reasons: list[str] = []
    actions: Counter[str] = Counter()
    for r in failed:
        actions[r.checklist.detected_action or "missing_action"] += 1
        if r.checklist.missing:
            reasons.append(f"Often missing phrases: {', '.join(r.checklist.missing)}")
        if r.checklist.forbidden_hits:
            reasons.append(f"Avoid forbidden phrases: {', '.join(r.checklist.forbidden_hits)}")
        if not r.checklist.action_ok:
            reasons.append("Always end with a correct ACTION: line.")

    uniq: list[str] = []
    for x in reasons:
        if x not in uniq:
            uniq.append(x)

    summary_lines = [
        f"- Seen {len(failed)} Part A failures.",
        f"- Action tag issues / distribution: {dict(actions)}",
    ] + [f"- {u}" for u in uniq[:6]]

    try:
        llm = chat_model(temperature=0.2)
        msg = llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You write short durable support-agent lessons for ParcelCo. "
                        "Never mention specific ticket IDs. Output 3-6 bullet lessons only."
                    ),
                },
                {"role": "user", "content": "Failure patterns:\n" + "\n".join(summary_lines)},
            ]
        )
        return (getattr(msg, "content", None) or str(msg)).strip()
    except Exception:
        return "\n".join(summary_lines)


# Lines that would teach harness jargon or invent fake "system recovery" copy.
_POISON_LESSON = (
    "failed after",
    "after 2 heal",
    "after n heal",
    "mention heal",
    "say heal",
    "heal succeeded",
    "after checklist",
    "automatic recovery",
    "automatically recovered",
    "system recovered",
    "system automatically",
    "internal process",
    "checklist failure",
    "without mentioning the term",
    "harness",
    "heal(",
    " heal",
    "heal,",
    "heals",
)


def _sanitize_lesson_block(block: str) -> str:
    """Drop Reflect lines that would teach the model to leak harness jargon."""
    kept: list[str] = []
    for line in block.splitlines():
        low = line.lower()
        if any(p in low for p in _POISON_LESSON):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _append_learnings(new_block: str, *, heading: str | None = None) -> str:
    cleaned = _sanitize_lesson_block(new_block)
    if not cleaned:
        return read_learnings()
    current = read_learnings().rstrip()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = heading or f"Round lessons ({stamp})"
    updated = current + f"\n\n## {title}\n{cleaned}\n"
    write_learnings(updated)
    return updated


def _first_fail_attempt(result: TicketRunResult) -> dict:
    for a in result.attempts or []:
        if isinstance(a, dict) and not a.get("passed"):
            return a
    return {}


def _lesson_from_single(result: TicketRunResult) -> str:
    """Write durable lessons from one learn-set ticket (no ticket ids)."""
    c = result.checklist
    first_fail = _first_fail_attempt(result)
    expected_action = first_fail.get("expected_action") or c.detected_action or "inform"
    missing = first_fail.get("missing") or list(c.missing or [])
    forbidden = first_fail.get("forbidden_hits") or list(c.forbidden_hits or [])
    detected0 = first_fail.get("detected_action")

    # Mechanical fix: reply was fine but ACTION line missing — no LLM needed.
    if (
        result.passed
        and result.heal_count > 0
        and detected0 in (None, "")
        and not missing
        and not forbidden
    ):
        return (
            f"- Always end every customer reply with a single line "
            f"`ACTION: {expected_action}` (refund|deny|escalate|inform).\n"
            f"- Put the ACTION tag after the customer-facing text, never inside it."
        )

    pattern = [
        f"- Final outcome: {'PASS' if result.passed else 'FAIL'}",
        f"- Expected ACTION tag: {expected_action}",
        f"- First attempt ACTION tag: {detected0 or 'missing'}",
        f"- Missing customer phrases: {', '.join(missing) or 'none'}",
        f"- Forbidden phrase hits: {', '.join(forbidden) or 'none'}",
    ]
    if result.passed and result.heal_count > 0:
        task = (
            "The first reply failed a policy checklist; a rewrite then passed. "
            "Write 2-4 durable bullets so the agent passes on the first try. "
            "Focus on: correct ACTION tag, required customer-visible policy phrases "
            "(e.g. 30-day, transit, 1 business day), and escalate/deny/refund wording. "
            "Never mention ticket IDs. "
            "Do NOT write about heals, retries, checklists, automatic recovery, or internal systems — "
            "those words must never appear in lessons or customer replies."
        )
    elif not result.passed:
        task = (
            "The ticket still failed the policy checklist. Write 3-6 durable corrective bullets. "
            "Focus on correct ACTION tags and required customer-visible policy phrases. "
            "Never mention ticket IDs. "
            "Do NOT invent phrases about failed repairs, heals, retries, or automatic recovery."
        )
    else:
        return ""

    try:
        llm = chat_model(temperature=0.2)
        msg = llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You write short durable ParcelCo support lessons as markdown bullets only. "
                        "Each bullet teaches customer-facing policy language or the ACTION tag format. "
                        "Never mention ticket IDs. "
                        "Never mention heals, retries, checklists, attempts, harnesses, "
                        "automatic recovery, or internal failures."
                    ),
                },
                {"role": "user", "content": task + "\n\nSignals:\n" + "\n".join(pattern)},
            ]
        )
        return (getattr(msg, "content", None) or str(msg)).strip()
    except Exception:
        return (
            f"- Always end replies with `ACTION: {expected_action}`.\n"
            f"- Include required policy phrases when relevant: "
            f"{', '.join(missing) if missing else 'follow retrieved policy/FAQ'}."
        )


def reflect_after_ticket(ticket, result: TicketRunResult) -> dict:
    """Autonomous layer: after a ticket loop, Reflect on learn-set outcomes.

    Holdout never writes lessons. Clean first-try PASSes skip writing.
    Local Qwen → we keep lessons immediately (no suite gate on this path).
    """
    split = getattr(ticket, "split", None) or (ticket.get("split") if isinstance(ticket, dict) else None)
    tid = result.ticket_id

    if split == "holdout":
        publish(
            {
                "type": "step",
                "node": "reflect",
                "stack": "autonomous",
                "stack_detail": f"{tid} is holdout — Reflect skipped (score only, no lessons)",
                "ticket_id": tid,
                "passed": result.passed,
            }
        )
        publish(
            {
                "type": "gate",
                "stack": "autonomous",
                "stack_detail": "Holdout: no memory write",
                "kept": False,
                "ticket_id": tid,
            }
        )
        return {"reflected": False, "reason": "holdout", "lesson": ""}

    if result.passed and int(result.heal_count or 0) == 0:
        publish(
            {
                "type": "step",
                "node": "reflect",
                "stack": "autonomous",
                "stack_detail": f"{tid} clean PASS — Reflect: nothing to learn",
                "ticket_id": tid,
                "passed": True,
            }
        )
        return {"reflected": False, "reason": "clean_pass", "lesson": ""}

    publish(
        {
            "type": "step",
            "node": "reflect",
            "stack": "autonomous",
            "stack_detail": (
                f"Reflect (autonomous): learning from {tid} "
                f"({'PASS after heal' if result.passed else 'FAIL'})"
            ),
            "ticket_id": tid,
            "passed": result.passed,
        }
    )
    publish(
        {
            "type": "status",
            "status": "reflect",
            "node": "reflect",
            "stack": "autonomous",
            "stack_detail": "LLM writing lessons into learnings.md…",
            "ticket_id": tid,
        }
    )

    lesson = _lesson_from_single(result)
    if not lesson:
        return {"reflected": False, "reason": "empty", "lesson": ""}

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    _append_learnings(
        lesson,
        heading=f"Autonomous lesson ({stamp}) · learn-set",
    )
    publish(
        {
            "type": "gate",
            "stack": "autonomous",
            "stack_detail": "KEEP (autonomous online learn — local Qwen)",
            "kept": True,
            "ticket_id": tid,
            "inspector": {"lesson": lesson, "source": "autonomous_reflect", "ticket_id": tid},
        }
    )
    return {"reflected": True, "reason": "learned", "lesson": lesson}


def improve(rounds: int | None = None) -> list[dict]:
    n = rounds if rounds is not None else _max_rounds()
    info = suite_info()
    publish(
        {
            "type": "status",
            "status": "improve",
            "node": "improve",
            "suite": info,
            "stack_detail": (
                f"Improve on suite mode={info['mode']} "
                f"({info['active_improve']}A / {info['active_holdout']}B)"
            ),
        }
    )

    prompt0 = read_prompt()
    learn0 = read_learnings()
    a0, last_a_res = run_suite("improve", prompt=prompt0, learnings=learn0)
    b0, _ = run_suite("holdout", prompt=prompt0, learnings=learn0)
    best_a, best_b = a0, b0
    best_prompt, best_learn = prompt0, learn0

    history.append_round(
        RoundRecord(
            round=0,
            part_a_rate=a0,
            part_b_rate=b0,
            kept=True,
            lesson_summary="improve-run baseline snapshot",
            prompt_version="start",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    publish({"type": "round", "round": 0, "part_a_rate": a0, "part_b_rate": b0, "kept": True})

    rows: list[dict] = [{"round": 0, "part_a_rate": a0, "part_b_rate": b0, "kept": True}]

    for i in range(1, n + 1):
        publish(
            {
                "type": "status",
                "status": f"improve_round_{i}",
                "round": i,
                "node": "reflect",
                "stack": "improve",
                "stack_detail": "Reflect: cluster learn-set failures → write lessons (same loop)",
            }
        )
        failed = [r for r in last_a_res if not r.passed]
        lesson = _cluster_lessons(failed)

        prev_prompt = read_prompt()
        prev_learn = read_learnings()
        new_learn = _append_learnings(lesson)

        if "Always end with ACTION" not in prev_prompt:
            write_prompt(
                prev_prompt.rstrip()
                + "\n\nAlways end with ACTION: refund|deny|escalate|inform on its own line.\n"
                "When denying or approving refunds, mention the 30-day rule.\n"
            )
        cur_prompt = read_prompt()

        publish(
            {
                "type": "status",
                "status": f"improve_round_{i}_eval",
                "round": i,
                "node": "suite",
                "stack": "improve",
                "stack_detail": "Re-score Part A + holdout Part B → keep or revert",
            }
        )
        a_rate, last_a_res = run_suite("improve", prompt=cur_prompt, learnings=new_learn)
        b_rate, _ = run_suite("holdout", prompt=cur_prompt, learnings=new_learn)

        improved = a_rate >= best_a + _min_delta()
        b_ok = b_rate + 1e-9 >= best_b - _part_b_tol()
        kept = bool(improved and b_ok)
        publish(
            {
                "type": "gate",
                "stack": "improve",
                "stack_detail": f"Gate: {'KEEP' if kept else 'REVERT'} (A {a_rate:.0%} / B {b_rate:.0%})",
                "kept": kept,
                "part_a_rate": a_rate,
                "part_b_rate": b_rate,
                "round": i,
            }
        )

        if kept:
            best_a, best_b = a_rate, b_rate
            best_prompt, best_learn = cur_prompt, new_learn
        else:
            write_prompt(prev_prompt)
            write_learnings(prev_learn)

        record = RoundRecord(
            round=i,
            part_a_rate=a_rate,
            part_b_rate=b_rate,
            kept=kept,
            lesson_summary=lesson[:500],
            prompt_version=f"round-{i}-{'kept' if kept else 'reverted'}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        history.append_round(record, payload={"lesson": lesson, "kind": "improve"})
        row = record.model_dump()
        rows.append(row)
        publish(
            {
                "type": "round",
                **row,
                "status": "round_done",
                "node": "idle",
                "stack_detail": (
                    f"Round {i} {'KEPT' if kept else 'REVERTED'} — "
                    f"A {a_rate:.0%} / B {b_rate:.0%} (logged to history)"
                ),
                "before_after": history.before_after(),
            }
        )

        if a_rate >= 0.999:
            break

    write_prompt(best_prompt)
    write_learnings(best_learn)
    publish(
        {
            "type": "status",
            "status": "improve_done",
            "node": "idle",
            "part_a_rate": best_a,
            "part_b_rate": best_b,
            "stack_detail": f"Improve done — now at A {best_a:.0%} / B {best_b:.0%}",
            "before_after": history.before_after(),
        }
    )
    return rows


def reset_all() -> None:
    reset_memory_files()
    history.clear_rounds()
    publish(
        {
            "type": "status",
            "status": "reset",
            "node": "idle",
            "part_a_rate": None,
            "part_b_rate": None,
        }
    )

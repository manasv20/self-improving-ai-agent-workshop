from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from parcelco.models import RoundRecord
from parcelco.paths import MEMORY_DIR, ROUNDS_DB


def _conn() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ROUNDS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round INTEGER NOT NULL,
            part_a_rate REAL NOT NULL,
            part_b_rate REAL NOT NULL,
            kept INTEGER NOT NULL,
            lesson_summary TEXT,
            prompt_version TEXT,
            timestamp TEXT NOT NULL,
            langfuse_url TEXT,
            payload TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            ticket_id TEXT,
            status TEXT,
            detail TEXT,
            passed INTEGER,
            round INTEGER,
            part_a_rate REAL,
            part_b_rate REAL,
            kept INTEGER,
            payload TEXT
        )
        """
    )
    conn.commit()
    return conn


def append_round(record: RoundRecord, payload: dict[str, Any] | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO rounds
            (round, part_a_rate, part_b_rate, kept, lesson_summary, prompt_version, timestamp, langfuse_url, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.round,
                record.part_a_rate,
                record.part_b_rate,
                1 if record.kept else 0,
                record.lesson_summary,
                record.prompt_version,
                record.timestamp or datetime.now(timezone.utc).isoformat(),
                record.langfuse_url,
                json.dumps(payload or {}),
            ),
        )
        conn.commit()


def list_rounds() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM rounds ORDER BY id ASC").fetchall()
    out: list[dict[str, Any]] = []
    prev_a: float | None = None
    prev_b: float | None = None
    for r in rows:
        payload: dict[str, Any] = {}
        try:
            payload = json.loads(r["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        a = r["part_a_rate"]
        b = r["part_b_rate"]
        row = {
            "id": r["id"],
            "round": r["round"],
            "part_a_rate": a,
            "part_b_rate": b,
            "kept": bool(r["kept"]),
            "lesson_summary": r["lesson_summary"] or "",
            "prompt_version": r["prompt_version"] or "",
            "timestamp": r["timestamp"],
            "langfuse_url": r["langfuse_url"],
            "payload": payload,
            "delta_a": None if prev_a is None else a - prev_a,
            "delta_b": None if prev_b is None else b - prev_b,
        }
        out.append(row)
        prev_a, prev_b = a, b
    return out


def append_event(event: dict[str, Any]) -> None:
    """Persist meaningful dashboard events for the full session history."""
    kind = event.get("type") or event.get("status") or "event"
    if kind in {"ping", "snapshot", "suite_ticket"}:
        return
    # Keep heal steps; drop routine retrieve/generate chatter during bulk suite
    if kind == "step" and event.get("node") != "heal":
        return
    detail = (
        event.get("stack_detail")
        or event.get("message")
        or event.get("lesson_summary")
        or event.get("status")
        or ""
    )
    if kind == "ticket_eval":
        ticket = event.get("ticket_id") or "?"
        passed = event.get("passed")
        detail = f"{ticket} → {'PASS' if passed else 'FAIL'}"
        if event.get("inspector") and isinstance(event["inspector"], dict):
            cl = (event["inspector"].get("checklist") or {}).get("details")
            if cl and not passed:
                detail = f"{detail} · {cl}"[:400]
    if isinstance(detail, str) and len(detail) > 400:
        detail = detail[:400] + "…"

    payload = {
        k: v
        for k, v in event.items()
        if k not in {"type", "stack_detail", "message", "inspector", "suite"}
        and not isinstance(v, (dict, list))
    }

    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO event_log
            (ts, kind, ticket_id, status, detail, passed, round, part_a_rate, part_b_rate, kept, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                str(kind),
                event.get("ticket_id"),
                event.get("status"),
                detail,
                None if event.get("passed") is None else (1 if event.get("passed") else 0),
                event.get("round"),
                event.get("part_a_rate"),
                event.get("part_b_rate"),
                None if event.get("kept") is None else (1 if event.get("kept") else 0),
                json.dumps(payload),
            ),
        )
        conn.execute(
            """
            DELETE FROM event_log WHERE id NOT IN (
                SELECT id FROM event_log ORDER BY id DESC LIMIT 800
            )
            """
        )
        conn.commit()


def list_events(limit: int = 200) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM event_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(r["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        out.append(
            {
                "id": r["id"],
                "ts": r["ts"],
                "kind": r["kind"],
                "ticket_id": r["ticket_id"],
                "status": r["status"],
                "detail": r["detail"] or "",
                "passed": None if r["passed"] is None else bool(r["passed"]),
                "round": r["round"],
                "part_a_rate": r["part_a_rate"],
                "part_b_rate": r["part_b_rate"],
                "kept": None if r["kept"] is None else bool(r["kept"]),
                "payload": payload,
            }
        )
    return out  # newest first


def clear_rounds() -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM rounds")
        conn.execute("DELETE FROM event_log")
        conn.commit()


def latest_scores() -> dict[str, float] | None:
    rounds = list_rounds()
    if not rounds:
        return None
    last = rounds[-1]
    return {"part_a_rate": last["part_a_rate"], "part_b_rate": last["part_b_rate"]}


def before_after() -> dict[str, Any] | None:
    """First recorded scores vs latest kept round — the improvement story."""
    rounds = list_rounds()
    if not rounds:
        return None
    before = rounds[0]
    kept = [r for r in rounds if r["kept"]]
    after = kept[-1] if kept else rounds[-1]
    return {
        "before": {
            "round": before["round"],
            "part_a_rate": before["part_a_rate"],
            "part_b_rate": before["part_b_rate"],
            "prompt_version": before.get("prompt_version") or "",
            "timestamp": before.get("timestamp"),
            "lesson_summary": before.get("lesson_summary") or "",
        },
        "after": {
            "round": after["round"],
            "part_a_rate": after["part_a_rate"],
            "part_b_rate": after["part_b_rate"],
            "prompt_version": after.get("prompt_version") or "",
            "timestamp": after.get("timestamp"),
            "lesson_summary": after.get("lesson_summary") or "",
        },
        "delta_a": after["part_a_rate"] - before["part_a_rate"],
        "delta_b": after["part_b_rate"] - before["part_b_rate"],
        "rounds": len(rounds),
        "kept_count": sum(1 for r in rounds if r["kept"]),
        "reverted_count": sum(1 for r in rounds if not r["kept"]),
        "why": _why_improved(before, after, kept),
    }


def _why_improved(before: dict, after: dict, kept: list[dict]) -> str:
    """Human-readable reason for lift (or lack of it) for the dashboard."""
    da = after["part_a_rate"] - before["part_a_rate"]
    db = after["part_b_rate"] - before["part_b_rate"]
    lesson = (after.get("lesson_summary") or "").strip()
    if after["round"] == before["round"] and len(kept) <= 1:
        return (
            "Baseline only so far — run Learn so Reflect writes lessons; "
            "lift appears when a round is kept."
        )
    bits = [
        f"Learn set {before['part_a_rate']:.0%} → {after['part_a_rate']:.0%} ({da:+.0%})",
        f"Holdout {before['part_b_rate']:.0%} → {after['part_b_rate']:.0%} ({db:+.0%})",
    ]
    if lesson and not lesson.startswith(("baseline", "improve-run")):
        bits.append(f"Kept lessons: {lesson[:400]}")
    elif da > 0.01:
        bits.append("Lift came from gated prompt / learnings.md changes that held on holdout.")
    elif da <= 0.01 and db <= 0.01:
        bits.append("No material lift yet — Reflect lessons may have been reverted by the gate.")
    return " · ".join(bits)


def journey() -> list[dict[str, Any]]:
    """Ordered milestones for the where-it-was → where-it-is timeline."""
    rounds = list_rounds()
    if not rounds:
        return []
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rounds):
        label = "Where it was" if i == 0 else ("Where it is now" if i == len(rounds) - 1 else f"Round {r['round']}")
        if i == 0 and (r.get("prompt_version") or "").startswith(("baseline", "start")):
            label = "Where it was"
        elif i == len(rounds) - 1:
            label = "Where it is now"
        out.append(
            {
                "label": label,
                "round": r["round"],
                "part_a_rate": r["part_a_rate"],
                "part_b_rate": r["part_b_rate"],
                "kept": r["kept"],
                "delta_a": r.get("delta_a"),
                "delta_b": r.get("delta_b"),
                "prompt_version": r.get("prompt_version") or "",
                "lesson_summary": r.get("lesson_summary") or "",
                "timestamp": r.get("timestamp"),
                "is_start": i == 0,
                "is_now": i == len(rounds) - 1,
            }
        )
    return out

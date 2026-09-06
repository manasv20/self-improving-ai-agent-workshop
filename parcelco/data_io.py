from __future__ import annotations

import json
import os

from parcelco.models import Expected, Ticket
from parcelco.paths import EXPECTED_DIR, LEARNINGS_PATH, PROMPT_PATH, TICKETS_DIR


def suite_mode() -> str:
    """demo = core 35 tickets (fast live); full = all ~1000 (before→after proof)."""
    mode = (os.getenv("PARCELCO_SUITE", "full") or "full").strip().lower()
    return "demo" if mode in {"demo", "core", "live"} else "full"


def load_tickets(split: str | None = None, *, respect_suite: bool = True) -> list[Ticket]:
    path = TICKETS_DIR / "all.jsonl"
    demo = suite_mode() == "demo"
    tickets: list[Ticket] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        t = Ticket.model_validate(json.loads(line))
        if respect_suite and demo and t.tier != "core":
            continue
        if split is None or t.split == split:
            tickets.append(t)
    return tickets


def suite_info() -> dict[str, int | str]:
    all_t = load_tickets(split=None, respect_suite=False)
    active = load_tickets(split=None, respect_suite=True)
    return {
        "mode": suite_mode(),
        "active_total": len(active),
        "active_improve": sum(1 for t in active if t.split == "improve"),
        "active_holdout": sum(1 for t in active if t.split == "holdout"),
        "catalog_total": len(all_t),
        "catalog_improve": sum(1 for t in all_t if t.split == "improve"),
        "catalog_holdout": sum(1 for t in all_t if t.split == "holdout"),
    }


def load_expected(ticket_id: str) -> Expected:
    path = EXPECTED_DIR / f"{ticket_id}.json"
    return Expected.model_validate_json(path.read_text())


def read_prompt() -> str:
    return PROMPT_PATH.read_text()


def write_prompt(text: str) -> None:
    PROMPT_PATH.write_text(text)


def read_learnings() -> str:
    if not LEARNINGS_PATH.exists():
        return ""
    return LEARNINGS_PATH.read_text()


def write_learnings(text: str) -> None:
    LEARNINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEARNINGS_PATH.write_text(text)


BASELINE_PROMPT = """You are a ParcelCo customer support agent speaking to a customer.

Follow the ParcelCo policy and retrieved FAQ excerpts exactly.
Decide one action tag at the end of your reply on its own line:
ACTION: refund | deny | escalate | inform

Rules:
- Cite the 30-day refund window when approving or denying refunds.
- Do not invent VIP exceptions.
- Do not invent refund dollar amounts.
- Be brief and specific.
- Write only what the customer should read.
- NEVER mention heals, retries, checklists, attempts, harnesses, lessons files, or internal failures.
"""

BASELINE_LEARNINGS = """# Learned lessons (updated by the outer improve loop)

(none yet)

## Standing rules
- Customer replies must stay customer-facing: never mention heals, retries, or checklist failures.
- When escalating: acknowledge the issue, say a specialist will follow up within 1 business day, include required policy phrases (e.g. 30-day when relevant), end with ACTION: escalate.
- Always end every reply with a single line: ACTION: refund|deny|escalate|inform.
"""


def reset_memory_files() -> None:
    write_prompt(BASELINE_PROMPT.strip() + "\n")
    write_learnings(BASELINE_LEARNINGS.strip() + "\n")

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Ticket(BaseModel):
    id: str
    message: str
    intent: str = "general"
    split: Literal["improve", "holdout"] = "improve"
    tier: Literal["core", "full"] = "full"
    meta: dict[str, Any] = Field(default_factory=dict)


class Expected(BaseModel):
    ticket_id: str
    must_include: list[str] = Field(default_factory=list)
    # Each inner list is an OR-group: at least one phrase from the group must appear.
    # Lets non-deterministic paraphrases still pass hard policy gates.
    must_include_any: list[list[str]] = Field(default_factory=list)
    must_not: list[str] = Field(default_factory=list)
    action: Literal["refund", "deny", "escalate", "inform"] = "inform"
    # When set, any of these ACTION tags pass (primary `action` is always included).
    # Use for tickets like "what are my options?" where inform listing choices is valid
    # even if the preferred disposition is refund/deny/escalate.
    acceptable_actions: list[Literal["refund", "deny", "escalate", "inform"]] = Field(
        default_factory=list
    )
    notes: str = ""
    # Optional tag for UI / suite filters
    difficulty: Literal["easy", "ambiguous", "adversarial"] = "easy"


class ChecklistResult(BaseModel):
    passed: bool
    action_ok: bool
    missing: list[str] = Field(default_factory=list)
    forbidden_hits: list[str] = Field(default_factory=list)
    detected_action: str | None = None
    score: float = 0.0
    details: str = ""


class TicketRunResult(BaseModel):
    ticket_id: str
    split: str
    draft: str
    passed: bool
    checklist: ChecklistResult
    heal_count: int = 0
    retrieved: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    attempts: list[dict[str, Any]] = Field(default_factory=list)
    trace_id: str | None = None
    langfuse_evidence: dict[str, Any] = Field(default_factory=dict)
    slm_judge: dict[str, Any] = Field(default_factory=dict)


class RoundRecord(BaseModel):
    round: int
    part_a_rate: float
    part_b_rate: float
    kept: bool
    lesson_summary: str = ""
    prompt_version: str = ""
    timestamp: str = ""
    langfuse_url: str | None = None

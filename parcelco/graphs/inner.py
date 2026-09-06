from __future__ import annotations

import os
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from parcelco.data_io import load_expected, read_learnings, read_prompt
from parcelco.eval.checklist import score_draft
from parcelco.events import publish
from parcelco.heal import build_heal_repair_brief
from parcelco.llm import chat_model
from parcelco.models import ChecklistResult, Ticket, TicketRunResult
from parcelco.rag import retrieve


class InnerState(TypedDict, total=False):
    ticket: dict[str, Any]
    docs: list[str]
    draft: str
    checklist: dict[str, Any]
    heal_count: int
    steps: list[str]
    learnings: str
    prompt: str
    passed: bool
    trace_id: str
    langfuse_url: str
    attempts: list[dict[str, Any]]


def _max_heal() -> int:
    return int(os.getenv("PARCELCO_MAX_HEAL", "2"))


def node_retrieve(state: InnerState) -> InnerState:
    ticket = state["ticket"]
    publish(
        {
            "type": "step",
            "node": "retrieve",
            "stack": "langchain",
            "stack_detail": "LangChain retriever → FAQ/policy context",
            "ticket_id": ticket["id"],
        }
    )
    docs = retrieve(ticket["message"], k=4)
    steps = list(state.get("steps") or []) + ["retrieve"]
    return {**state, "docs": docs, "steps": steps}


def node_generate(state: InnerState) -> InnerState:
    from parcelco.tracing import (
        create_trace_id,
        flush,
        get_callbacks,
        langfuse_enabled,
        remember_trace,
        trace_url,
    )

    ticket = state["ticket"]
    publish(
        {
            "type": "step",
            "node": "generate",
            "stack": "langchain",
            "stack_detail": "LangChain ChatOpenAI → local Qwen (LM Studio)",
            "ticket_id": ticket["id"],
        }
    )
    prompt = state.get("prompt") or read_prompt()
    learnings = state.get("learnings") or read_learnings()
    docs = "\n\n---\n\n".join(state.get("docs") or [])
    heal_hint = ""
    checklist = state.get("checklist") or {}
    heal_n = int(state.get("heal_count") or 0)
    if heal_n > 0 and checklist:
        expected_action = None
        try:
            expected_action = load_expected(ticket["id"]).action
        except Exception:
            expected_action = None
        heal_hint = build_heal_repair_brief(
            checklist=checklist,
            prior_draft=state.get("draft") or "",
            expected_action=expected_action,
            heal_n=heal_n,
        )
        publish(
            {
                "type": "step",
                "node": "generate",
                "stack": "heal",
                "stack_detail": f"Structured heal #{heal_n}: rewriting with prior draft + fix list",
                "ticket_id": ticket["id"],
                "heal_count": heal_n,
            }
        )
    user = (
        f"Customer ticket ({ticket['id']}):\n{ticket['message']}\n\n"
        f"Retrieved policy/FAQ:\n{docs}\n\n"
        f"Learned lessons:\n{learnings}\n"
        f"{heal_hint}"
        "Write the support reply now."
    )
    publish(
        {
            "type": "step",
            "node": "generate",
            "stack": "langgraph",
            "stack_detail": "LangGraph node 'generate' invoking LangChain→Qwen",
            "ticket_id": ticket["id"],
        }
    )

    trace_id = state.get("trace_id") or create_trace_id()
    callbacks = get_callbacks(trace_id=trace_id) if langfuse_enabled() else []
    lf_url = trace_url(trace_id) if trace_id else None
    if callbacks:
        publish(
            {
                "type": "step",
                "node": "generate",
                "stack": "langfuse",
                "stack_detail": "LangFuse tracing this generation",
                "ticket_id": ticket["id"],
                "langfuse_on": True,
                "langfuse_url": lf_url,
                "trace_id": trace_id,
            }
        )

    llm = chat_model(temperature=0.1)
    msg = llm.invoke(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
        config={"callbacks": callbacks} if callbacks else {},
    )
    if callbacks:
        flush()
        if trace_id:
            remember_trace(ticket_id=ticket["id"], trace_id=trace_id, detail="generation")
            lf_url = trace_url(trace_id) or lf_url

    draft = getattr(msg, "content", None) or str(msg)
    steps = list(state.get("steps") or []) + ["generate"]
    return {
        **state,
        "draft": draft,
        "steps": steps,
        "prompt": prompt,
        "learnings": learnings,
        "trace_id": trace_id or "",
        "langfuse_url": lf_url or "",
    }


def node_evaluate(state: InnerState) -> InnerState:
    from parcelco.tracing import langfuse_enabled, remember_trace, score_checklist_to_langfuse

    ticket = state["ticket"]
    publish(
        {
            "type": "step",
            "node": "evaluate",
            "stack": "evaluator",
            "stack_detail": "Deterministic checklist (not LLM self-grade)",
            "ticket_id": ticket["id"],
        }
    )
    expected = load_expected(ticket["id"])
    result = score_draft(state.get("draft") or "", expected)
    steps = list(state.get("steps") or []) + ["evaluate"]
    trace_id = state.get("trace_id") or None
    lf_url = state.get("langfuse_url") or None
    attempts = list(state.get("attempts") or [])
    attempt_no = len(attempts) + 1
    heal_before = int(state.get("heal_count") or 0)
    attempt = {
        "attempt": attempt_no,
        "heal_count_before": heal_before,
        "passed": result.passed,
        "detected_action": result.detected_action,
        "expected_action": expected.action,
        "missing": result.missing,
        "forbidden_hits": result.forbidden_hits,
        "details": result.details,
        "draft": state.get("draft") or "",
    }
    attempts.append(attempt)

    if trace_id:
        score_checklist_to_langfuse(
            trace_id,
            passed=result.passed,
            details=result.details,
            heal_count=heal_before,
            attempt=attempt_no,
            missing=result.missing,
            detected_action=result.detected_action,
            expected_action=expected.action,
        )
        lf_url = remember_trace(
            ticket_id=ticket["id"],
            trace_id=trace_id,
            passed=result.passed,
            detail=result.details,
        ) or lf_url

    will_heal = (not result.passed) and heal_before < _max_heal()
    publish(
        {
            "type": "ticket_eval",
            "ticket_id": ticket["id"],
            "passed": result.passed,
            "node": "evaluate",
            "stack": "langfuse" if langfuse_enabled() else "evaluator",
            "stack_detail": (
                f"Attempt {attempt_no}: {'PASS' if result.passed else 'FAIL'}"
                + (f" · will heal ({result.details})" if will_heal else "")
                + (f" · {result.details}" if (not result.passed and not will_heal) else "")
                + (" · scored → LangFuse" if trace_id else "")
            )[:400],
            "langfuse_on": langfuse_enabled(),
            "langfuse_url": lf_url,
            "trace_id": trace_id,
            "attempt": attempt,
            "attempts": attempts,
            "will_heal": will_heal,
            "inspector": {
                "ticket_id": ticket["id"],
                "draft": state.get("draft"),
                "checklist": result.model_dump(),
                "retrieved": state.get("docs") or [],
                "langfuse_url": lf_url,
                "trace_id": trace_id,
                "heal_count": heal_before,
                "attempts": attempts,
                "stack_path": [
                    "LangChain retrieve",
                    "LangChain generate (Qwen)",
                    "LangGraph evaluate",
                    "LangFuse scores" if langfuse_enabled() else "LangFuse (off)",
                ],
            },
        }
    )
    return {
        **state,
        "checklist": result.model_dump(),
        "passed": result.passed,
        "steps": steps,
        "langfuse_url": lf_url or "",
        "attempts": attempts,
    }


def node_heal(state: InnerState) -> InnerState:
    ticket = state["ticket"]
    checklist = state.get("checklist") or {}
    heal_n = int(state.get("heal_count") or 0) + 1
    detail = checklist.get("details") or "checklist failed"
    expected_action = None
    try:
        expected_action = load_expected(ticket["id"]).action
    except Exception:
        expected_action = None
    repair = build_heal_repair_brief(
        checklist=checklist,
        prior_draft=state.get("draft") or "",
        expected_action=expected_action,
        heal_n=heal_n,
    )
    missing = checklist.get("missing") or []
    forbidden = checklist.get("forbidden_hits") or []
    publish(
        {
            "type": "step",
            "node": "heal",
            "stack": "langgraph",
            "stack_detail": (
                f"Structured heal #{heal_n}: {detail}"
                + (f" · fix include={missing}" if missing else "")
                + (f" · remove={forbidden}" if forbidden else "")
            )[:400],
            "ticket_id": ticket["id"],
            "heal_count": heal_n,
            "checklist": checklist,
            "attempt_summary": {
                "heal": heal_n,
                "reason": detail,
                "missing": missing,
                "forbidden_hits": forbidden,
                "detected_action": checklist.get("detected_action"),
                "expected_action": expected_action,
                "repair_brief": repair[:800],
            },
        }
    )
    steps = list(state.get("steps") or []) + ["heal"]
    return {**state, "heal_count": heal_n, "steps": steps}


def _should_heal(state: InnerState) -> str:
    if state.get("passed"):
        return "end"
    if int(state.get("heal_count") or 0) >= _max_heal():
        return "end"
    return "heal"


def build_inner_graph():
    g = StateGraph(InnerState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", node_generate)
    g.add_node("evaluate", node_evaluate)
    g.add_node("heal", node_heal)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "evaluate")
    g.add_conditional_edges("evaluate", _should_heal, {"heal": "heal", "end": END})
    g.add_edge("heal", "retrieve")
    return g.compile()


_GRAPH = None


def get_inner_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_inner_graph()
    return _GRAPH


def run_ticket(ticket: Ticket, *, prompt: str | None = None, learnings: str | None = None) -> TicketRunResult:
    from parcelco.tracing import create_trace_id, flush, verify_run_against_langfuse

    graph = get_inner_graph()
    init: InnerState = {
        "ticket": ticket.model_dump(),
        "docs": [],
        "draft": "",
        "checklist": {},
        "heal_count": 0,
        "steps": [],
        "attempts": [],
        "learnings": learnings if learnings is not None else read_learnings(),
        "prompt": prompt if prompt is not None else read_prompt(),
        "passed": False,
        "trace_id": create_trace_id() or "",
        "langfuse_url": "",
    }
    final = graph.invoke(init)
    checklist = ChecklistResult.model_validate(
        final.get("checklist") or score_draft("", load_expected(ticket.id)).model_dump()
    )
    heal_count = int(final.get("heal_count") or 0)
    passed = bool(final.get("passed"))
    trace_id = final.get("trace_id") or None
    flush()
    evidence = verify_run_against_langfuse(
        trace_id,
        heal_count=heal_count,
        passed=passed,
    )
    publish(
        {
            "type": "step",
            "node": "evaluate",
            "stack": "langfuse",
            "stack_detail": evidence.get("detail") or "LangFuse verify skipped",
            "ticket_id": ticket.id,
            "passed": passed,
            "trace_id": trace_id,
            "langfuse_url": evidence.get("url"),
            "langfuse_evidence": evidence,
            "inspector": {"langfuse_evidence": evidence, "trace_id": trace_id},
        }
    )
    result = TicketRunResult(
        ticket_id=ticket.id,
        split=ticket.split,
        draft=final.get("draft") or "",
        passed=passed,
        checklist=checklist,
        heal_count=heal_count,
        retrieved=list(final.get("docs") or []),
        steps=list(final.get("steps") or []) + (["langfuse_verify"] if evidence.get("enabled") else []),
        attempts=list(final.get("attempts") or []),
        trace_id=trace_id,
        langfuse_evidence=evidence,
    )
    return result

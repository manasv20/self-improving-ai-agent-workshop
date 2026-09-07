from __future__ import annotations

import os
import threading

from flask import Flask, Response, jsonify, render_template, request

from parcelco import history
from parcelco.events import publish, snapshot, sse_stream, subscribe, unsubscribe
from parcelco.graphs import outer
from parcelco.llm import llm_base_url, model_name
from parcelco.paths import PKG

_TEMPLATES = PKG / "templates"
_STATIC = PKG / "static"

app = Flask(
    __name__,
    template_folder=str(_TEMPLATES),
    static_folder=str(_STATIC),
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "workshop-dev-secret")

_job_lock = threading.Lock()
_job_running = False


def _start_job(fn, *args, **kwargs) -> bool:
    global _job_running
    with _job_lock:
        if _job_running:
            return False
        _job_running = True

    def runner():
        global _job_running
        try:
            fn(*args, **kwargs)
        except Exception as e:
            publish({"type": "error", "status": "error", "message": str(e), "node": "idle"})
        finally:
            with _job_lock:
                _job_running = False

    threading.Thread(target=runner, daemon=True).start()
    return True


@app.get("/")
def index():
    from parcelco.data_io import suite_info
    from parcelco import tracing

    info = suite_info()
    return render_template(
        "dashboard.html",
        model=model_name(),
        base_url=llm_base_url(),
        suite=info,
        langfuse=tracing.status(),
    )


@app.get("/api/knowledge")
def api_knowledge():
    """Everything the harness uses: policy, FAQ, memory, stack, split definitions."""
    from parcelco.data_io import read_learnings, read_prompt, suite_info
    from parcelco.paths import FAQ_DIR, POLICY_PATH
    from parcelco import tracing

    faqs = []
    for path in sorted(FAQ_DIR.glob("*.md")):
        faqs.append({"name": path.name, "text": path.read_text()})
    policy = POLICY_PATH.read_text() if POLICY_PATH.exists() else ""
    info = suite_info()
    return jsonify(
        {
            "stack": [
                {"id": "qwen", "name": "Qwen 3.5 4B (LM Studio)", "role": "Writes the reply", "detail": model_name()},
                {"id": "langchain", "name": "LangChain", "role": "Model I/O + RAG glue", "detail": llm_base_url()},
                {"id": "langgraph", "name": "LangGraph", "role": "Autonomous loop: retrieve→generate→evaluate→heal→reflect", "detail": "Reflect learns from corrected learn-set runs; suite scores lift"},
                {"id": "rag", "name": "RAG (policy + FAQ)", "role": "Frozen knowledge retrieve — not retrained", "detail": "Chroma or keyword fallback"},
                {"id": "checklist", "name": "Python checklist", "role": "Hard pass/fail gate (not LLM self-grade)", "detail": "expected/*.json"},
                {
                    "id": "slm-judge",
                    "name": "Eval SLM",
                    "role": "Eval gate when PARCELCO_EVAL_MODEL is set (Python Expected = rubric)",
                    "detail": os.getenv("PARCELCO_EVAL_MODEL") or "off — checklist-only gate",
                },
                {"id": "memory", "name": "Prompt + learnings.md", "role": "What Reflect updates (gated keep/revert)", "detail": "parcelco/memory/"},
                {"id": "langfuse", "name": "LangFuse", "role": "Score store + heal workflow verify + lesson annotate", "detail": tracing.status().get("label")},
                {"id": "data", "name": "Labeled tickets", "role": "Learn set + holdout", "detail": f"{info['catalog_improve']} learn / {info['catalog_holdout']} holdout"},
            ],
            "splits": {
                "learn_set": {
                    "name": "Learn set (Part A)",
                    "split": "improve",
                    "count_active": info["active_improve"],
                    "count_catalog": info["catalog_improve"],
                    "used_for": "Run the loop; failures feed Reflect / lessons",
                    "not_used_for": "—",
                },
                "holdout": {
                    "name": "Holdout (Part B)",
                    "split": "holdout",
                    "count_active": info["active_holdout"],
                    "count_catalog": info["catalog_holdout"],
                    "used_for": "Score only — prove we generalized",
                    "not_used_for": "Never write holdout ticket ids into lessons",
                },
                "rag_note": "RAG indexes policy.md + faq/*.md once. We do NOT retrain or fine-tune RAG/embeddings when the loop learns — only prompt/learnings change.",
            },
            "policy": {"name": "policy.md", "text": policy},
            "faqs": faqs,
            "prompt": read_prompt(),
            "learnings": read_learnings(),
            "suite": info,
        }
    )


@app.get("/api/state")
def api_state():
    from parcelco.data_io import suite_info
    from parcelco import tracing

    return jsonify(
        {
            "snapshot": snapshot(),
            "history": history.list_rounds(),
            "before_after": history.before_after(),
            "journey": history.journey(),
            "events": history.list_events(250),
            "suite": suite_info(),
            "langfuse": tracing.status(),
            "busy": _job_running,
        }
    )


@app.get("/api/langfuse")
def api_langfuse():
    from parcelco import tracing

    return jsonify(tracing.status())


@app.get("/api/history")
def api_history():
    return jsonify(
        {
            "rounds": history.list_rounds(),
            "before_after": history.before_after(),
            "journey": history.journey(),
            "events": history.list_events(250),
        }
    )


@app.get("/api/events")
def api_events():
    q = subscribe()

    def gen():
        try:
            yield from sse_stream(q)
        finally:
            unsubscribe(q)

    return Response(gen(), mimetype="text/event-stream")


@app.post("/api/suite")
def api_set_suite():
    """Switch active catalog: demo (47 core tickets) or full (1000 tickets)."""
    data = request.get_json(silent=True) or {}
    mode = (data.get("mode") or "").strip().lower()
    if mode not in {"demo", "full"}:
        return jsonify({"ok": False, "error": "mode must be demo|full"}), 400
    os.environ["PARCELCO_SUITE"] = mode
    from parcelco.data_io import suite_info

    info = suite_info()
    publish(
        {
            "type": "status",
            "status": "suite_mode",
            "stack_detail": (
                f"Suite → {info['mode']}: {info['active_total']} active "
                f"({info['active_improve']}A / {info['active_holdout']}B) "
                f"of {info['catalog_total']} catalog"
            ),
            "suite": info,
            "node": "idle",
        }
    )
    return jsonify({"ok": True, "suite": info})


@app.get("/api/tickets")
def api_tickets():
    from parcelco.data_io import load_expected, load_tickets, suite_info

    q = (request.args.get("q") or "").strip().lower()
    split = request.args.get("split")  # improve | holdout | empty=all
    tickets = load_tickets(split if split in {"improve", "holdout"} else None)
    out = []
    for t in tickets:
        if q and q not in t.id.lower() and q not in t.message.lower() and q not in t.intent.lower():
            continue
        try:
            exp = load_expected(t.id)
            action = exp.action
            notes = exp.notes
            difficulty = getattr(exp, "difficulty", None) or "easy"
        except Exception:
            action, notes, difficulty = None, "", "easy"
        out.append(
            {
                "id": t.id,
                "message": t.message,
                "intent": t.intent,
                "split": t.split,
                "tier": t.tier,
                "action": action,
                "notes": notes,
                "difficulty": difficulty,
                "preview": t.message[:110] + ("…" if len(t.message) > 110 else ""),
            }
        )
    return jsonify({"tickets": out, "suite": suite_info(), "count": len(out)})


@app.get("/api/tickets/<ticket_id>")
def api_ticket_detail(ticket_id: str):
    from parcelco.data_io import load_expected, load_tickets

    tickets = {t.id: t for t in load_tickets(None)}
    t = tickets.get(ticket_id)
    if not t:
        return jsonify({"error": "not found"}), 404
    try:
        exp = load_expected(t.id).model_dump()
    except Exception:
        exp = None
    return jsonify({"ticket": t.model_dump(), "expected": exp})


def _ticket_result_detail(result, reflected: dict, *, trace_available: bool) -> str:
    """Describe this run only; never imply a memory write or trace that did not happen."""
    reason = reflected.get("reason")
    detail = f"Ticket {result.ticket_id}: {'PASS' if result.passed else 'FAIL'} after {result.heal_count} heal(s)"
    if reason == "learned":
        detail += " · Reflect wrote a lesson to learnings.md"
    elif reason == "holdout":
        detail += " · holdout: Reflect skipped; memory unchanged"
    elif reason == "clean_pass":
        detail += " · clean PASS: nothing to learn; memory unchanged"
    elif reason == "blocked":
        detail += " · Reflect lesson blocked by safety filter; memory unchanged"
    elif reason == "rejected":
        detail += " · Reflect produced no safe lesson; memory unchanged"
    else:
        detail += " · memory unchanged"

    evidence = result.langfuse_evidence or {}
    if not evidence.get("enabled"):
        detail += " · LangFuse off: no trace written"
    elif not result.trace_id:
        detail += " · LangFuse on, but no trace was captured"
    elif evidence.get("error"):
        detail += " · LangFuse verification unavailable"
    elif trace_available:
        detail += " · LangFuse trace available"
    return detail


def _publish_ticket_result(ticket, result, reflected: dict | None = None) -> None:
    from parcelco.tracing import trace_url

    reflected = reflected or {}
    learned = bool(reflected.get("reflected"))
    ev = result.langfuse_evidence or {}
    trace_available = bool(result.trace_id and ev.get("enabled") and not ev.get("error"))
    lf_url = (ev.get("url") or trace_url(result.trace_id)) if trace_available else None
    detail = _ticket_result_detail(result, reflected, trace_available=trace_available)
    if ev.get("verdict"):
        detail += f" · LF {ev.get('verdict')}"
        if ev.get("generation_count") is not None:
            detail += f" ({ev.get('generation_count')} gen)"

    inspector = {
        "ticket_id": result.ticket_id,
        "message": ticket.message,
        "passed": result.passed,
        "draft": result.draft,
        "checklist": result.checklist.model_dump(),
        "slm_judge": getattr(result, "slm_judge", None) or {},
        "retrieved": result.retrieved,
        "steps": result.steps,
        "heal_count": result.heal_count,
        "attempts": result.attempts,
        "langfuse_url": lf_url,
        "trace_id": result.trace_id,
        "langfuse_evidence": result.langfuse_evidence or reflected.get("langfuse_evidence") or {},
        "autonomous": reflected,
    }
    if reflected.get("lesson"):
        inspector["autonomous_lesson"] = reflected["lesson"]

    publish(
        {
            "type": "status",
            "status": "demo_done",
            "stack": "autonomous" if learned else ("langfuse" if lf_url else "evaluator"),
            "stack_detail": detail,
            "ticket_id": result.ticket_id,
            "node": "reflect" if learned else "idle",
            "passed": result.passed,
            "reflect_reason": reflected.get("reason"),
            "langfuse_on": bool(ev.get("enabled")),
            "trace_available": trace_available,
            "langfuse_url": lf_url,
            "trace_id": result.trace_id,
            "inspector": inspector,
            "attempts": result.attempts,
            "heal_count": result.heal_count,
        }
    )


@app.post("/api/run-ticket")
def api_run_ticket():
    """Run a selected ticket through the inner graph + autonomous Reflect."""
    data = request.get_json(silent=True) or {}
    ticket_id = (data.get("ticket_id") or "").strip()
    if not ticket_id:
        return jsonify({"ok": False, "error": "ticket_id is required"}), 400

    from parcelco.data_io import load_tickets

    tickets = {t.id: t for t in load_tickets(None)}
    ticket = tickets.get(ticket_id)
    if ticket is None:
        return jsonify({"ok": False, "error": f"ticket {ticket_id} is not in the active suite"}), 404

    def job():
        from parcelco.graphs.inner import run_ticket
        from parcelco.graphs.outer import reflect_after_ticket

        publish(
            {
                "type": "status",
                "status": "demo",
                "stack": "langgraph",
                "stack_detail": (
                    f"Running {ticket.id}: retrieve → generate → evaluate → heal"
                    + (" → Reflect" if ticket.split == "improve" else " (holdout: no Reflect)")
                ),
                "node": "retrieve",
                "ticket_id": ticket.id,
            }
        )
        result = run_ticket(ticket)
        reflected = reflect_after_ticket(ticket, result)
        _publish_ticket_result(ticket, result, reflected)

    if not _start_job(job):
        return jsonify({"ok": False, "error": "job already running"}), 409
    return jsonify({"ok": True, "started": "run-ticket", "ticket_id": ticket_id})


@app.post("/api/demo-ticket")
def api_demo_ticket():
    """Back-compat: run A01 with autonomous Reflect."""
    data = request.get_json(silent=True) or {}
    data["ticket_id"] = data.get("ticket_id") or "A01"

    def job():
        from parcelco.data_io import load_tickets
        from parcelco.graphs.inner import run_ticket
        from parcelco.graphs.outer import reflect_after_ticket

        tickets = {t.id: t for t in load_tickets(None)}
        ticket = tickets.get(data["ticket_id"]) or next(iter(tickets.values()))
        publish(
            {
                "type": "status",
                "status": "demo",
                "stack": "langgraph",
                "stack_detail": f"Running {ticket.id} through the autonomous loop",
                "node": "retrieve",
                "ticket_id": ticket.id,
            }
        )
        result = run_ticket(ticket)
        reflected = reflect_after_ticket(ticket, result)
        _publish_ticket_result(ticket, result, reflected)

    if not _start_job(job):
        return jsonify({"ok": False, "error": "job already running"}), 409
    return jsonify({"ok": True, "started": "demo-ticket", "ticket_id": data["ticket_id"]})


@app.post("/api/baseline")
def api_baseline():
    if not _start_job(outer.baseline):
        return jsonify({"ok": False, "error": "job already running"}), 409
    return jsonify({"ok": True, "started": "baseline"})


@app.post("/api/improve")
def api_improve():
    data = request.get_json(silent=True) or {}
    rounds = data.get("rounds")
    rounds_i = int(rounds) if rounds is not None else None
    if not _start_job(outer.improve, rounds_i):
        return jsonify({"ok": False, "error": "job already running"}), 409
    return jsonify({"ok": True, "started": "improve", "rounds": rounds_i})


@app.post("/api/reset")
def api_reset():
    if _job_running:
        return jsonify({"ok": False, "error": "job already running"}), 409
    outer.reset_all()
    return jsonify({"ok": True})


def create_app() -> Flask:
    return app

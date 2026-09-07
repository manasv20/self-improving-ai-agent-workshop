from __future__ import annotations

import os
import threading
from typing import Any

_lock = threading.Lock()
_recent: list[dict[str, Any]] = []
_MAX_RECENT = 40


def langfuse_host() -> str:
    return (
        os.getenv("LANGFUSE_HOST")
        or os.getenv("LANGFUSE_BASE_URL")
        or "http://localhost:3000"
    ).rstrip("/")


def langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _ensure_env() -> None:
    """Langfuse v4 CallbackHandler reads host from LANGFUSE_BASE_URL / LANGFUSE_HOST."""
    host = langfuse_host()
    os.environ.setdefault("LANGFUSE_HOST", host)
    os.environ.setdefault("LANGFUSE_BASE_URL", host)


def get_client() -> Any | None:
    if not langfuse_enabled():
        return None
    try:
        _ensure_env()
        from langfuse import Langfuse

        return Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=langfuse_host(),
        )
    except Exception:
        return None


def auth_ok() -> bool | None:
    """True/False if check ran; None if tracing disabled."""
    if not langfuse_enabled():
        return None
    client = get_client()
    if client is None:
        return False
    try:
        return bool(client.auth_check())
    except Exception:
        return False


def status() -> dict[str, Any]:
    enabled = langfuse_enabled()
    ok = auth_ok() if enabled else None
    host = langfuse_host()
    return {
        "enabled": enabled,
        "auth_ok": ok,
        "host": host,
        "ui_url": host,
        "traces_url": f"{host}/",  # project home; deep links use get_trace_url
        "label": (
            "Tracing ON"
            if enabled and ok
            else ("Keys set · auth failed" if enabled and ok is False else ("Keys set · checking…" if enabled else "Off — set LANGFUSE_* in .env"))
        ),
        "recent": list_recent_traces(12),
    }


def create_trace_id() -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        return client.create_trace_id()
    except Exception:
        return None


def get_callbacks(*, trace_id: str | None = None) -> list[Any]:
    if not langfuse_enabled():
        return []
    try:
        _ensure_env()
        from langfuse.langchain import CallbackHandler

        kwargs: dict[str, Any] = {"public_key": os.getenv("LANGFUSE_PUBLIC_KEY")}
        if trace_id:
            kwargs["trace_context"] = {"trace_id": trace_id}
        return [CallbackHandler(**kwargs)]
    except Exception:
        return []


def flush() -> None:
    client = get_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        pass


def trace_url(trace_id: str | None) -> str | None:
    if not trace_id:
        return None
    client = get_client()
    if client is not None:
        try:
            return client.get_trace_url(trace_id=trace_id)
        except Exception:
            pass
    host = langfuse_host()
    return f"{host}/trace/{trace_id}"


def score_trace(trace_id: str | None, name: str, value: float, comment: str = "") -> None:
    if not langfuse_enabled() or not trace_id:
        return
    client = get_client()
    if client is None:
        return
    try:
        client.create_score(
            name=name,
            value=float(value),
            trace_id=trace_id,
            comment=(comment or None),
            data_type="NUMERIC",
        )
        client.flush()
    except Exception:
        pass


def score_checklist_to_langfuse(
    trace_id: str | None,
    *,
    passed: bool,
    details: str,
    heal_count: int,
    attempt: int,
    missing: list[str] | None = None,
    detected_action: str | None = None,
    expected_action: str | None = None,
) -> None:
    """Push checklist outcome onto the LangFuse trace (shared evidence for the run)."""
    if not trace_id:
        return
    miss = ", ".join(missing or []) or "none"
    comment = (
        f"attempt={attempt} heal={heal_count} "
        f"action={detected_action or '?'}→{expected_action or '?'} "
        f"missing=[{miss}] | {details or ''}"
    )[:900]
    score_trace(trace_id, "checklist_passed", 1.0 if passed else 0.0, comment)
    score_trace(trace_id, "heal_count", float(heal_count), f"heals used before this eval: {heal_count}")
    score_trace(trace_id, "attempt_number", float(attempt), comment)


def score_slm_judge_to_langfuse(trace_id: str | None, judge: dict[str, Any] | None) -> None:
    """Record optional SLM hard + soft eval outcome."""
    if not trace_id or not isinstance(judge, dict) or not judge.get("enabled"):
        return
    if judge.get("error"):
        score_trace(trace_id, "slm_judge_error", 0.0, str(judge.get("error"))[:900])
        return
    if judge.get("passed") is None and judge.get("rules_passed") is None:
        return
    rationale = str(judge.get("rationale") or "")
    model = str(judge.get("model") or "eval-slm")
    tips = "; ".join(str(s) for s in (judge.get("suggestions") or [])[:3])
    comment = f"model={model} · soft_ok={judge.get('soft_ok')} · {rationale}"
    if tips:
        comment += f" · tips={tips}"
    score_trace(
        trace_id,
        "slm_judge_passed",
        1.0 if judge.get("passed") else 0.0,
        comment[:900],
    )
    if judge.get("rules_passed") is not None:
        score_trace(
            trace_id,
            "slm_rules_passed",
            1.0 if judge.get("rules_passed") else 0.0,
            rationale[:900],
        )
    if judge.get("soft_ok") is not None:
        score_trace(
            trace_id,
            "slm_soft_ok",
            1.0 if judge.get("soft_ok") else 0.0,
            tips[:900] or rationale[:900],
        )


def annotate_lesson_on_trace(trace_id: str | None, lesson: str, *, kept: bool = True) -> None:
    """Record Reflect output on the same trace so learning is visible in LangFuse."""
    if not trace_id or not lesson:
        return
    score_trace(
        trace_id,
        "lesson_kept" if kept else "lesson_rejected",
        1.0 if kept else 0.0,
        lesson.strip()[:900],
    )


def fetch_trace_evidence(trace_id: str | None) -> dict[str, Any]:
    """Read back observations + scores from LangFuse for this run."""
    empty: dict[str, Any] = {
        "enabled": langfuse_enabled(),
        "trace_id": trace_id,
        "url": trace_url(trace_id),
        "generation_count": 0,
        "total_latency_s": 0.0,
        "generations": [],
        "scores": [],
        "error": None,
    }
    if not langfuse_enabled() or not trace_id:
        empty["error"] = "langfuse_off" if not langfuse_enabled() else "no_trace_id"
        return empty
    flush()
    client = get_client()
    if client is None:
        empty["error"] = "client_unavailable"
        return empty
    try:
        obs = client.api.observations.get_many(trace_id=trace_id, limit=50)
        data = obs.model_dump() if hasattr(obs, "model_dump") else {}
        rows = data.get("data") or []
        generations: list[dict[str, Any]] = []
        total_lat = 0.0
        for o in rows:
            if not isinstance(o, dict):
                o = o.model_dump() if hasattr(o, "model_dump") else {}
            typ = (o.get("type") or "").upper()
            if typ and typ != "GENERATION":
                continue
            lat = o.get("latency")
            try:
                lat_f = float(lat) if lat is not None else 0.0
            except (TypeError, ValueError):
                lat_f = 0.0
            total_lat += lat_f
            generations.append(
                {
                    "id": o.get("id"),
                    "name": o.get("name") or "generation",
                    "latency_s": round(lat_f, 3),
                    "start_time": str(o.get("start_time") or ""),
                }
            )
        scores_out: list[dict[str, Any]] = []
        try:
            sc = client.api.scores.get_many(trace_id=trace_id, limit=50)
            sc_data = sc.model_dump() if hasattr(sc, "model_dump") else {}
            for s in sc_data.get("data") or []:
                if not isinstance(s, dict):
                    s = s.model_dump() if hasattr(s, "model_dump") else {}
                scores_out.append(
                    {
                        "name": s.get("name"),
                        "value": s.get("value"),
                        "comment": (s.get("comment") or "")[:240],
                    }
                )
        except Exception:
            # scores API shape varies across Langfuse versions
            pass
        return {
            "enabled": True,
            "trace_id": trace_id,
            "url": trace_url(trace_id),
            "generation_count": len(generations),
            "total_latency_s": round(total_lat, 3),
            "generations": generations,
            "scores": scores_out,
            "error": None,
        }
    except Exception as e:
        empty["error"] = str(e)[:200]
        return empty


def verify_run_against_langfuse(
    trace_id: str | None,
    *,
    heal_count: int,
    passed: bool,
) -> dict[str, Any]:
    """Use LangFuse as independent evidence that heal/generate actually ran.

    Checklist remains the policy grader. LangFuse verifies the *workflow*:
    we expect at least (1 + heal_count) LLM generations on the trace.
    """
    evidence = fetch_trace_evidence(trace_id)
    expected = 1 + max(0, int(heal_count or 0))
    gens = int(evidence.get("generation_count") or 0)
    if not evidence.get("enabled"):
        verdict = "skipped"
        ok = None
        detail = "LangFuse off — checklist-only verification"
    elif evidence.get("error"):
        verdict = "unavailable"
        ok = None
        detail = f"LangFuse read failed: {evidence['error']}"
    elif gens >= expected:
        verdict = "confirmed"
        ok = True
        detail = (
            f"LangFuse saw {gens} generation(s) (expected ≥{expected} for "
            f"{heal_count} heal(s)). Checklist={'PASS' if passed else 'FAIL'}."
        )
    else:
        verdict = "mismatch"
        ok = False
        detail = (
            f"LangFuse saw {gens} generation(s); expected ≥{expected} "
            f"after {heal_count} heal(s). Checklist={'PASS' if passed else 'FAIL'}."
        )
    evidence.update(
        {
            "expected_generations": expected,
            "heal_count": heal_count,
            "checklist_passed": passed,
            "verified": ok,
            "verdict": verdict,
            "detail": detail,
        }
    )
    # Persist verification back onto the trace
    if evidence.get("enabled") and trace_id and ok is not None:
        score_trace(
            trace_id,
            "heal_workflow_verified",
            1.0 if ok else 0.0,
            detail,
        )
    return evidence


def remember_trace(
    *,
    ticket_id: str | None,
    trace_id: str | None,
    passed: bool | None = None,
    detail: str = "",
) -> str | None:
    url = trace_url(trace_id)
    if not url and not trace_id:
        return None
    row = {
        "ticket_id": ticket_id,
        "trace_id": trace_id,
        "url": url,
        "passed": passed,
        "detail": detail,
    }
    with _lock:
        # Upsert by trace_id so heal retries don't spam the UI table
        for i, existing in enumerate(_recent):
            if existing.get("trace_id") == trace_id:
                merged = {**existing, **{k: v for k, v in row.items() if v is not None}}
                if passed is not None:
                    merged["passed"] = passed
                if detail:
                    merged["detail"] = detail
                _recent.pop(i)
                _recent.insert(0, merged)
                break
        else:
            _recent.insert(0, row)
        del _recent[_MAX_RECENT:]
    return url


def list_recent_traces(limit: int = 12) -> list[dict[str, Any]]:
    with _lock:
        return list(_recent[:limit])

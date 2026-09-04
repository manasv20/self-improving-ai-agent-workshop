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
            comment=comment or None,
            data_type="NUMERIC",
        )
        client.flush()
    except Exception:
        pass


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

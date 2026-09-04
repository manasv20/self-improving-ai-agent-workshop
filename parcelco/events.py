"""Simple in-process event bus for SSE dashboard updates."""

from __future__ import annotations

import json
import queue
import threading
from typing import Any, Iterator

_lock = threading.Lock()
_subscribers: list[queue.Queue] = []
_latest: dict[str, Any] = {
    "node": "idle",
    "ticket_id": None,
    "part_a_rate": None,
    "part_b_rate": None,
    "round": None,
    "status": "idle",
    "inspector": None,
}


def subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=256)
    with _lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: queue.Queue) -> None:
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)


def publish(event: dict[str, Any]) -> None:
    # Persist so history survives SSE drops / page refresh
    try:
        from parcelco import history as hist

        hist.append_event(event)
    except Exception:
        pass

    with _lock:
        _latest.update({k: v for k, v in event.items() if k != "type"})
        dead: list[queue.Queue] = []
        for q in _subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


def snapshot() -> dict[str, Any]:
    with _lock:
        return dict(_latest)


def sse_stream(q: queue.Queue) -> Iterator[str]:
    yield f"data: {json.dumps({'type': 'snapshot', **snapshot()})}\n\n"
    try:
        while True:
            try:
                event = q.get(timeout=15)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    finally:
        unsubscribe(q)

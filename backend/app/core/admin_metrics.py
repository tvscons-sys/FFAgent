"""Failure-isolated background metrics for the admin dashboard."""

from __future__ import annotations

import json
import queue
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

_events: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1000)
_worker_started = False
_worker_lock = threading.Lock()


def _database_path() -> Path:
    path = settings.admin_metrics_database
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(), timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize() -> None:
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                estimated_cost_inr REAL NOT NULL,
                latency_ms REAL NOT NULL,
                retrieval_latency_ms REAL NOT NULL,
                retrieved_count INTEGER NOT NULL,
                sources_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                feedback TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                issue TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL
            );
            """
        )


def _worker() -> None:
    _initialize()
    while True:
        event = _events.get()
        try:
            with _connect() as connection:
                connection.execute(
                    """INSERT INTO chat_events
                    (created_at, query, answer, model, input_tokens, output_tokens,
                     total_tokens, estimated_cost_inr, latency_ms, retrieval_latency_ms,
                     retrieved_count, sources_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event["created_at"], event["query"], event["answer"], event["model"],
                        event["input_tokens"], event["output_tokens"], event["total_tokens"],
                        event["estimated_cost_inr"], event["latency_ms"],
                        event["retrieval_latency_ms"], event["retrieved_count"],
                        json.dumps(event["sources"]),
                    ),
                )
        except Exception:
            # Metrics must never terminate or delay the customer request path.
            pass
        finally:
            _events.task_done()


def _ensure_worker() -> None:
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if not _worker_started:
            thread = threading.Thread(target=_worker, name="ff-admin-metrics", daemon=True)
            thread.start()
            _worker_started = True


def record_chat(event: dict[str, Any]) -> None:
    """Queue a chat event without waiting for disk I/O."""
    _ensure_worker()
    try:
        _events.put_nowait({"created_at": _now(), **event})
    except queue.Full:
        pass


def record_ticket(title: str, description: str, source: str = "chat") -> str:
    """Persist a submitted support ticket and return its human-readable reference."""
    _initialize()
    with _connect() as connection:
        cursor = connection.execute(
            """INSERT INTO support_tickets
            (created_at, issue, category, priority, status)
            VALUES (?, ?, ?, ?, ?)""",
            (_now(), f"{title}\n\n{description}", source, "normal", "submitted"),
        )
        return f"TKT-{cursor.lastrowid:06d}"


def dashboard(days: int = 30) -> dict[str, Any]:
    _initialize()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM chat_events WHERE created_at >= datetime('now', ?) ORDER BY id DESC",
            (f"-{days} days",),
        ).fetchall()
        ticket_count = connection.execute(
            "SELECT COUNT(*) FROM support_tickets WHERE created_at >= datetime('now', ?)",
            (f"-{days} days",),
        ).fetchone()[0]
    events = [dict(row) for row in rows]
    total = len(events)
    input_tokens = sum(row["input_tokens"] for row in events)
    output_tokens = sum(row["output_tokens"] for row in events)
    return {
        "updated_at": _now(),
        "kpis": {
            "total_questions": total,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_inr": round(sum(row["estimated_cost_inr"] for row in events), 4),
            "average_latency_ms": round(sum(row["latency_ms"] for row in events) / total, 1) if total else 0,
            "average_retrieval_latency_ms": round(sum(row["retrieval_latency_ms"] for row in events) / total, 1) if total else 0,
            "average_chunks": round(sum(row["retrieved_count"] for row in events) / total, 1) if total else 0,
            "ticket_count": ticket_count,
        },
        "recent_questions": [
            {**row, "sources": json.loads(row.pop("sources_json"))} for row in events[:20]
        ],
        "model_usage": _model_usage(events),
        "feedback": [],
        "tickets": [],
    }


def _model_usage(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usage: dict[str, dict[str, Any]] = {}
    for event in events:
        item = usage.setdefault(event["model"], {"model": event["model"], "requests": 0, "tokens": 0, "cost_inr": 0.0})
        item["requests"] += 1
        item["tokens"] += event["total_tokens"]
        item["cost_inr"] += event["estimated_cost_inr"]
    return list(usage.values())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

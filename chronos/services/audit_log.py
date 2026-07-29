"""JSON-lines audit trail shared with the dashboard."""
from __future__ import annotations

import asyncio
from pathlib import Path
from chronos.db.postgres_audit import PostgresAuditSink
from chronos.models.decisions import AuditEntry


class AuditLog:
    """Serializes events to an append-only local JSONL file."""

    def __init__(self, path: str = "logs/audit.jsonl", database_sink: PostgresAuditSink | None = None) -> None:
        """Set the audit file location and a lock for concurrent emitters."""
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._database_sink = database_sink

    async def write(self, entry: AuditEntry) -> None:
        """Append one validated audit event without blocking other coroutines."""
        async with self._lock:
            line = entry.model_dump_json() + "\n"
            await asyncio.to_thread(self._append, line)
            if self._database_sink:
                self._database_sink.enqueue(entry)

    def _append(self, line: str) -> None:
        """Perform the small synchronous append operation."""
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line)

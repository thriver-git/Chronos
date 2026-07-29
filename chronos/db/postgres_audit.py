"""Asynchronous persistence of Chronos audit events to PostgreSQL."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from chronos.models.decisions import AuditEntry


class PostgresAuditSink:
    """Write audit events off the execution path, keeping broker orders responsive."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._queue: asyncio.Queue[AuditEntry] = asyncio.Queue(maxsize=10_000)
        self._worker: asyncio.Task[None] | None = None
        self._logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Create the schema before starting the background writer."""
        await asyncio.to_thread(self._initialize)
        self._worker = asyncio.create_task(self._run(), name="postgres-audit-writer")

    def enqueue(self, entry: AuditEntry) -> None:
        """Queue an event without adding database latency to a trade decision."""
        try:
            self._queue.put_nowait(entry)
        except asyncio.QueueFull:
            self._logger.error("PostgreSQL audit queue is full; event retained only in local JSONL")

    async def close(self) -> None:
        """Flush queued events during a graceful shutdown."""
        if self._worker is None:
            return
        await self._queue.join()
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass

    async def _run(self) -> None:
        while True:
            entry = await self._queue.get()
            try:
                await asyncio.to_thread(self._insert_entries, [entry])
            except Exception:
                self._logger.exception("Could not persist audit event to PostgreSQL")
            finally:
                self._queue.task_done()

    def _initialize(self) -> None:
        import psycopg

        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(schema)

    def _insert_entries(self, entries: list[AuditEntry]) -> None:
        import psycopg

        rows = []
        for entry in entries:
            decision = entry.decision
            rows.append((
                entry.timestamp,
                entry.symbol,
                entry.event,
                entry.message,
                decision.action.value if decision else None,
                decision.confidence_score if decision else None,
                decision.reasoning if decision else None,
                json.dumps(entry.model_dump(mode="json")),
            ))
        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO audit_events
                    (occurred_at, symbol, event_type, message, action, confidence_score, reasoning, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)""",
                    rows,
                )

"""Tests for local and optional database audit persistence."""
from pathlib import Path

import pytest

from chronos.models.decisions import AuditEntry
from chronos.services.audit_log import AuditLog


class FakeDatabaseSink:
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    def enqueue(self, entry: AuditEntry) -> None:
        self.entries.append(entry)


@pytest.mark.asyncio
async def test_audit_is_retained_locally_and_enqueued_for_database(tmp_path: Path) -> None:
    sink = FakeDatabaseSink()
    audit = AuditLog(path=str(tmp_path / "audit.jsonl"), database_sink=sink)  # type: ignore[arg-type]
    entry = AuditEntry(symbol="SPY", event="decision", message="test")

    await audit.write(entry)

    assert sink.entries == [entry]
    assert '"symbol":"SPY"' in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")

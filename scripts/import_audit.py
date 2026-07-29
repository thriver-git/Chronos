"""One-time import of existing JSONL audit history into the configured PostgreSQL database."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

# Running this file directly makes Python search ``scripts/`` first; include
# the project root so the Chronos package is available without installation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chronos.db.postgres_audit import PostgresAuditSink
from chronos.models.decisions import AuditEntry


async def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to import audit history")
    sink = PostgresAuditSink(database_url)
    await sink.start()
    try:
        for line in Path("logs/audit.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                sink.enqueue(AuditEntry.model_validate_json(line))
    finally:
        await sink.close()


if __name__ == "__main__":
    asyncio.run(main())

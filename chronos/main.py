"""Chronos process entrypoint."""
from __future__ import annotations

import asyncio
import logging
from config.settings import Settings
from chronos.broker.alpaca_client import AlpacaPaperBroker
from chronos.data.market_stream import MarketStream
from chronos.db.postgres_audit import PostgresAuditSink
from chronos.llm.reasoning import LlmReasoner
from chronos.risk.risk_manager import RiskManager
from chronos.services.audit_log import AuditLog
from chronos.services.runtime_status import write_runtime_status
from chronos.services.trading_engine import TradingEngine
from chronos.utils.logging import configure_logging


async def run() -> None:
    """Build production collaborators and start the live paper-data websocket."""
    write_runtime_status("starting", "Loading Chronos configuration.")
    try:
        settings = Settings.from_env()
        configure_logging(settings.log_level)
        database_sink = PostgresAuditSink(settings.database_url) if settings.database_url else None
        if database_sink:
            try:
                await database_sink.start()
            except Exception:
                logging.getLogger(__name__).exception(
                    "PostgreSQL is unavailable; continuing with the local JSONL audit fallback"
                )
                database_sink = None
        try:
            broker = AlpacaPaperBroker(settings.alpaca_api_key, settings.alpaca_secret_key)
            engine = TradingEngine(
                broker, LlmReasoner(settings.groq_api_key), RiskManager(), AuditLog(database_sink=database_sink)
            )
            stream = MarketStream(settings.alpaca_api_key, settings.alpaca_secret_key, settings.symbols, engine.handle_trigger)
            write_runtime_status(
                "running",
                "Connected to the market stream. Waiting for enough bars and a signal trigger.",
            )
            await stream.run()
        finally:
            if database_sink:
                await database_sink.close()
    except Exception as error:
        write_runtime_status("error", str(error)[:500])
        raise


if __name__ == "__main__":
    asyncio.run(run())

"""Chronos process entrypoint."""
from __future__ import annotations

import asyncio
from config.settings import Settings
from chronos.broker.alpaca_client import AlpacaPaperBroker
from chronos.data.market_stream import MarketStream
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
        broker = AlpacaPaperBroker(settings.alpaca_api_key, settings.alpaca_secret_key)
        engine = TradingEngine(broker, LlmReasoner(settings.groq_api_key), RiskManager(), AuditLog())
        stream = MarketStream(settings.alpaca_api_key, settings.alpaca_secret_key, settings.symbols, engine.handle_trigger)
        write_runtime_status(
            "running",
            "Connected to the market stream. Waiting for enough bars and a signal trigger.",
        )
        await stream.run()
    except Exception as error:
        write_runtime_status("error", str(error)[:500])
        raise


if __name__ == "__main__":
    asyncio.run(run())

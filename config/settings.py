"""Validated environment-backed settings for Chronos."""
from __future__ import annotations

from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application configuration loaded from environment variables."""

    alpaca_api_key: str
    alpaca_secret_key: str
    groq_api_key: str
    symbols: tuple[str, ...]
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        """Load required secrets and trading symbols without exposing their values."""
        load_dotenv()
        values = {key: os.getenv(key, "").strip() for key in (
            "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "GROQ_API_KEY"
        )}
        missing = [key for key, value in values.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        symbols = tuple(item.strip().upper() for item in os.getenv(
            "TRADING_SYMBOLS", "AAPL,MSFT,SPY").split(",") if item.strip())
        if not symbols:
            raise RuntimeError("TRADING_SYMBOLS must contain at least one symbol")
        return cls(**values, symbols=symbols, log_level=os.getenv("LOG_LEVEL", "INFO"))

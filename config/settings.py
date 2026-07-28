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
        env_keys = (
            ("ALPACA_API_KEY", "alpaca_api_key"),
            ("ALPACA_SECRET_KEY", "alpaca_secret_key"),
            ("GROQ_API_KEY", "groq_api_key"),
        )
        values = {field: os.getenv(env_key, "").strip() for env_key, field in env_keys}
        missing = [env_key for env_key, field in env_keys if not values[field]]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        symbols = tuple(item.strip().upper() for item in os.getenv(
            "TRADING_SYMBOLS", "AAPL,MSFT,SPY").split(",") if item.strip())
        if not symbols:
            raise RuntimeError("TRADING_SYMBOLS must contain at least one symbol")
        return cls(**values, symbols=symbols, log_level=os.getenv("LOG_LEVEL", "INFO"))

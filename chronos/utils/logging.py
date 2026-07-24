"""Logging configuration."""
from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str) -> logging.Logger:
    """Configure console and rotating file logging, returning the root logger."""
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("logs/chronos.log", encoding="utf-8")],
        force=True,
    )
    return logging.getLogger("chronos")

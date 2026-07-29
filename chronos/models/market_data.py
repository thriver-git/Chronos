"""Market-state input models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    """Technical state used to decide whether reasoning is warranted."""

    symbol: str
    price: float = Field(gt=0)
    rsi: float = Field(ge=0, le=100)
    macd: float
    macd_signal: float


class PortfolioState(BaseModel):
    """Minimal portfolio state injected into a reasoning request."""

    buying_power: float = Field(ge=0)
    equity: float = Field(gt=0)
    unrealized_pnl: float
    position_quantity: float = 0
    has_open_order: bool = False

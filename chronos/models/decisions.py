"""Strict models for LLM decisions and audit records."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class Action(str, Enum):
    """Permitted trading actions."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradeDecision(BaseModel):
    """Validated, untrusted model recommendation; it is not an order."""

    action: Action
    confidence_score: int = Field(ge=1, le=100)
    reasoning: str = Field(min_length=1, max_length=500)

    @field_validator("reasoning")
    @classmethod
    def compact_reasoning(cls, value: str) -> str:
        """Normalize model explanations for safe persistent logging."""
        return " ".join(value.split())


class AuditEntry(BaseModel):
    """One append-only record of a trigger, decision, or execution outcome."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    event: str
    message: str
    decision: TradeDecision | None = None

"""Hard-coded risk controls that cannot be overridden by LLM output."""
from __future__ import annotations

from dataclasses import dataclass
from chronos.models.decisions import Action, TradeDecision
from chronos.models.market_data import PortfolioState


MAX_DRAWDOWN = 0.10
MAX_POSITION_FRACTION = 0.05


@dataclass(slots=True)
class RiskResult:
    """The sole executable outcome of risk validation."""
    allowed: bool
    quantity: int = 0
    reason: str = ""
    halt: bool = False


class RiskManager:
    """Tracks peak equity and constrains every individual trade."""

    def __init__(self) -> None:
        """Start without a peak; the first portfolio observation establishes it."""
        self._peak_equity = 0.0
        self.paused = False

    def validate(self, decision: TradeDecision, state: PortfolioState, price: float) -> RiskResult:
        """Reject unsafe orders and calculate a capped integral share quantity."""
        self._peak_equity = max(self._peak_equity, state.equity)
        if self._peak_equity and state.equity <= self._peak_equity * (1 - MAX_DRAWDOWN):
            self.paused = True
            return RiskResult(False, reason="10% max-drawdown kill switch activated", halt=True)
        if self.paused:
            return RiskResult(False, reason="trading remains paused")
        if decision.action == Action.HOLD:
            return RiskResult(False, reason="model selected HOLD")
        if decision.action == Action.SELL:
            quantity = int(state.position_quantity)
            return RiskResult(quantity > 0, quantity, "no position to sell" if not quantity else "")
        maximum_notional = min(state.equity * MAX_POSITION_FRACTION, state.buying_power)
        quantity = int(maximum_notional // price)
        return RiskResult(quantity > 0, quantity, "insufficient buying power for one share" if not quantity else "")

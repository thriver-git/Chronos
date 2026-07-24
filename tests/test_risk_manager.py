"""Tests for inviolable risk limits."""
from chronos.models.decisions import Action, TradeDecision
from chronos.models.market_data import PortfolioState
from chronos.risk.risk_manager import RiskManager


def test_buy_is_capped_at_five_percent() -> None:
    """A BUY decision must never receive more than five percent of equity."""
    result = RiskManager().validate(TradeDecision(action=Action.BUY, confidence_score=90, reasoning="test"),
                                    PortfolioState(buying_power=100_000, equity=100_000, unrealized_pnl=0), 100)
    assert result.allowed and result.quantity == 50


def test_drawdown_halts_execution() -> None:
    """A 10% equity fall activates the liquidation circuit breaker."""
    risk = RiskManager()
    decision = TradeDecision(action=Action.BUY, confidence_score=90, reasoning="test")
    risk.validate(decision, PortfolioState(buying_power=100_000, equity=100_000, unrealized_pnl=0), 100)
    result = risk.validate(decision, PortfolioState(buying_power=90_000, equity=90_000, unrealized_pnl=-10_000), 100)
    assert result.halt and risk.paused

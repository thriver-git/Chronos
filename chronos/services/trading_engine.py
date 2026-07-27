"""Coordinates streaming, reasoning, risk evaluation, and paper execution."""
from __future__ import annotations

import logging
from alpaca.trading.enums import OrderSide
from chronos.broker.alpaca_client import AlpacaPaperBroker
from chronos.llm.reasoning import LlmReasoner
from chronos.models.decisions import Action, AuditEntry
from chronos.models.market_data import MarketSnapshot
from chronos.risk.risk_manager import RiskManager
from chronos.services.audit_log import AuditLog
from chronos.services.runtime_status import write_runtime_status


class TradingEngine:
    """Single-symbol handler that preserves the market stream during slow I/O."""

    def __init__(self, broker: AlpacaPaperBroker, reasoner: LlmReasoner, risk: RiskManager, audit: AuditLog) -> None:
        """Store injected collaborators, simplifying isolated testing."""
        self._broker, self._reasoner, self._risk, self._audit = broker, reasoner, risk, audit
        self._logger = logging.getLogger(__name__)

    async def handle_trigger(self, market: MarketSnapshot) -> None:
        """Process one technical trigger; failures are audited and never crash streaming."""
        try:
            state = await self._broker.portfolio_state(market.symbol)
            decision = await self._reasoner.decide(market, state)
            await self._audit.write(AuditEntry(symbol=market.symbol, event="decision", message=decision.reasoning,
                                               decision=decision))
            result = self._risk.validate(decision, state, market.price)
            if result.halt:
                await self._broker.liquidate_all()
                await self._audit.write(AuditEntry(symbol=market.symbol, event="kill_switch", message=result.reason))
                write_runtime_status("halted", result.reason)
                return
            if not result.allowed:
                await self._audit.write(AuditEntry(symbol=market.symbol, event="rejected", message=result.reason))
                write_runtime_status("decision_rejected", f"{market.symbol}: {result.reason}")
                return
            side = OrderSide.BUY if decision.action == Action.BUY else OrderSide.SELL
            order_id = await self._broker.submit_limit_order(market.symbol, result.quantity, side, market.price)
            await self._audit.write(AuditEntry(symbol=market.symbol, event="order_submitted",
                                               message=f"{side.value} {result.quantity} limit @ {market.price}; id={order_id}",
                                               decision=decision))
            write_runtime_status("order_submitted", f"{market.symbol}: {side.value} {result.quantity} shares submitted.")
        except Exception as error:
            self._logger.exception("Trigger cycle failed for %s", market.symbol)
            await self._audit.write(AuditEntry(symbol=market.symbol, event="error", message=str(error)[:500]))
            write_runtime_status("error", f"{market.symbol}: {str(error)[:450]}")

"""Async facade around Alpaca's synchronous trading client."""
from __future__ import annotations

import asyncio
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.requests import GetOrdersRequest
from chronos.models.market_data import PortfolioState


MARKETABLE_LIMIT_BUFFER = 0.001


class AlpacaPaperBroker:
    """Paper-only broker adapter; blocking SDK work is isolated in threads."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        """Create an Alpaca client permanently configured for paper trading."""
        self._client = TradingClient(api_key, secret_key, paper=True)

    async def portfolio_state(self, symbol: str) -> PortfolioState:
        """Fetch account and optional current position without blocking the event loop."""
        account = await asyncio.to_thread(self._client.get_account)
        try:
            position = await asyncio.to_thread(self._client.get_open_position, symbol)
            quantity = float(position.qty)
        except Exception:  # Alpaca uses an exception when no position exists.
            quantity = 0.0
        try:
            positions = await asyncio.to_thread(self._client.get_all_positions)
            unrealized_pnl = sum(float(p.unrealized_pl or 0) for p in positions)
        except Exception:
            unrealized_pnl = 0.0
        orders = await asyncio.to_thread(
            self._client.get_orders,
            filter=GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[symbol]),
        )
        return PortfolioState(
            buying_power=float(account.buying_power), equity=float(account.equity),
            unrealized_pnl=unrealized_pnl, position_quantity=quantity,
            has_open_order=bool(orders),
        )

    async def submit_limit_order(
        self, symbol: str, quantity: int, side: OrderSide, limit_price: float
    ) -> str:
        """Submit a protected marketable day-limit order and return its identifier."""
        # A limit exactly at a completed bar's close commonly remains unfilled
        # by the time the order reaches Alpaca.  This small buffer lets a BUY
        # cross the current ask (and a SELL cross the bid) while still bounding
        # the worst accepted price.
        protected_price = limit_price * (
            1 + MARKETABLE_LIMIT_BUFFER if side == OrderSide.BUY else 1 - MARKETABLE_LIMIT_BUFFER
        )
        request = LimitOrderRequest(
            symbol=symbol, qty=quantity, side=side, time_in_force=TimeInForce.DAY,
            limit_price=round(protected_price, 2),
        )
        order = await asyncio.to_thread(self._client.submit_order, order_data=request)
        return str(order.id)

    async def liquidate_all(self) -> None:
        """Close every paper position for the drawdown circuit breaker."""
        await asyncio.to_thread(self._client.close_all_positions, cancel_orders=True)

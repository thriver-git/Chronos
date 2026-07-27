"""Non-blocking Alpaca websocket bar stream."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

import pandas as pd
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar

from chronos.data.indicators import calculate_macd, calculate_rsi
from chronos.models.market_data import MarketSnapshot
from chronos.services.runtime_status import write_runtime_status

SnapshotHandler = Callable[[MarketSnapshot], Awaitable[None]]


class MarketStream:
    """Converts live five-minute Alpaca bars into threshold-triggered snapshots."""

    def __init__(self, api_key: str, secret_key: str, symbols: tuple[str, ...], handler: SnapshotHandler) -> None:
        """Configure the websocket and retain short rolling price histories."""
        self._stream = StockDataStream(api_key, secret_key)
        self._symbols = symbols
        self._handler = handler
        self._closes: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=60))
        self._logger = logging.getLogger(__name__)

    async def _on_bar(self, bar: Bar) -> None:
        """Update history and call downstream reasoning only at defined triggers."""
        prices = self._closes[bar.symbol]
        prices.append(float(bar.close))
        if len(prices) < 35:
            write_runtime_status(
                "warming_up",
                f"{bar.symbol}: collected {len(prices)}/35 bars before signal analysis starts.",
            )
            return
        try:
            closes = pd.Series(prices, dtype="float64")
            rsi = calculate_rsi(closes)
            macd, signal = calculate_macd(closes)
            if rsi < 30 or rsi > 70:
                write_runtime_status(
                    "decision_pending",
                    f"{bar.symbol}: RSI {rsi:.1f} triggered an LLM decision.",
                )
                await self._handler(MarketSnapshot(symbol=bar.symbol, price=float(bar.close), rsi=rsi,
                                                   macd=macd, macd_signal=signal))
            else:
                write_runtime_status(
                    "waiting_for_signal",
                    f"{bar.symbol}: RSI {rsi:.1f} is within the 30–70 trading range.",
                )
        except (ValueError, ArithmeticError) as error:
            self._logger.warning("Indicator calculation skipped for %s: %s", bar.symbol, error)

    async def run(self) -> None:
        """Subscribe to five-minute bars and keep the websocket alive."""
        self._stream.subscribe_bars(self._on_bar, *self._symbols)
        await asyncio.to_thread(self._stream.run)

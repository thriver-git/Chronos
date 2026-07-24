"""Pure, local technical indicator functions."""
from __future__ import annotations

import pandas as pd


def calculate_rsi(closes: pd.Series, period: int = 14) -> float:
    """Return Wilder-style RSI, raising when insufficient price history exists."""
    if len(closes) < period + 1:
        raise ValueError("Not enough candles to calculate RSI")
    delta = closes.diff()
    gains = delta.clip(lower=0).rolling(period).mean()
    losses = -delta.clip(upper=0).rolling(period).mean()
    denominator = losses.iloc[-1]
    if denominator == 0:
        return 100.0
    return float(100 - (100 / (1 + gains.iloc[-1] / denominator)))


def calculate_macd(closes: pd.Series) -> tuple[float, float]:
    """Return the latest MACD and its signal line from close prices."""
    if len(closes) < 35:
        raise ValueError("Not enough candles to calculate MACD")
    macd = closes.ewm(span=12, adjust=False).mean() - closes.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(signal.iloc[-1])

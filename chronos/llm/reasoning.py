"""Groq-backed decision engine with strict JSON validation."""
from __future__ import annotations

import asyncio
import json
from groq import Groq
from chronos.models.decisions import TradeDecision
from chronos.models.market_data import MarketSnapshot, PortfolioState


SYSTEM_PROMPT = """You are a conservative paper-trading decision engine. Return ONLY valid JSON:
{"action":"BUY|SELL|HOLD","confidence_score":1-100,"reasoning":"short explanation"}.
Never include Markdown, quantities, or advice beyond this schema. Prefer HOLD when uncertain."""


class LlmReasoner:
    """Obtains bounded, schema-validated recommendations from Groq."""

    def __init__(self, api_key: str) -> None:
        """Initialize the Groq SDK; calls are executed off the asyncio event loop."""
        self._client = Groq(api_key=api_key)

    async def decide(self, market: MarketSnapshot, portfolio: PortfolioState) -> TradeDecision:
        """Request and validate exactly one decision for a technical trigger."""
        payload = {"asset": market.symbol, "price": market.price, "rsi": market.rsi,
                   "macd": market.macd, "macd_signal": market.macd_signal,
                   "portfolio_balance": portfolio.equity,
                   "buying_power": portfolio.buying_power,
                   "unrealized_pnl": portfolio.unrealized_pnl,
                   "current_position": portfolio.position_quantity}
        response = await asyncio.to_thread(
            self._client.chat.completions.create,
            model="llama-3.1-8b-instant", temperature=0, max_tokens=120,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": json.dumps(payload)}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned an empty response")
        return TradeDecision.model_validate_json(content)

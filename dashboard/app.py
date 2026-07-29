"""Live paper-trading dashboard for the Chronos agent."""
from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest
from dotenv import load_dotenv

load_dotenv()

_ENGINE_LOCK = threading.Lock()
_ENGINE_THREAD: threading.Thread | None = None


def _embed_engine_enabled() -> bool:
    return os.getenv("CHRONOS_EMBED_ENGINE", "").strip().lower() in {"1", "true", "yes"}


def _start_embedded_engine() -> None:
    """Run the trading engine in-process for the low-memory demo deployment."""
    global _ENGINE_THREAD
    if not _embed_engine_enabled():
        return
    with _ENGINE_LOCK:
        if _ENGINE_THREAD is not None and _ENGINE_THREAD.is_alive():
            return

        def _run_engine() -> None:
            from chronos.main import run

            asyncio.run(run())

        _ENGINE_THREAD = threading.Thread(target=_run_engine, daemon=True, name="chronos-engine")
        _ENGINE_THREAD.start()


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


@st.cache_data(ttl=15, show_spinner=False)
def load_alpaca_data() -> tuple[dict[str, float | str], pd.DataFrame, pd.DataFrame, str | None]:
    """Read live broker facts server-side; credentials never reach the browser."""
    api_key = os.getenv("ALPACA_API_KEY", "").strip()
    secret_key = os.getenv("ALPACA_SECRET_KEY", "").strip()
    if not api_key or not secret_key:
        return {}, _empty_frame([]), _empty_frame([]), "Alpaca credentials are not configured."
    try:
        client = TradingClient(api_key, secret_key, paper=True)
        account = client.get_account()
        positions = client.get_all_positions()
        orders = client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.ALL, limit=100))
        position_rows = [{
            "Symbol": position.symbol,
            "Quantity": float(position.qty),
            "Average entry": float(position.avg_entry_price),
            "Current price": float(position.current_price),
            "Market value": float(position.market_value),
            "Unrealized P&L": float(position.unrealized_pl),
            "Unrealized P&L %": float(position.unrealized_plpc) * 100,
        } for position in positions]
        order_rows = [{
            "Submitted": order.submitted_at,
            "Symbol": order.symbol,
            "Side": order.side.value,
            "Quantity": float(order.qty),
            "Type": order.type.value,
            "Limit price": float(order.limit_price) if order.limit_price else None,
            "Filled price": float(order.filled_avg_price) if order.filled_avg_price else None,
            "Status": order.status.value,
        } for order in orders]
        account_data = {
            "equity": float(account.equity),
            "last_equity": float(account.last_equity),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
        }
        return account_data, pd.DataFrame(position_rows), pd.DataFrame(order_rows), None
    except Exception as error:
        return {}, _empty_frame([]), _empty_frame([]), f"Could not fetch Alpaca data: {str(error)[:180]}"


@st.cache_data(ttl=20, show_spinner=False)
def load_strategy_events() -> tuple[pd.DataFrame, str]:
    """Prefer Neon audit history and retain JSONL as a local development fallback."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        try:
            import psycopg

            with psycopg.connect(database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT occurred_at, symbol, event_type, message, action, confidence_score, reasoning
                        FROM audit_events ORDER BY occurred_at DESC LIMIT 500
                    """)
                    rows = cursor.fetchall()
            return pd.DataFrame(rows, columns=[
                "Timestamp", "Symbol", "Event", "Message", "Action", "Confidence", "Reasoning",
            ]), "Neon PostgreSQL"
        except Exception:
            pass
    path = Path("logs/audit.jsonl")
    if not path.exists():
        return _empty_frame(["Timestamp", "Symbol", "Event", "Message"]), "No event store available"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
            decision = item.get("decision") or {}
            rows.append({
                "Timestamp": item.get("timestamp"), "Symbol": item.get("symbol"),
                "Event": item.get("event"), "Message": item.get("message"),
                "Action": decision.get("action"), "Confidence": decision.get("confidence_score"),
                "Reasoning": decision.get("reasoning"),
            })
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows).sort_values("Timestamp", ascending=False), "Local JSONL fallback"


def load_runtime_status() -> dict[str, str]:
    try:
        return json.loads(Path("logs/runtime_status.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"state": "starting", "detail": "The engine has not reported a status yet."}


_start_embedded_engine()
st.set_page_config(page_title="Chronos | Paper Trading", page_icon="◷", layout="wide")

st.title("Chronos")
st.caption("Paper-trading command center. Broker facts are live from Alpaca; strategy history is stored in Neon.")

if st.button("Refresh live data", type="primary"):
    st.cache_data.clear()
    st.rerun()

account, positions, orders, alpaca_error = load_alpaca_data()
events, event_source = load_strategy_events()
status = load_runtime_status()

if alpaca_error:
    st.warning(alpaca_error)
if status["state"] == "running":
    st.success(f"Engine running — {status['detail']}")
elif status["state"] == "error":
    st.error(f"Engine error — {status['detail']}")
else:
    st.info(f"Engine {status['state'].replace('_', ' ')} — {status['detail']}")

today_pnl = account.get("equity", 0) - account.get("last_equity", 0)
top = st.columns(5)
top[0].metric("Equity", f"${account.get('equity', 0):,.2f}", f"${today_pnl:,.2f} today")
top[1].metric("Buying power", f"${account.get('buying_power', 0):,.2f}")
top[2].metric("Cash", f"${account.get('cash', 0):,.2f}")
top[3].metric("Open positions", len(positions))
top[4].metric("Open orders", int((orders.get("Status", pd.Series(dtype=str)) == "open").sum()))

overview_tab, portfolio_tab, orders_tab, strategy_tab, system_tab = st.tabs(
    ["Overview", "Portfolio", "Orders & fills", "Strategy", "System"]
)

with overview_tab:
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Position P&L")
        if positions.empty:
            st.info("No open paper positions.")
        else:
            chart = px.bar(positions, x="Symbol", y="Unrealized P&L", color="Unrealized P&L", color_continuous_scale="RdYlGn")
            chart.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(chart, use_container_width=True)
    with right:
        st.subheader("Recent decisions")
        decisions = events[events.get("Event", pd.Series(dtype=str)) == "decision"] if not events.empty else events
        if decisions.empty:
            st.info("No strategy decisions recorded yet.")
        else:
            st.dataframe(decisions[["Timestamp", "Symbol", "Action", "Confidence"]].head(8), use_container_width=True, hide_index=True)

with portfolio_tab:
    st.subheader("Live Alpaca positions")
    if positions.empty:
        st.info("No open positions in the paper account.")
    else:
        st.dataframe(
            positions.style.format({
                "Average entry": "${:,.2f}", "Current price": "${:,.2f}", "Market value": "${:,.2f}",
                "Unrealized P&L": "${:,.2f}", "Unrealized P&L %": "{:+.2f}%",
            }), use_container_width=True, hide_index=True,
        )

with orders_tab:
    st.subheader("Latest Alpaca order status")
    if orders.empty:
        st.info("No broker orders found.")
    else:
        st.dataframe(
            orders.style.format({"Limit price": "${:,.2f}", "Filled price": "${:,.2f}"}),
            use_container_width=True, hide_index=True,
        )

with strategy_tab:
    st.subheader("Decision & risk timeline")
    st.caption(f"Source: {event_source}")
    if events.empty:
        st.info("No strategy events are available yet.")
    else:
        symbols = ["All symbols", *sorted(events["Symbol"].dropna().unique().tolist())]
        selected_symbol = st.selectbox("Symbol", symbols)
        visible_events = events if selected_symbol == "All symbols" else events[events["Symbol"] == selected_symbol]
        st.dataframe(visible_events, use_container_width=True, hide_index=True)

with system_tab:
    st.subheader("System health")
    st.json(status)
    st.caption("Alpaca API data refreshes every 15 seconds. Strategy events refresh every 20 seconds.")

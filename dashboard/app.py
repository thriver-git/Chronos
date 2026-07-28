"""Streamlit audit dashboard for the Chronos paper-trading agent."""
from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path

import pandas as pd
import streamlit as st

_ENGINE_LOCK = threading.Lock()
_ENGINE_THREAD: threading.Thread | None = None


def _embed_engine_enabled() -> bool:
    return os.getenv("CHRONOS_EMBED_ENGINE", "").strip().lower() in {"1", "true", "yes"}


def _start_embedded_engine() -> None:
    """Run the trading engine in-process for low-memory single-container deploys."""
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


_start_embedded_engine()


def load_audit(path: Path) -> pd.DataFrame:
    """Load valid audit JSON lines, returning an empty frame if none exist yet."""
    if not path.exists():
        return pd.DataFrame()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows)


def load_runtime_status(path: Path) -> dict[str, str]:
    """Load the latest engine status without breaking the dashboard."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"state": "starting", "detail": "The engine has not reported a status yet."}


st.set_page_config(page_title="Chronos", layout="wide")
st.title("Chronos — Paper Trading Audit")
st.caption("Live order decisions and risk outcomes. Paper trading only.")
status = load_runtime_status(Path("logs/runtime_status.json"))
if status["state"] == "running":
    st.success(f"Engine running — {status['detail']}")
elif status["state"] == "error":
    st.error(f"Engine error — {status['detail']}")
else:
    st.info(f"Engine {status['state'].replace('_', ' ')} — {status['detail']}")
if st.button("Refresh"):
    st.rerun()
audit = load_audit(Path("logs/audit.jsonl"))
if audit.empty:
    st.info("No events yet. Start the Chronos engine to populate this feed.")
else:
    st.metric("Events", len(audit))
    st.dataframe(audit.sort_values("timestamp", ascending=False), use_container_width=True)

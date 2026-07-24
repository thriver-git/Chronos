"""Streamlit audit dashboard for the Chronos paper-trading agent."""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as st


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


st.set_page_config(page_title="Chronos", layout="wide")
st.title("Chronos — Paper Trading Audit")
st.caption("Live order decisions and risk outcomes. Paper trading only.")
if st.button("Refresh"):
    st.rerun()
audit = load_audit(Path("logs/audit.jsonl"))
if audit.empty:
    st.info("No events yet. Start the Chronos engine to populate this feed.")
else:
    st.metric("Events", len(audit))
    st.dataframe(audit.sort_values("timestamp", ascending=False), use_container_width=True)

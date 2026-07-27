"""Small shared status file used by the deployment dashboard."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


STATUS_PATH = Path("logs/runtime_status.json")


def write_runtime_status(state: str, detail: str) -> None:
    """Persist an engine state that the Streamlit process can display."""
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps({
        "state": state,
        "detail": detail,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")

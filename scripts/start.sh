#!/bin/sh
# Start the trading engine beside Streamlit, matching local development.
set -eu

export CHRONOS_EMBED_ENGINE=0

python -m chronos.main &
ENGINE_PID="$!"
trap 'kill "$ENGINE_PID" 2>/dev/null || true' EXIT

exec streamlit run dashboard/app.py \
    --server.address 0.0.0.0 \
    --server.port "${PORT:-8501}" \
    --server.headless true \
    --server.fileWatcherType none

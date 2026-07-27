#!/bin/sh
# Start the stream-processing engine and keep the public Streamlit process in
# the foreground. The engine records its own status for the dashboard.
set -eu

python -m chronos.main &
engine_pid=$!

shutdown() {
    kill "$engine_pid" 2>/dev/null || true
}
trap shutdown INT TERM EXIT

exec streamlit run dashboard/app.py \
    --server.address 0.0.0.0 \
    --server.port "${PORT:-8501}" \
    --server.headless true

#!/bin/sh
# Single Streamlit process embeds the engine to stay within Render free-tier RAM.
set -eu

export CHRONOS_EMBED_ENGINE=1

exec streamlit run dashboard/app.py \
    --server.address 0.0.0.0 \
    --server.port "${PORT:-8501}" \
    --server.headless true \
    --server.fileWatcherType none

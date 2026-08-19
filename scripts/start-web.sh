#!/usr/bin/env bash
# ==============================================================================
# Customer Support Chatbot - Start Web Chat UI
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source .env if present
if [ -f "${ROOT_DIR}/.env" ]; then
    set -a
    source "${ROOT_DIR}/.env"
    set +a
fi

PYTHON_BIN="python3"
if [ -f "${ROOT_DIR}/.venv/bin/python" ]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
fi

HOST="${1:-127.0.0.1}"
PORT="${2:-8000}"

echo "Starting Customer Support Web UI on http://${HOST}:${PORT}..."
"${PYTHON_BIN}" "${ROOT_DIR}/src/web/server.py" --host "${HOST}" --port "${PORT}"

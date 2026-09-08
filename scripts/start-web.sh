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
MODE="${3:---mock}"

if [[ "${MODE}" != "--mock" && "${MODE}" != "--live" ]]; then
    echo "Mode must be --mock or --live." >&2
    exit 2
fi

echo "Starting Customer Support Web UI on http://${HOST}:${PORT} (${MODE})..."
PYTHONPATH="${ROOT_DIR}/backend/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON_BIN}" -m support_service.legacy_web \
    --host "${HOST}" --port "${PORT}" "${MODE}"

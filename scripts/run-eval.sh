#!/usr/bin/env bash
# ==============================================================================
# Customer Support Chatbot - Automated Evaluation Runner
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

MODE="${1:---mock}"

echo "=================================================================="
echo " Running Customer Support Chatbot Evaluation Suite"
echo " Mode: ${MODE}"
echo "=================================================================="

# 1. Generate Bedrock Evaluation Dataset JSONL
echo "--> Generating Evaluation Dataset JSONL..."
"${PYTHON_BIN}" "${ROOT_DIR}/eval/generate_eval_dataset.py" "${MODE}" \
    --tests-json "${ROOT_DIR}/eval/test_cases.json" \
    --out-jsonl "${ROOT_DIR}/eval/eval_dataset.jsonl"

# 2. Run Comprehensive Accuracy Evaluation
echo ""
echo "--> Running Evaluation Benchmark..."
"${PYTHON_BIN}" "${ROOT_DIR}/eval/evaluate_agent.py" "${MODE}" \
    --tests-file "${ROOT_DIR}/eval/test_cases.json"

echo "=================================================================="
echo " Evaluation finished successfully."
echo "=================================================================="

#!/usr/bin/env python3
"""
Generate Amazon Bedrock Evaluations BYOI (Bring Your Own Inference) dataset JSONL
by running the Customer Support Agent against the curated golden test suite.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.config import AgentConfig
from src.agent.core import CustomerSupportAgent
from src.agent.session import SessionMemory


def generate_eval_dataset(
    tests_json_path: Path,
    out_jsonl_path: Path,
    model_identifier: str = "agentcore-customer-support",
    mock_mode: bool = True,
    region: str = "us-east-1"
) -> int:
    """Run test cases and generate Bedrock Evaluation JSONL."""
    with open(tests_json_path, "r", encoding="utf-8") as f:
        suite = json.load(f)

    tests = suite.get("tests", [])
    if mock_mode:
        os.environ["AWS_MOCK_MODE"] = "true"
    config = AgentConfig(
        model_id=model_identifier if not mock_mode else "amazon.nova-pro-v1:0",
        region_name=region,
        mock_mode=mock_mode
    )
    agent = CustomerSupportAgent(config=config)

    print(f"Executing {len(tests)} test prompts (Mock Mode: {mock_mode})...")

    out_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    records_written = 0

    with open(out_jsonl_path, "w", encoding="utf-8") as out_f:
        for idx, test in enumerate(tests, 1):
            test_id = test["id"]
            prompt = test["prompt"]
            reference = test.get("expected", "")
            category = test.get("category", "general")

            session = SessionMemory()
            try:
                agent_resp = agent.chat(prompt, session=session)
                response_text = agent_resp.text
                tools_used = [tc.tool_name for tc in agent_resp.tool_calls]
            except Exception as exc:
                print(f"[{test_id}] Error: {exc}", file=sys.stderr)
                response_text = f"[ERROR] {exc}"
                tools_used = []

            record = {
                "id": test_id,
                "category": category,
                "prompt": prompt,
                "referenceResponse": reference,
                "modelResponses": [
                    {
                        "modelIdentifier": model_identifier,
                        "response": response_text
                    }
                ],
                "metadata": {
                    "toolsUsed": tools_used,
                    "stopReason": agent_resp.stop_reason if 'agent_resp' in locals() else "error"
                }
            }

            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            records_written += 1
            print(f"[{idx}/{len(tests)}] {test_id} ({category}) -> OK")

    print(f"\nSuccessfully generated {records_written} evaluation records in {out_jsonl_path}")
    return records_written


def main():
    parser = argparse.ArgumentParser(description="Generate Bedrock Evaluations Dataset JSONL")
    parser.add_argument(
        "--tests-json",
        default=str(Path(__file__).parent / "test_cases.json"),
        help="Path to the test suite JSON file."
    )
    parser.add_argument(
        "--out-jsonl",
        default=str(Path(__file__).parent / "eval_dataset.jsonl"),
        help="Path where output JSONL should be written."
    )
    parser.add_argument(
        "--model-identifier",
        default="customer-support-agentcore",
        help="Model identifier label in output records."
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Run agent in local mock mode (default: True)."
    )
    parser.add_argument(
        "--live",
        dest="mock",
        action="store_false",
        help="Run agent against live AWS Bedrock model."
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="AWS region for live Bedrock invocation."
    )
    args = parser.parse_args()

    generate_eval_dataset(
        tests_json_path=Path(args.tests_json),
        out_jsonl_path=Path(args.out_jsonl),
        model_identifier=args.model_identifier,
        mock_mode=args.mock,
        region=args.region
    )


if __name__ == "__main__":
    main()

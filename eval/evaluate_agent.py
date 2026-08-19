#!/usr/bin/env python3
"""
Automated Evaluation Harness for Customer Support Chatbot.
Evaluates agent performance against the test suite across grounding, tool calling, and safety.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from src.agent.config import AgentConfig
from src.agent.core import CustomerSupportAgent
from src.agent.session import SessionMemory

console = Console()


def evaluate_single_test(agent: CustomerSupportAgent, test: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a single test case against acceptance criteria."""
    test_id = test["id"]
    category = test.get("category", "unknown")
    prompt = test["prompt"]
    expected_tool = test.get("expected_tool")
    keywords = test.get("keywords", [])

    session = SessionMemory()
    response = agent.chat(prompt, session=session)
    response_text = response.text
    tools_called = [tc.tool_name for tc in response.tool_calls]

    passed = True
    failure_reasons: list[str] = []

    # Check tool calling requirement
    if expected_tool and expected_tool not in tools_called:
        passed = False
        failure_reasons.append(f"Expected tool '{expected_tool}' was not called. Called: {tools_called}")

    # Check keyword presence for grounding / deflection
    if keywords:
        found_keywords = [k for k in keywords if k.lower() in response_text.lower()]
        if not found_keywords:
            passed = False
            failure_reasons.append(f"None of expected keywords found: {keywords}")

    return {
        "id": test_id,
        "category": category,
        "prompt": prompt,
        "response": response_text,
        "tools_called": tools_called,
        "passed": passed,
        "reasons": failure_reasons,
    }


def run_evaluation(tests_file: Path, mock: bool = True) -> bool:
    """Execute complete evaluation suite and render score summary."""
    with open(tests_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    tests = data.get("tests", [])
    if mock:
        os.environ["AWS_MOCK_MODE"] = "true"
    config = AgentConfig(mock_mode=mock)
    agent = CustomerSupportAgent(config=config)

    console.print(f"\n[bold cyan]Running Agent Evaluation Suite ({len(tests)} cases)[/bold cyan]")
    console.print(f"Mode: {'[yellow]Mock[/yellow]' if mock else '[green]Live AWS[/green]'}\n")

    results: list[dict[str, Any]] = []
    category_stats: dict[str, dict[str, int]] = {}

    for test in tests:
        res = evaluate_single_test(agent, test)
        results.append(res)

        cat = res["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1
        if res["passed"]:
            category_stats[cat]["passed"] += 1

    # Render results table
    table = Table(title="Evaluation Results by Test Case", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=18)
    table.add_column("Category", width=22)
    table.add_column("Tools Used", width=20)
    table.add_column("Status", width=10)
    table.add_column("Details", style="dim")

    for r in results:
        status = "[bold green]PASS[/bold green]" if r["passed"] else "[bold red]FAIL[/bold red]"
        tools = ", ".join(r["tools_called"]) if r["tools_called"] else "-"
        detail = "" if r["passed"] else "; ".join(r["reasons"])
        table.add_row(r["id"], r["category"], tools, status, detail)

    console.print(table)

    # Render summary table
    summary_table = Table(title="Category Performance Summary", show_header=True, header_style="bold green")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Total Cases", justify="right")
    summary_table.add_column("Passed", justify="right")
    summary_table.add_column("Accuracy", justify="right")

    total_cases = len(results)
    total_passed = sum(1 for r in results if r["passed"])

    for cat, stats in category_stats.items():
        pct = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0
        summary_table.add_row(cat, str(stats["total"]), str(stats["passed"]), f"{pct:.1f}%")

    overall_pct = (total_passed / total_cases) * 100 if total_cases > 0 else 0.0
    summary_table.add_row("[bold]OVERALL[/bold]", str(total_cases), str(total_passed), f"[bold]{overall_pct:.1f}%[/bold]")

    console.print(summary_table)

    return total_passed == total_cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Customer Support Agent")
    parser.add_argument("--tests-file", default=str(Path(__file__).parent / "test_cases.json"))
    parser.add_argument("--mock", action="store_true", default=True)
    parser.add_argument("--live", dest="mock", action="store_false")
    args = parser.parse_args()

    success = run_evaluation(tests_file=Path(args.tests_file), mock=args.mock)
    sys.exit(0 if success else 1)

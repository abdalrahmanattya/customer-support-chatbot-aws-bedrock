"""Interactive CLI Chat Interface for Customer Support Chatbot."""

import argparse

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.agent.config import AgentConfig
from src.agent.core import CustomerSupportAgent
from src.agent.session import SessionMemory

console = Console()


def run_cli():
    parser = argparse.ArgumentParser(description="Customer Support Chatbot (AWS Bedrock AgentCore)")
    parser.add_argument("--model", default=None, help="Bedrock Model ID (e.g. amazon.nova-pro-v1:0)")
    parser.add_argument("--region", default="us-east-1", help="AWS Region")
    parser.add_argument("--mock", action="store_true", help="Run in local offline mock mode")
    parser.add_argument("--lambda-arn", default=None, help="Optional Lambda ARN for bug reports")
    args = parser.parse_args()

    config = AgentConfig(
        region_name=args.region,
        mock_mode=args.mock,
    )
    if args.model:
        config.model_id = args.model
    if args.lambda_arn:
        config.lambda_tool_arn = args.lambda_arn

    agent = CustomerSupportAgent(config=config)
    session = SessionMemory()

    mode_label = "[bold yellow]OFFLINE MOCK MODE[/bold yellow]" if config.mock_mode else f"[bold green]AWS BEDROCK ({config.model_id})[/bold green]"

    console.print(
        Panel.fit(
            f"[bold cyan]Customer Support Assistant[/bold cyan]\n"
            f"Mode: {mode_label}\n"
            f"Type [bold red]'exit'[/bold red] to quit, [bold yellow]'clear'[/bold yellow] to reset history.",
            border_style="cyan"
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold green]You > [/bold green]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[bold cyan]Thank you for visiting Online Shop Support. Goodbye![/bold cyan]")
                break

            if user_input.lower() in ("clear", "reset"):
                session.clear()
                console.print("[yellow]Conversation history cleared.[/yellow]")
                continue

            with console.status("[cyan]Assistant is thinking...[/cyan]"):
                response = agent.chat(user_input, session=session)

            # Display any tool calls made
            if response.tool_calls:
                for tc in response.tool_calls:
                    console.print(
                        f"[dim cyan]🔧 [Tool Executed]: {tc.tool_name} | "
                        f"Result: {tc.tool_result.get('status', 'OK')} "
                        f"({tc.tool_result.get('ticketId', '')})[/dim cyan]"
                    )

            console.print(
                Panel(
                    Markdown(response.text),
                    title="[bold cyan]Assistant[/bold cyan]",
                    border_style="blue"
                )
            )

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold cyan]Session ended. Goodbye![/bold cyan]")
            break
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")


if __name__ == "__main__":
    run_cli()

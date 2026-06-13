"""Mage Audit CLI — command-line interface for code review."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.agent import ReviewService, Severity
from src.core.config import settings
from src.core.llm import get_llm_provider

app = typer.Typer(
    name="mage-audit",
    help="AI-powered architecture auditor for Magento codebases.",
)
console = Console()


def severity_color(severity: Severity) -> str:
    """Map severity to Rich color."""
    match severity:
        case Severity.CRITICAL:
            return "bold red"
        case Severity.ERROR:
            return "red"
        case Severity.WARNING:
            return "yellow"
        case Severity.INFO:
            return "blue"


@app.command()
def review(
    file: Path = typer.Argument(
        ...,
        help="Path to PHP file to review.",
        exists=True,
        readable=True,
    ),
    model: str = typer.Option(
        "",
        "--model",
        "-m",
        help="LLM model override (default from .env).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output raw JSON instead of formatted report.",
    ),
) -> None:
    """Review a PHP file for bugs, security issues, and architecture problems."""
    asyncio.run(_review(file, model, json_output))


async def _review(file: Path, model: str, json_output: bool) -> None:
    """Async implementation of the review command."""
    code = file.read_text(encoding="utf-8")

    console.print(
        Panel(
            f"[bold]Reviewing:[/bold] {file}\n"
            f"[bold]Lines:[/bold] {len(code.splitlines())}\n"
            f"[bold]Provider:[/bold] {settings.llm_provider}\n"
            f"[bold]Model:[/bold] {model or settings.llm_model}",
            title="Mage Audit",
            border_style="blue",
        )
    )

    with console.status("[bold green]Analyzing code..."):
        llm = get_llm_provider(settings.llm_provider, model=model)
        service = ReviewService(llm)
        result = await service.review_file(str(file), code)

    if json_output:
        import json

        output = [f.model_dump() for f in result.findings]
        console.print_json(json.dumps(output, indent=2))
        return

    # Summary
    console.print()
    if not result.findings:
        console.print("[bold green]No issues found! 🎉[/bold green]")
        return

    # Findings table
    table = Table(
        title=f"Review: {result.file_path}",
        show_lines=True,
    )
    table.add_column("Sev", width=8, justify="center")
    table.add_column("Line", width=6, justify="right")
    table.add_column("Cat", width=12)
    table.add_column("Issue", min_width=30)
    table.add_column("Suggestion", min_width=30)

    for finding in result.findings:
        color = severity_color(finding.severity)
        table.add_row(
            f"[{color}]{finding.severity.upper()}[/{color}]",
            str(finding.line or "-"),
            finding.category,
            finding.issue,
            finding.suggestion,
        )

    console.print(table)

    # Summary footer
    console.print(
        Panel(
            f"[bold red]Critical: {result.critical_count}[/bold red]  "
            f"[red]Error: {result.error_count}[/red]  "
            f"[yellow]Warning: {result.warning_count}[/yellow]  "
            f"[dim]Model: {result.model} | "
            f"Tokens: {result.input_tokens} in / {result.output_tokens} out[/dim]",
            title="Summary",
            border_style="dim",
        )
    )


if __name__ == "__main__":
    app()

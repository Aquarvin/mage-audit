"""Mage Audit CLI — command-line interface for Magento code analysis."""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from src.core.agent import ReviewService, SearchService, Severity
from src.core.config import settings
from src.core.embeddings import LocalEmbedder
from src.core.llm import get_llm_provider
from src.frameworks.magento import MagentoModuleIndexer

app = typer.Typer(
    name="mage-audit",
    help="AI-powered architecture auditor for Magento codebases.",
    no_args_is_help=True,
)
console = Console()


# ──────────────────────────────────────────────
#  review command
# ──────────────────────────────────────────────


@app.command()
def review(
    file: Path = typer.Argument(..., help="Path to PHP file to review.", exists=True),
    model: str = typer.Option("", "--model", "-m", help="LLM model override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Review a PHP file for bugs, security issues, and architecture problems."""
    asyncio.run(_review(file, model, json_output))


def severity_color(severity: Severity) -> str:
    match severity:
        case Severity.CRITICAL:
            return "bold red"
        case Severity.ERROR:
            return "red"
        case Severity.WARNING:
            return "yellow"
        case Severity.INFO:
            return "blue"


async def _review(file: Path, model: str, json_output: bool) -> None:
    code = file.read_text(encoding="utf-8")

    console.print(
        Panel(
            f"[bold]Reviewing:[/bold] {file}\n"
            f"[bold]Lines:[/bold] {len(code.splitlines())}\n"
            f"[bold]Provider:[/bold] {settings.llm_provider}\n"
            f"[bold]Model:[/bold] {model or settings.llm_model}",
            title="Mage Audit — Review",
            border_style="blue",
        )
    )

    with console.status("[bold green]Analyzing code..."):
        llm = get_llm_provider(settings.llm_provider, model=model)
        service = ReviewService(llm)
        result = await service.review_file(str(file), code)

    if json_output:
        output = [f.model_dump() for f in result.findings]
        console.print_json(json.dumps(output, indent=2))
        return

    if not result.findings:
        console.print("[bold green]No issues found![/bold green]")
        return

    table = Table(title=f"Review: {result.file_path}", show_lines=True)
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


# ──────────────────────────────────────────────
#  index command
# ──────────────────────────────────────────────


@app.command()
def index(
    module_path: Path = typer.Argument(
        ..., help="Path to Magento module directory.", exists=True
    ),
    repo_name: str = typer.Option(
        "", "--name", "-n", help="Repository name (default: directory name)."
    ),
) -> None:
    """Index a Magento module for semantic search."""
    if not repo_name:
        repo_name = module_path.name

    asyncio.run(_index(module_path, repo_name))


async def _index(module_path: Path, repo_name: str) -> None:
    console.print(
        Panel(
            f"[bold]Module:[/bold] {module_path}\n[bold]Repo name:[/bold] {repo_name}",
            title="Mage Audit — Index",
            border_style="green",
        )
    )

    with console.status("[bold green]Indexing module..."):
        embedder = LocalEmbedder()
        indexer = MagentoModuleIndexer(embedder=embedder)
        stats = await indexer.index_module(module_path, repo_name=repo_name)

    table = Table(title="Indexing Results")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    for key, value in stats.items():
        table.add_row(key, str(value))

    console.print(table)
    console.print(
        f"\n[green]Done![/green] Use [bold]mage-audit search '{repo_name}' 'query'[/bold] to search."  # noqa: E501
    )


# ──────────────────────────────────────────────
#  search command
# ──────────────────────────────────────────────


@app.command()
def search(
    repo_name: str = typer.Argument(..., help="Repository name to search in."),
    query: str = typer.Argument(..., help="Natural language search query."),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results."),
    show_code: bool = typer.Option(False, "--code", "-c", help="Show code snippets."),
) -> None:
    """Search indexed code by semantic similarity."""
    asyncio.run(_search(repo_name, query, limit, show_code))


async def _search(repo_name: str, query: str, limit: int, show_code: bool) -> None:
    console.print(
        Panel(
            f"[bold]Repo:[/bold] {repo_name}\n[bold]Query:[/bold] {query}",
            title="Mage Audit — Search",
            border_style="cyan",
        )
    )

    with console.status("[bold cyan]Searching..."):
        embedder = LocalEmbedder()
        service = SearchService(embedder=embedder)
        results = await service.search(query, repo_name=repo_name, limit=limit)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Results for: '{query}'")
    table.add_column("#", width=3, justify="right")
    table.add_column("Sim", width=6, justify="right")
    table.add_column("Type", width=10)
    table.add_column("File :: Name", min_width=30)
    table.add_column("Tags", min_width=20)

    for i, r in enumerate(results, 1):
        tags = ""
        deps = r.metadata.get("dependencies", [])
        magento_tags = [d for d in deps if d.startswith("[")]
        if magento_tags:
            tags = " ".join(magento_tags)

        sim_color = (
            "green" if r.similarity > 0.7 else "yellow" if r.similarity > 0.5 else "dim"
        )
        table.add_row(
            str(i),
            f"[{sim_color}]{r.similarity:.4f}[/{sim_color}]",
            r.chunk_type,
            f"{r.file_path} :: {r.chunk_name}",
            tags,
        )

    console.print(table)

    if show_code:
        for i, r in enumerate(results, 1):
            console.print(
                Panel(
                    Syntax(r.content, "php", theme="monokai", line_numbers=True),
                    title=f"[{i}] {r.file_path} :: {r.chunk_name}",
                    border_style="dim",
                )
            )


if __name__ == "__main__":
    app()

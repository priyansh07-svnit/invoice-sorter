import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, TextColumn
from rich.table import Table

from invoice_sorter.models import ProcessingResult
from invoice_sorter.pipeline import run_pipeline

console = Console(force_terminal=True, legacy_windows=False, width=120)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Invoice Sorter - Local AI-powered invoice and receipt organizer for freelancers.

    Runs entirely on your machine using open-source AI (Ollama).
    Your client data never leaves your laptop.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@cli.command()
@click.argument("input_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path))
@click.option("--model", default="llama3.2:3b", help="Ollama model to use for extraction")
@click.option("--organize-by", type=click.Choice(["category", "date", "vendor", "type"]),
              default="category", help="How to organize output folders")
@click.option("--export", multiple=True, type=click.Choice(["json", "csv", "excel"]),
              default=["json", "csv"], help="Export formats")
@click.option("--ollama-host", default="http://localhost:11434", envvar="OLLAMA_HOST",
              help="Ollama server URL (also OLLAMA_HOST env var)")
def process(input_dir: Path, output_dir: Path, model: str, organize_by: str,
            export: tuple, ollama_host: str):
    """Process invoices and receipts from INPUT_DIR and save results to OUTPUT_DIR."""

    console.print("[bold blue]Invoice Sorter[/bold blue] - Processing documents")
    console.print(f"Input:  [cyan]{input_dir}[/cyan]")
    console.print(f"Output: [cyan]{output_dir}[/cyan]")
    console.print(f"Model:  [cyan]{model}[/cyan]")
    console.print(f"Organize by: [cyan]{organize_by}[/cyan]")
    console.print()

    if not input_dir.resolve().exists():
        console.print(f"[red]Error: Input directory '{input_dir}' does not exist.[/red]")
        sys.exit(1)

    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=None)

        try:
            result = run_pipeline(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                model=model,
                organize_by=organize_by,
                export_formats=list(export),
                ollama_host=ollama_host,
            )
            progress.update(task, completed=True)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    _print_results(result, console)


@cli.command()
@click.option("--host", default="http://localhost:11434", envvar="OLLAMA_HOST",
              help="Ollama server URL (also OLLAMA_HOST env var)")
def check_ollama(host: str):
    """Check if Ollama is running and list available models."""
    import ollama

    try:
        client = ollama.Client(host=host)
        models_response = client.list()

        if isinstance(models_response, dict):
            models_list = models_response.get("models", [])
        elif hasattr(models_response, "models"):
            models_list = models_response.models
        else:
            models_list = []

        console.print("[green]OK Ollama is running[/green]")
        console.print()

        if models_list:
            table = Table(title="Available Models")
            table.add_column("Name", style="cyan")
            table.add_column("Size", style="green")
            table.add_column("Modified", style="yellow")

            for m in models_list:
                if isinstance(m, dict):
                    name = m.get("name", "unknown")
                    size = m.get("size", 0)
                    modified = m.get("modified_at", "unknown")[:19]
                else:
                    name = getattr(m, "name", "unknown")
                    size = getattr(m, "size", 0)
                    modified = str(getattr(m, "modified_at", "unknown"))[:19]

                table.add_row(
                    name,
                    f"{size / 1e9:.1f} GB",
                    modified,
                )
            console.print(table)
        else:
            msg = "[yellow]No models installed. Pull one with: ollama pull llama3.2:3b[/yellow]"
            console.print(msg)
    except Exception as e:
        console.print(f"[red]X Cannot connect to Ollama at {host}[/red]")
        console.print(f"Error: {e}")
        console.print("\nMake sure Ollama is running: [cyan]ollama serve[/cyan]")
        sys.exit(1)


@cli.command()
def categories():
    """List supported expense categories."""
    from invoice_sorter.models import ExpenseCategory

    table = Table(title="Supported Expense Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Description", style="white")

    descriptions = {
        "software": "Software licenses, SaaS subscriptions",
        "hardware": "Computer equipment, peripherals",
        "office_supplies": "Stationery, office materials",
        "travel": "Transportation, accommodation",
        "meals": "Business meals, coffee meetings",
        "marketing": "Ads, promotional materials",
        "professional_services": "Legal, accounting, consulting",
        "subscriptions": "Recurring service subscriptions",
        "utilities": "Internet, phone, electricity",
        "rent": "Office/co-working space rent",
        "insurance": "Business insurance",
        "taxes": "Tax payments",
        "other": "Uncategorized expenses",
    }

    for cat in ExpenseCategory:
        table.add_row(cat.value, descriptions.get(cat.value, ""))

    console.print(table)


def _print_results(result: ProcessingResult, console: Console):
    console.print()
    console.print("[bold green]Processing Complete![/bold green]")
    console.print()

    table = Table(title="Results Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Processed", str(result.total_processed))
    table.add_row("Successful", str(result.successful))
    table.add_row("Failed / Needs Review", str(result.failed))
    console.print(table)

    if result.errors:
        console.print()
        console.print("[yellow]Errors:[/yellow]")
        for err in result.errors[:5]:
            console.print(f"  • {err}")
        if len(result.errors) > 5:
            console.print(f"  ... and {len(result.errors) - 5} more")

    if result.documents:
        console.print()
        console.print("[bold]Extracted Data Preview:[/bold]")
        preview_table = Table()
        preview_table.add_column("File", style="cyan", max_width=30)
        preview_table.add_column("Type", style="white")
        preview_table.add_column("Vendor", style="white", max_width=20)
        preview_table.add_column("Amount", style="green")
        preview_table.add_column("Date", style="yellow")
        preview_table.add_column("Category", style="magenta")
        preview_table.add_column("Confidence", style="blue")

        for doc in result.documents[:10]:
            preview_table.add_row(
                Path(doc.file_path).name,
                doc.document_type.value,
                doc.vendor or "-",
                f"{doc.amount:.2f} {doc.currency}" if doc.amount else "-",
                doc.date.isoformat() if doc.date else "-",
                doc.category.value,
                f"{doc.confidence:.0%}",
            )
        console.print(preview_table)

        if len(result.documents) > 10:
            console.print(f"\n[dim]... and {len(result.documents) - 10} more documents[/dim]")


if __name__ == "__main__":
    cli()
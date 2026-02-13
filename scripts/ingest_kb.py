# -*- coding: utf-8 -*-
"""Script to ingest PDF knowledge base into FAISS vector store."""
import io
import os
import sys

import click
from rich.console import Console
from rich.progress import Progress

# Force UTF-8 output for Hebrew filename support
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.config import Settings
from server.rag.ingest import PDFIngestor

console = Console(force_terminal=True)


@click.command()
@click.option("--kb-dir", default="./knowledge_base", help="Directory containing PDF files")
@click.option("--clear", is_flag=True, help="Clear existing vector store before ingesting")
def main(kb_dir: str, clear: bool):
    settings = Settings()
    console.print("[bold]Ask Michal - Knowledge Base Ingestion[/bold]\n")

    console.print("Loading embedding model (first run may download ~470MB)...")
    ingestor = PDFIngestor(settings)
    console.print("[green]Model loaded.[/green]\n")

    if clear:
        ingestor.clear()
        console.print("[yellow]Vector store cleared.[/yellow]\n")

    if not os.path.isdir(kb_dir):
        console.print(f"[red]Directory not found: {kb_dir}[/red]")
        sys.exit(1)

    pdfs = [f for f in os.listdir(kb_dir) if f.lower().endswith(".pdf")]
    if not pdfs:
        console.print(f"[yellow]No PDF files found in {kb_dir}[/yellow]")
        sys.exit(0)

    console.print(f"Found [bold]{len(pdfs)}[/bold] PDF files to process.\n")

    total_chunks = 0
    with Progress() as progress:
        task = progress.add_task("Processing PDFs...", total=len(pdfs))
        for pdf_file in pdfs:
            path = os.path.join(kb_dir, pdf_file)
            chunks = ingestor.ingest_pdf(path)
            console.print(f"  [green]{pdf_file}[/green]: {chunks} new chunks")
            total_chunks += chunks
            progress.update(task, advance=1)

    console.print(
        f"\n[bold green]Done![/bold green] "
        f"Added {total_chunks} new chunks. "
        f"Total chunks in store: {len(ingestor.metadata['chunks'])}"
    )


if __name__ == "__main__":
    main()

"""CLI for resume management using typer."""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from clanker.logger import get_logger
from rich.console import Console
from rich.markdown import Markdown

from .agents import generate_resume, parse_job_posting
from .models import AppConfig, ModelConfig, ResumeDeps, UserBackground
from .storage import ResumeStorage

logger = get_logger("resumes")

app = typer.Typer(help="AI-powered resume generator")
console = Console()
storage = ResumeStorage()


def get_model_config(provider: Optional[str] = None, model: Optional[str] = None) -> ModelConfig:
    """Get model configuration with optional overrides."""
    config = AppConfig.load()
    model_config = config.default_model

    if provider:
        model_config.provider = provider
    if model:
        model_config.model_name = model

    return model_config


@app.command()
def init():
    """Initialize vault with background template."""
    storage.init_background_template()
    console.print("[green]✓[/green] Initialized vault with background.md template.")
    console.print("Edit your background in the vault to customize your profile.")


@app.command()
def parse_job(
    input_file: Path = typer.Argument(..., help="Job posting text file to parse", exists=True),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider (anthropic/openai)"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name")
):
    """Parse a job posting from a text file."""
    # Load content (text files only)
    if input_file.suffix.lower() == '.pdf':
        console.print("[red]Error: PDF files are not supported. Please provide a text file.[/red]")
        raise typer.Exit(1)

    raw_content = input_file.read_text()
    model_config = get_model_config(provider, model)

    # Parse job posting
    with console.status(f"[yellow]Parsing job posting with {model_config.provider}:{model_config.model_name}...[/yellow]"):
        try:
            job = parse_job_posting(raw_content, model_config)

            job_id = storage.save_job_posting(job)

            console.print(f"\n[green]✓[/green] Parsed job posting:")
            console.print(f"[bold]ID:[/bold] {job_id}")
            console.print(f"[bold]Title:[/bold] {job.title}")
            console.print(f"[bold]Company:[/bold] {job.company}")
            console.print(f"[bold]Industry:[/bold] {job.industry}")
            console.print(f"\n[bold]Practical description:[/bold]")
            console.print(job.practical_description)

        except Exception as e:
            console.print(f"[red]Error parsing job posting:[/red] {e}", err=True)
            raise typer.Exit(1)


@app.command("list-jobs")
def list_jobs():
    """List all parsed job postings."""
    jobs = storage.list_jobs()

    if not jobs:
        console.print("[yellow]No job postings found. Use 'parse-job' to add one.[/yellow]")
        return

    console.print("[bold]Job Postings:[/bold]")
    for job in jobs:
        console.print(f"  • [{job['id']}] {job['title']} at {job['company']}")
        console.print(f"    Added: {job['created_at'][:10]}")


@app.command()
def generate(
    job_id: str = typer.Argument(..., help="Job posting ID to generate resume for"),
    tone: Optional[str] = typer.Option(None, "--tone", help="Resume tone (e.g., technical, casual, formal)"),
    feedback: Optional[str] = typer.Option(None, "--feedback", help="Feedback for revision"),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider (anthropic/openai)"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name")
):
    """Generate a resume for a specific job posting."""
    # Load job posting
    job = storage.load_job_posting(job_id)
    if not job:
        console.print(f"[red]Error: Job posting '{job_id}' not found. Use 'list-jobs' to see available postings.[/red]")
        raise typer.Exit(1)

    # Load user background
    background_text = storage.load_user_background()

    # Parse background into sections (simplified for now)
    background = UserBackground(
        experience_md=background_text,
        education_md="",
        contact_md="",
        skills_md=""
    )

    # Configure model
    model_config = get_model_config(provider, model)

    # Create resume dependencies
    deps = ResumeDeps(
        job_posting=job,
        user_background=background,
        template="standard",  # Simple template for now
        tone=tone,
        user_feedback=feedback
    )

    # Generate resume
    with console.status(f"[yellow]Generating resume for: {job.title} at {job.company}[/yellow]"):
        with console.status(f"[yellow]Using {model_config.provider}:{model_config.model_name}...[/yellow]"):
            try:
                result, metadata = generate_resume(deps, model_config)

                # Save resume
                storage.save_resume(job_id, result.resume_markdown, metadata)

                # Display resume
                console.print(f"\n[green]✓[/green] Generated resume for {job.title} at {job.company}")
                console.print(f"[dim]Summary: {result.summary or 'No summary available'}[/dim]")
                console.print("\n" + "="*60)
                console.print(Markdown(result.resume_markdown))
                console.print("="*60 + "\n")

            except Exception as e:
                console.print(f"[red]Error generating resume:[/red] {e}", err=True)
                raise typer.Exit(1)


@app.command("show-resume")
def show_resume(job_id: str = typer.Argument(..., help="Job posting ID to show resume for")):
    """Show resumes for a job posting."""
    # Load job posting
    job = storage.load_job_posting(job_id)
    if not job:
        console.print(f"[red]Error: Job posting '{job_id}' not found.[/red]")
        raise typer.Exit(1)

    # Get latest resume markdown
    resume_md = storage.get_latest_resume_markdown(job_id)
    if not resume_md:
        console.print(f"[red]No resume found for job '{job_id}'. Use 'generate' to create one.[/red]")
        raise typer.Exit(1)

    console.print(Markdown(resume_md))


@app.command("show-background")
def show_background():
    """Show current background information."""
    background = storage.load_user_background()
    console.print(Markdown(background))


@app.command("edit-background")
def edit_background(
    content: Optional[str] = typer.Argument(None, help="New background content"),
):
    """Edit your background information.

    Pass content as argument or pipe from stdin:
    - edit-background "Your new background content"
    - echo "Your content" | edit-background
    - cat background.md | edit-background
    """
    # Get content from argument or stdin
    if content is None:
        # Read from stdin if no argument provided
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            console.print("[red]Error: Provide content as argument or via stdin[/red]")
            console.print("Examples:")
            console.print('  edit-background "Your background here"')
            console.print('  cat background.md | edit-background')
            raise typer.Exit(1)

    # Save the new background using vault
    storage.vault.write("background.md", content)
    console.print("[green]✓[/green] Background updated successfully.")


@app.command()
def export(
    job_id: str = typer.Argument(..., help="Job posting ID to export"),
    template: str = typer.Option('professional', "--template",
                                help="PDF template style (professional/modern)")
):
    """Export resume to PDF format."""
    # Load job posting
    job = storage.load_job_posting(job_id)
    if not job:
        console.print(f"[red]Error: Job posting '{job_id}' not found.[/red]")
        raise typer.Exit(1)

    # Get latest resume markdown
    resume_md = storage.get_latest_resume_markdown(job_id)
    if not resume_md:
        console.print(f"[red]No resume found for job '{job_id}'. Use 'generate' to create one first.[/red]")
        raise typer.Exit(1)

    # Generate PDF
    from .pdf_generator import PDFGenerator
    import tempfile

    gen = PDFGenerator()

    try:
        # Generate PDF to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        # Generate PDF to temp location
        generated_pdf = gen.generate(resume_md, tmp_path, template)

        # Read PDF content
        pdf_content = generated_pdf.read_bytes()

        # Save to vault
        vault_path = storage.save_resume_pdf(job_id, pdf_content)

        # Clean up temp file
        tmp_path.unlink()

        console.print(f"[green]✓[/green] Exported PDF resume to vault: {vault_path}")
        console.print(f"[dim]Template: {template}[/dim]")

    except Exception as e:
        console.print(f"[red]Error generating PDF:[/red] {e}", err=True)
        console.print("\n[dim]Note: WeasyPrint requires system dependencies:[/dim]")
        console.print("  [dim]macOS: brew install cairo pango gdk-pixbuf libffi[/dim]")
        console.print("  [dim]Ubuntu: sudo apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0[/dim]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()


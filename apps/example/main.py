"""Journal app demonstrating all Clanker storage features."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime
import json
from typing import Optional, List
import uuid

from example.storage import JournalStorage

app = typer.Typer(help="Personal journal app demonstrating Clanker features")
console = Console()


@app.command()
def add(entry: str = typer.Argument(..., help="Journal entry text")):
    """Add a new journal entry."""
    storage = JournalStorage()
    
    try:
        entry_id = storage.add_entry(entry)
        console.print(f"[green]✓ Added journal entry {entry_id}[/green]")
        
        # Get the full entry data for structured response
        entries = storage.db.query("entries", {"entry_id": entry_id})
        if entries:
            entry_data = entries[0]
            return json.dumps({
                "success": True,
                "entry_id": entry_id,
                "created_at": entry_data['created_at'],
                "word_count": entry_data['word_count'],
                "tags": entry_data['tags'],
                "summary": entry_data['summary'],
                "content": entry
            })
        else:
            return json.dumps({
                "success": True,
                "entry_id": entry_id,
                "message": "Entry added successfully"
            })
            
    except Exception as e:
        console.print(f"[red]✗ Failed to add entry: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list(count: int = typer.Option(5, "--count", "-n", help="Number of recent entries to show")):
    """Show recent journal entries."""
    storage = JournalStorage()
    
    try:
        entries = storage.get_recent_entries(count)
        
        if not entries:
            console.print("[yellow]No journal entries found.[/yellow]")
            return json.dumps({"entries": [], "count": 0})
        
        # Build structured data with content for agents
        structured_entries = []
        for entry in entries:
            # Parse the entry metadata
            created = entry['created_at']
            content = storage.get_entry_content(entry['entry_id'])
            
            # Display rich panel for console users
            panel = Panel(
                content.strip(),
                title=f"Entry {entry['entry_id'][:8]}... | {created}",
                border_style="blue",
                padding=(1, 2)
            )
            console.print(panel)
            
            # Add to structured data for agents
            structured_entries.append({
                "entry_id": entry['entry_id'],
                "created_at": entry['created_at'],
                "word_count": entry['word_count'],
                "tags": entry['tags'],
                "summary": entry['summary'],
                "content": content.strip()
            })
        
        # Return structured data for agents
        return json.dumps({
            "entries": structured_entries,
            "count": len(structured_entries)
        })
        
    except Exception as e:
        console.print(f"[red]✗ Failed to list entries: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def search(query: str = typer.Argument(..., help="Search term")):
    """Search journal entries by content."""
    storage = JournalStorage()
    
    try:
        results = storage.search_entries(query)
        
        if not results:
            console.print(f"[yellow]No entries found matching '{query}'[/yellow]")
            return json.dumps({
                "query": query,
                "results": [],
                "count": 0
            })
        
        console.print(f"[green]Found {len(results)} entries matching '{query}':[/green]")
        
        # Build structured data with content for agents
        structured_results = []
        for entry in results:
            content = storage.get_entry_content(entry['entry_id'])
            
            # Display rich panel for console users
            panel = Panel(
                content.strip(),
                title=f"Entry {entry['entry_id'][:8]}... | {entry['created_at']}",
                border_style="green",
                padding=(1, 2)
            )
            console.print(panel)
            
            # Add to structured data for agents
            structured_results.append({
                "entry_id": entry['entry_id'],
                "created_at": entry['created_at'],
                "word_count": entry['word_count'],
                "tags": entry['tags'],
                "summary": entry['summary'],
                "content": content.strip()
            })
        
        # Return structured data for agents
        return json.dumps({
            "query": query,
            "results": structured_results,
            "count": len(structured_results)
        })
        
    except Exception as e:
        console.print(f"[red]✗ Search failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show journal statistics."""
    storage = JournalStorage()
    
    try:
        stats = storage.get_statistics()
        
        # Display rich table for console users
        table = Table(title="Journal Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Entries", str(stats['total_entries']))
        table.add_row("Total Words", str(stats['total_words']))
        table.add_row("Average Words per Entry", f"{stats['avg_words']:.1f}")
        table.add_row("First Entry", stats['first_entry'] or "N/A")
        table.add_row("Last Entry", stats['last_entry'] or "N/A")
        table.add_row("Entries This Month", str(stats['entries_this_month']))
        
        console.print(table)
        
        # Return structured data for agents
        return json.dumps(stats)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to get statistics: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def backup():
    """Export all journal entries to JSON format in vault."""
    storage = JournalStorage()
    
    try:
        backup_filename = storage.create_backup()
        
        # Get entry count for display
        stats = storage.get_statistics()
        
        console.print(f"[green]✓ Backup saved to vault: {backup_filename}[/green]")
        console.print(f"[blue]Exported {stats['total_entries']} entries[/blue]")
        
        # Return structured data for agents
        return json.dumps({
            "success": True,
            "backup_filename": backup_filename,
            "total_entries": stats['total_entries'],
            "backup_location": "vault",
            "created_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        console.print(f"[red]✗ Backup failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
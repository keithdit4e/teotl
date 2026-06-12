"""Memory management CLI commands."""

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from teotl.primitives.memory.local import LocalMemory

console = Console()


@click.group()
def memory():
    """Manage agent memory."""
    pass


@memory.command()
@click.option("--path", type=click.Path(), help="Memory database path")
@click.option("--limit", default=100, help="Maximum memories to list")
@click.option("--offset", default=0, help="Pagination offset")
def list(path: str | None, limit: int, offset: int):
    """List all stored memories."""
    memory_path = Path(path) if path else None
    mem = LocalMemory(memory_path, auto_cleanup=False)

    async def _list():
        memories = await mem.list_all(limit=limit, offset=offset)
        total = await mem.count()

        if not memories:
            console.print("[yellow]No memories found.[/yellow]")
            return

        table = Table(title=f"Memories ({len(memories)} of {total})")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Content", style="white")
        table.add_column("Importance", justify="center")
        table.add_column("Created", style="dim")
        table.add_column("Expires", style="dim")

        for m in memories:
            # Truncate content
            content = m.content if len(m.content) < 60 else m.content[:57] + "..."

            # Format expiration
            expires = "Never" if not m.expires_at else m.expires_at.strftime("%Y-%m-%d")

            table.add_row(
                m.id[:8],
                content,
                str(m.metadata.importance),
                m.created.strftime("%Y-%m-%d"),
                expires,
            )

        console.print(table)

        if total > limit + offset:
            console.print(
                f"\n[dim]Showing {offset + 1}-{offset + len(memories)} of {total}. Use --offset to see more.[/dim]"
            )

    asyncio.run(_list())


@memory.command()
@click.argument("query")
@click.option("--path", type=click.Path(), help="Memory database path")
@click.option("--limit", default=10, help="Maximum results")
def search(query: str, path: str | None, limit: int):
    """Search memories by content."""
    memory_path = Path(path) if path else None
    mem = LocalMemory(memory_path, auto_cleanup=False)

    async def _search():
        memories = await mem.recall(query, limit=limit)

        if not memories:
            console.print(f"[yellow]No memories found matching '{query}'[/yellow]")
            return

        console.print(f"\n[bold]Found {len(memories)} memories:[/bold]\n")

        for i, m in enumerate(memories, 1):
            panel = Panel(
                f"{m.content}\n\n"
                f"[dim]Importance: {m.metadata.importance} | "
                f"Source: {m.metadata.source} | "
                f"Created: {m.created.strftime('%Y-%m-%d %H:%M')}[/dim]",
                title=f"[cyan]{i}. {m.id[:8]}[/cyan]",
                border_style="blue",
            )
            console.print(panel)

    asyncio.run(_search())


@memory.command()
@click.argument("memory_id")
@click.option("--path", type=click.Path(), help="Memory database path")
def delete(memory_id: str, path: str | None):
    """Delete a specific memory by ID."""
    memory_path = Path(path) if path else None
    mem = LocalMemory(memory_path, auto_cleanup=False)

    async def _delete():
        deleted = await mem.forget(memory_id)

        if deleted:
            console.print(f"[green]✓[/green] Deleted memory {memory_id[:8]}")
        else:
            console.print(f"[red]✗[/red] Memory {memory_id[:8]} not found")

    asyncio.run(_delete())


@memory.command()
@click.option("--path", type=click.Path(), help="Memory database path")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
def cleanup(path: str | None, dry_run: bool):
    """Clean up expired and inactive memories."""
    memory_path = Path(path) if path else None
    mem = LocalMemory(memory_path, auto_cleanup=False)

    async def _cleanup():
        if dry_run:
            # Show what would be deleted
            stats = await mem.get_retention_stats()
            console.print("[yellow]Dry run - no memories will be deleted[/yellow]\n")
            console.print(f"Expired memories pending cleanup: {stats['expired_pending_cleanup']}")
            console.print(f"Never accessed memories: {stats['never_accessed']}")
            return

        expired = await mem.cleanup_expired()
        storage = await mem.cleanup_by_storage_limit(mem.max_memories)

        total = expired + storage

        if total > 0:
            console.print(f"[green]✓[/green] Cleaned up {total} memories")
            console.print(f"  - Expired: {expired}")
            console.print(f"  - Over storage limit: {storage}")
        else:
            console.print("[green]✓[/green] No memories needed cleanup")

    asyncio.run(_cleanup())


@memory.command()
@click.option("--path", type=click.Path(), help="Memory database path")
def stats(path: str | None):
    """Show memory retention statistics."""
    memory_path = Path(path) if path else None
    mem = LocalMemory(memory_path, auto_cleanup=False)

    async def _stats():
        stats = await mem.get_retention_stats()

        # Create stats table
        table = Table(title="Memory Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")

        table.add_row("Total Memories", str(stats["total_memories"]))
        table.add_row("Expired (pending cleanup)", str(stats["expired_pending_cleanup"]))
        table.add_row("Never Accessed", str(stats["never_accessed"]))
        table.add_row("Avg Access Count", str(stats["avg_access_count"]))

        console.print(table)

        # Importance distribution
        console.print("\n[bold]By Importance:[/bold]")
        importance_table = Table()
        importance_table.add_column("Importance", justify="center")
        importance_table.add_column("Count", justify="right")

        for importance in range(10, 0, -1):
            count = stats["by_importance"].get(importance, 0)
            if count > 0:
                importance_table.add_row(str(importance), str(count))

        console.print(importance_table)

    asyncio.run(_stats())


@memory.command()
@click.argument("output_file", type=click.Path())
@click.option("--path", type=click.Path(), help="Memory database path")
def export(output_file: str, path: str | None):
    """Export memories to JSON file."""
    memory_path = Path(path) if path else None
    mem = LocalMemory(memory_path, auto_cleanup=False)

    async def _export():
        memories = await mem.list_all(limit=100000)  # Get all

        export_data = []
        for m in memories:
            export_data.append(
                {
                    "id": m.id,
                    "content": m.content,
                    "importance": m.metadata.importance,
                    "source": m.metadata.source,
                    "tags": m.metadata.tags,
                    "created": m.created.isoformat(),
                    "expires_at": m.expires_at.isoformat() if m.expires_at else None,
                    "access_count": m.access_count,
                }
            )

        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)

        console.print(f"[green]✓[/green] Exported {len(export_data)} memories to {output_file}")

    asyncio.run(_export())


@memory.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--path", type=click.Path(), help="Memory database path")
def import_memories(input_file: str, path: str | None):
    """Import memories from JSON file."""
    memory_path = Path(path) if path else None
    mem = LocalMemory(memory_path, auto_cleanup=False)

    async def _import():
        with open(input_file) as f:
            import_data = json.load(f)

        from datetime import datetime

        from teotl.core.types import MemoryMeta

        imported = 0
        for item in import_data:
            # Calculate TTL if expires_at is set
            ttl_days = None
            if item.get("expires_at"):
                expires_at = datetime.fromisoformat(item["expires_at"])
                days_until_expiry = (expires_at - datetime.now()).days
                if days_until_expiry > 0:
                    ttl_days = days_until_expiry

            await mem.remember(
                item["content"],
                MemoryMeta(
                    source=item.get("source", "import"),
                    importance=item.get("importance", 5),
                    tags=item.get("tags", []),
                ),
                ttl_days=ttl_days,
            )
            imported += 1

        console.print(f"[green]✓[/green] Imported {imported} memories from {input_file}")

    asyncio.run(_import())


if __name__ == "__main__":
    memory()

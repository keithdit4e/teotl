"""`teotl mcp`: review the tools your MCP servers offer."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from teotl.primitives.integrations.mcp_inventory import APPROVED, BLOCKED, PENDING, ToolInventory

console = Console()

STATUS_STYLE = {APPROVED: "green", PENDING: "yellow", BLOCKED: "red"}


@click.group()
def mcp() -> None:
    """Review the tools your MCP servers offer.

    Teotl records every MCP server's tools. Tools that appear or change after a
    server's first connection are held: the agent must ask before using them,
    and they're refused when no one is watching, until you approve them here.
    """


def _split(target: str) -> tuple[str, str]:
    server, sep, tool = target.partition(".")
    if not sep or not server or not tool:
        raise click.BadParameter(f"use SERVER.TOOL (patterns work: github.*), not {target!r}")
    return server, tool


@mcp.command("tools")
@click.argument("server", required=False)
@click.option("--held", is_flag=True, help="Only tools waiting for approval")
@click.option("--removed", is_flag=True, help="Include tools the server no longer lists")
def tools_command(server: str | None, held: bool, removed: bool) -> None:
    """List the recorded tools, marking new, changed and blocked ones."""
    inventory = ToolInventory()
    servers = inventory.servers()
    if server is not None and server not in servers:
        raise click.ClickException(f"No MCP server named {server!r} has been seen yet")
    if not servers:
        console.print("No MCP servers recorded yet. They're recorded when an agent connects.")
        return
    table = Table()
    for column in ("Tool", "Status", "Risk", "Description"):
        table.add_column(column)
    shown = 0
    for name, record in sorted(servers.items()):
        if server is not None and name != server:
            continue
        for tool, entry in sorted(record.get("tools", {}).items()):
            gone = entry.get("removed")
            if (gone and not removed) or (held and entry.get("status") != PENDING):
                continue
            status = entry.get("status", "")
            label = {
                PENDING: f"held ({entry.get('reason', 'new')})",
            }.get(status, status)
            if gone:
                label += ", removed"
            style = STATUS_STYLE.get(status, "")
            table.add_row(
                f"{name}.{tool}",
                f"[{style}]{label}[/{style}]" if style else label,
                entry.get("risk") or "",
                entry.get("description") or "",
            )
            shown += 1
    if not shown:
        console.print("No tools waiting for approval." if held else "No tools to show.")
        return
    console.print(table)
    console.print(f"Inventory: {inventory.path}")


def _set(target: str, status: str) -> list[str]:
    server, tool = _split(target)
    inventory = ToolInventory()
    if server not in inventory.servers():
        raise click.ClickException(f"No MCP server named {server!r} has been seen yet")
    matched = inventory.set_status(server, tool, status)
    if not matched:
        raise click.ClickException(f"{server} has no tool matching {tool!r}")
    return [f"{server}.{t}" for t in matched]


@mcp.command()
@click.argument("targets", nargs=-1, required=True)
def approve(targets: tuple[str, ...]) -> None:
    """Approve held tools: teotl mcp approve github.create_issue 'notes.*'"""
    for target in targets:
        for name in _set(target, APPROVED):
            console.print(f"[green]Approved[/green] {name}")
    console.print("Running agents pick this up on their next MCP call.")


@mcp.command()
@click.argument("targets", nargs=-1, required=True)
def block(targets: tuple[str, ...]) -> None:
    """Block tools so agents never call them, even if they change later."""
    for target in targets:
        for name in _set(target, BLOCKED):
            console.print(f"[red]Blocked[/red] {name}")


@mcp.command()
@click.argument("server")
@click.confirmation_option(prompt="Forget this server's tools? Its next tool list is approved.")
def forget(server: str) -> None:
    """Drop a server's record; its next tool list becomes the approved baseline."""
    if not ToolInventory().forget(server):
        raise click.ClickException(f"No MCP server named {server!r} has been seen yet")
    console.print(f"Forgot {server}")

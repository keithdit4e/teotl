"""A tiny MCP server for tests: notes kept in a folder (NOTES_DIR)."""

import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

NOTES = Path(os.environ["NOTES_DIR"])
server = MCPServer("notes")


@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_notes() -> str:
    """List the notes.

    Returns one name per line."""
    return "\n".join(sorted(p.name for p in NOTES.iterdir())) or "(none)"


@server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
def add_note(name: str, text: str) -> str:
    """Add a note."""
    (NOTES / name).write_text(text)
    return f"added {name}"


@server.tool()
def delete_all() -> str:
    """Delete every note."""
    for p in NOTES.iterdir():
        p.unlink()
    return "deleted"


@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def big() -> str:
    """Return a lot of text."""
    return "x" * 50_000


@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def fail() -> str:
    """Always fails."""
    raise ValueError("no such thing")


if __name__ == "__main__":
    server.run()

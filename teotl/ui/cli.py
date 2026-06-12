"""Rich terminal UI for interactive agent sessions."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

logger = logging.getLogger(__name__)


class CliUI:
    """
    Rich terminal interface for Forge agents.

    Provides:
    - Markdown-rendered responses
    - Colored confirmation prompts for guardrails
    - Streaming output support
    - Slash command handling
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    async def confirm(self, message: str, *, title: str = "Confirm") -> bool:
        """Show a guardrail confirmation prompt."""
        self.console.print()
        self.console.print(
            Panel(
                message,
                title=f"[bold yellow]{title}[/bold yellow]",
                border_style="yellow",
            )
        )
        return Confirm.ask("[yellow]Allow this action?[/yellow]", console=self.console)

    async def display(self, message: str) -> None:
        """Display a message (renders markdown)."""
        self.console.print(Markdown(message))

    async def display_raw(self, message: str) -> None:
        """Display raw text without markdown rendering."""
        self.console.print(message)

    async def input(self, prompt: str = "You") -> str:
        """Get input from the user."""
        return Prompt.ask(f"[bold blue]{prompt}[/bold blue]", console=self.console)

    async def error(self, message: str) -> None:
        """Display an error."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def status(self, message: str = "Thinking...") -> rich.status.Status:
        """Show a spinner/status indicator."""
        return self.console.status(f"[dim]{message}[/dim]")

    def rule(self, title: str = "") -> None:
        """Print a horizontal rule."""
        self.console.rule(title)

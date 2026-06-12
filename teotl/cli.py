"""Teotl CLI: the main entry point."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

if TYPE_CHECKING:
    from teotl.core.agent import Agent
    from teotl.core.provider import Provider
    from teotl.ui.cli import CliUI

console = Console()


@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.option(
    "--policy", "-p", default="standard", help="Guardrail policy (minimal/standard/strict)"
)
@click.option("--model", "-m", default=None, help="Model to use")
@click.option("--provider", default="anthropic", help="LLM provider (anthropic/openai/ollama)")
@click.pass_context
def main(ctx: click.Context, verbose: bool, policy: str, model: str, provider: str) -> None:
    """Teotl — build safe, memory-aware AI agents."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(name)s %(message)s",
    )

    ctx.ensure_object(dict)
    ctx.obj["policy"] = policy
    ctx.obj["model"] = model
    ctx.obj["provider"] = provider

    if ctx.invoked_subcommand is None:
        # Default: start interactive REPL
        asyncio.run(_interactive(policy=policy, model=model, provider_name=provider))


async def _interactive(
    policy: str = "standard",
    model: str | None = None,
    provider_name: str = "anthropic",
) -> None:
    """Interactive REPL session."""
    from teotl.core.agent import Agent
    from teotl.ui.cli import CliUI

    ui = CliUI(console)

    # Resolve provider
    provider = _make_provider(provider_name, model)

    agent = Agent(
        provider=provider,
        instructions="You are Teotl, a helpful AI assistant.",
        policy=policy,
    )

    console.print("[bold]Teotl[/bold] — type /help for commands, /quit to exit\n")

    while True:
        try:
            user_input = await ui.input()
        except (KeyboardInterrupt, EOFError):
            console.print("\nGoodbye!")
            break

        if not user_input.strip():
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            handled = await _handle_command(user_input, agent, ui)
            if handled == "quit":
                break
            continue

        # Run agent
        with ui.status("Thinking..."):
            try:
                response = await agent.run(user_input, ui=ui)
            except Exception as e:
                await ui.error(str(e))
                continue

        await ui.display(response.text)
        console.print()


async def _handle_command(command: str, agent: Agent, ui: CliUI) -> str | None:
    """Handle slash commands."""
    cmd = command.strip().split()[0].lower()
    args = command[len(cmd) :].strip()

    if cmd in ("/quit", "/exit", "/q"):
        console.print("Goodbye!")
        return "quit"

    elif cmd == "/help":
        console.print("""[bold]Commands:[/bold]
  /help         Show this help
  /quit         Exit Forge
  /memory       Manage memories
  /skills       List available skills
  /policy       Show current policy
  /audit        Show recent audit log
  /undo         Undo last file change
""")

    elif cmd == "/skills":
        if agent.skills:
            console.print(agent.skills.get_descriptions())
        else:
            console.print("No skills loaded.")

    elif cmd == "/policy":
        if agent.guardrails:
            console.print(f"Policy level: [bold]{agent.guardrails.policy.level}[/bold]")
        else:
            console.print("Guardrails not configured.")

    elif cmd == "/memory":
        if agent.memory:
            count = await agent.memory.count()
            console.print(f"Memories stored: [bold]{count}[/bold]")
            if args == "list":
                memories = await agent.memory.list_all(limit=10)
                for mem in memories:
                    console.print(f"  [{mem.id[:8]}] {mem.content}")
        else:
            console.print("Memory not configured.")

    elif cmd == "/undo":
        # Delegate to undo extension if registered
        handler = agent._commands.get("/undo")
        if handler:
            result = await handler(args, ui)
            console.print(result)
        else:
            console.print("Undo extension not loaded.")

    else:
        console.print(f"Unknown command: {cmd}. Type /help for available commands.")

    return None


def _make_provider(name: str, model: str | None) -> Provider:
    """Create an LLM provider instance."""
    if name == "anthropic":
        from teotl.core.provider import AnthropicProvider

        return AnthropicProvider(model=model or "claude-sonnet-4-20250514")
    elif name == "openai":
        from teotl.core.provider import OpenAIProvider

        return OpenAIProvider(model=model or "gpt-4o")
    elif name == "ollama":
        from teotl.core.provider import OllamaProvider

        return OllamaProvider(model=model or "llama3")
    else:
        raise click.ClickException(f"Unknown provider: {name}")


# -------------------------------------------------------------------
# Subcommands
# -------------------------------------------------------------------


@main.command()
def init() -> None:
    """Initialize Forge in the current directory."""
    forge_dir = Path.home() / ".forge"
    forge_dir.mkdir(exist_ok=True)
    (forge_dir / "skills").mkdir(exist_ok=True)
    (forge_dir / "auth").mkdir(exist_ok=True)

    console.print("[green]✓[/green] Forge initialized at ~/.forge")
    console.print("  Run [bold]forge[/bold] to start an interactive session.")


@main.group()
def skills() -> None:
    """Manage skills."""
    pass


@skills.command("list")
def skills_list() -> None:
    """List available skills."""
    from teotl.primitives.skills.registry import SkillRegistry

    registry = SkillRegistry()
    if registry.registered_count == 0:
        console.print("No skills found. Add SKILL.md files to ~/.forge/skills/")
        return

    for name, meta in registry.skills.items():
        console.print(f"  [bold]{name}[/bold] — {meta.description}")


@main.group()
def memory() -> None:
    """Manage memories."""
    pass


@memory.command("list")
@click.option("--limit", "-n", default=20, help="Number of memories to show")
def memory_list(limit: int) -> None:
    """List stored memories."""

    async def _list() -> None:
        from teotl.primitives.memory.local import LocalMemory

        mem = LocalMemory()
        count = await mem.count()
        console.print(f"Total memories: [bold]{count}[/bold]\n")
        memories = await mem.list_all(limit=limit)
        for m in memories:
            tags = ", ".join(m.metadata.tags) if m.metadata.tags else ""
            console.print(f"  [{m.id[:8]}] {m.content}")
            if tags:
                console.print(f"           [dim]tags: {tags}[/dim]")
        mem.close()

    asyncio.run(_list())


@memory.command("search")
@click.argument("query")
def memory_search(query: str) -> None:
    """Search memories."""

    async def _search() -> None:
        from teotl.primitives.memory.local import LocalMemory

        mem = LocalMemory()
        results = await mem.recall(query, limit=10)
        if not results:
            console.print("No matching memories found.")
            return
        for m in results:
            console.print(f"  [{m.id[:8]}] {m.content}")
        mem.close()

    asyncio.run(_search())


@memory.command("forget")
@click.argument("memory_id")
def memory_forget(memory_id: str) -> None:
    """Delete a specific memory."""

    async def _forget() -> None:
        from teotl.primitives.memory.local import LocalMemory

        mem = LocalMemory()
        # Support short IDs (prefix match)
        all_memories = await mem.list_all(limit=1000)
        for m in all_memories:
            if m.id.startswith(memory_id):
                deleted = await mem.forget(m.id)
                if deleted:
                    console.print(f"[green]✓[/green] Deleted memory: {m.content[:60]}")
                    mem.close()
                    return
        console.print(f"Memory not found: {memory_id}")
        mem.close()

    asyncio.run(_forget())


@main.command()
def onboard() -> None:
    """Interactive onboarding wizard to set up your agent."""
    from teotl.cli.wizard import OnboardingWizard

    wizard = OnboardingWizard()
    try:
        wizard.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Setup cancelled.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ An error occurred: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""CLI commands for Forge agent framework."""

import sys

import click

from teotl.cli.memory import memory
from teotl.cli.security import main as security_main
from teotl.cli.wizard import OnboardingWizard
from teotl.cli.wizard import main as wizard_main

__all__ = ["memory", "OnboardingWizard", "wizard_main", "security_main", "main"]


@click.group()
@click.version_option(version="0.1.0", prog_name="teotl")
def main():
    """Forge - AI Agent Framework

    Build safe, memory-aware, context-efficient AI agents.
    """
    pass


@main.command()
@click.option("--agent", "-a", help="Agent ID to load workspace files from")
@click.option(
    "--skills", "-s", multiple=True, help="Skills to enable (comma-separated or multiple times)"
)
@click.option("--no-memory", is_flag=True, help="Disable memory system")
def chat(agent: str | None, skills: tuple[str, ...], no_memory: bool):
    """Start interactive chat mode.

    Examples:

      \b
      # Basic chat
      forge chat

      \b
      # Chat with skills (comma-separated)
      forge chat --skills filesystem,git,web

      \b
      # Chat with skills (repeated flags)
      forge chat --skills filesystem --skills git

      \b
      # Chat with specific agent (loads workspace files)
      forge chat --agent my-agent

      \b
      # Chat without memory
      forge chat --no-memory
    """
    import asyncio

    from teotl.cli.chat import chat_command

    # Handle comma-separated skills
    skill_list = []
    if skills:
        for skill_arg in skills:
            # Split by comma in case user specified: --skills filesystem,git,web
            skill_list.extend([s.strip() for s in skill_arg.split(",") if s.strip()])

    try:
        asyncio.run(
            chat_command(
                agent_id=agent,
                skills=skill_list if skill_list else None,
                no_memory=no_memory,
            )
        )
    except KeyboardInterrupt:
        click.echo("\n👋 Chat ended")
        sys.exit(0)


@main.command()
def onboard():
    """Run interactive onboarding wizard.

    Sets up your first agent with:
    - API key configuration
    - Agent personality and preferences
    - Skills selection
    - Security policies
    """
    wizard_main()


@main.command()
def wizard():
    """Alias for 'onboard' command."""
    wizard_main()


@main.command()
def security():
    """Manage security policies and configurations."""
    security_main()

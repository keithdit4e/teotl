"""`teotl sandbox`: manage named Docker sandbox sessions."""

from __future__ import annotations

import click


def _run(action, name: str) -> None:
    try:
        click.echo(action(name))
    except Exception as e:
        raise click.ClickException(str(e)) from e


@click.group()
def sandbox():
    """Manage named sandbox sessions (long-lived Docker containers)."""


@sandbox.command("list")
def list_cmd():
    """List sandbox sessions."""
    from teotl.core.tools.sandbox_session import list_sessions

    try:
        rows = list_sessions()
    except Exception as e:
        raise click.ClickException(f"Couldn't list sessions (is Docker running?): {e}") from e
    if not rows:
        click.echo("No sandbox sessions.")
        return
    width = max(len(r["name"]) for r in rows)
    for r in rows:
        kind = "named" if r["named"] == "yes" else "agent"
        click.echo(
            f"{r['name']:<{width}}  {r['state']:<8}  {kind:<5}  {r['image']}  ({r['status']})"
        )


@sandbox.command()
@click.argument("name")
def stop(name: str):
    """Stop a session. Its files and installs are kept; the next command restarts it."""
    from teotl.core.tools.sandbox_session import stop_session

    _run(stop_session, name)


@sandbox.command()
@click.argument("name")
def start(name: str):
    """Start a stopped session."""
    from teotl.core.tools.sandbox_session import start_session

    _run(start_session, name)


@sandbox.command()
@click.argument("name")
@click.confirmation_option(prompt="Delete this session's container and everything installed in it?")
def reset(name: str):
    """Delete a session's container; the next run starts clean. The safe zone isn't touched."""
    from teotl.core.tools.sandbox_session import reset_session

    _run(reset_session, name)

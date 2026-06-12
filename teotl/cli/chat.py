"""Interactive chat mode for Forge agents.

Provides a CLI interface to chat with agents in real-time.
"""

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.core.types import UI

logger = logging.getLogger(__name__)


class ChatUI(UI):
    """UI adapter for interactive chat mode."""

    def __init__(self, console: Console):
        self.console = console

    async def confirm(self, message: str, *, title: str = "") -> bool:
        """Request confirmation from user."""
        self.console.print(f"\n[yellow]🛡️  {message}[/yellow]")
        response = Prompt.ask("Confirm? (yes/no)", choices=["yes", "no"], default="no")
        return response.lower() == "yes"

    async def display(self, message: str) -> None:
        """Display a message to user."""
        self.console.print(message)

    async def input(self, prompt: str = "") -> str:
        """Get input from user."""
        return Prompt.ask(prompt or "Input")

    async def error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[red]❌ Error: {message}[/red]")


class ChatSession:
    """Interactive chat session with an agent."""

    def __init__(
        self,
        agent_id: str | None = None,
        skills: list[str] | None = None,
        use_memory: bool = True,
        session_dir: Path | None = None,
    ):
        """Initialize chat session.

        Args:
            agent_id: Agent identifier (for loading workspace files)
            skills: List of skills to enable
            use_memory: Whether to use memory system
            session_dir: Override session directory
        """
        self.console = Console()
        self.agent_id = agent_id or "chat"
        self.skills = skills or []
        self.use_memory = use_memory

        # Determine workspace and session directories
        forge_dir = Path.home() / ".forge"
        if agent_id:
            self.workspace_dir = forge_dir / "agents" / agent_id
            self.session_dir = session_dir or self.workspace_dir / "sessions"
        else:
            self.workspace_dir = None
            self.session_dir = session_dir or forge_dir / "chat-sessions"

        self.session_dir.mkdir(parents=True, exist_ok=True)

        # UI adapter
        self.ui = ChatUI(self.console)

        # Agent (initialized in start())
        self.agent: Agent | None = None

    def _load_instructions(self) -> str:
        """Load instructions from workspace files if available."""
        if not self.workspace_dir or not self.workspace_dir.exists():
            return "You are a helpful AI assistant."

        from teotl.daemon.executor import load_workspace_files

        workspace_instructions = load_workspace_files(self.workspace_dir)
        if workspace_instructions:
            return workspace_instructions

        return "You are a helpful AI assistant."

    def _display_welcome(self):
        """Display welcome message."""
        welcome_text = """
# 💬 Forge Interactive Chat

Welcome! You're now chatting with a Forge agent.

**Commands:**
- Type your message and press Enter
- `/exit` or `/quit` - Exit chat
- `/help` - Show this help
- `/skills` - List active skills
- `/memory` - Show recent memories
- `/clear` - Clear screen
"""

        if self.agent_id != "chat":
            welcome_text += f"\n**Agent:** {self.agent_id}"

        if self.skills:
            welcome_text += f"\n**Skills:** {', '.join(self.skills)}"

        welcome_text += "\n\nType your message below:\n"

        self.console.print(Markdown(welcome_text))

    def _display_help(self):
        """Display help information."""
        help_text = """
# Chat Commands

- `/exit`, `/quit` - Exit chat session
- `/help` - Show this help message
- `/skills` - List active skills and their descriptions
- `/memory` - Show recent memories (if memory enabled)
- `/clear` - Clear the screen

**Tips:**
- Skills activate automatically based on your request
- Confirmations may be required for destructive operations
- Use Ctrl+C as alternative to /exit
"""
        self.console.print(Markdown(help_text))

    async def _handle_command(self, command: str) -> bool:
        """Handle special commands.

        Args:
            command: Command string (e.g., "/help")

        Returns:
            True if should continue, False to exit
        """
        command = command.lower().strip()

        if command in ["/exit", "/quit"]:
            return False

        elif command == "/help":
            self._display_help()

        elif command == "/skills":
            if not self.agent:
                self.console.print("[yellow]Agent not initialized[/yellow]")
            elif not self.agent.skills:
                self.console.print("[yellow]No skills enabled[/yellow]")
            else:
                descriptions = self.agent.skills.get_descriptions()
                if not descriptions:
                    self.console.print("[yellow]No skill descriptions available[/yellow]")
                    self.console.print(f"Debug: skills object = {self.agent.skills}")
                    self.console.print(
                        f"Debug: registered skills = {list(self.agent.skills.skills.keys())}"
                    )
                else:
                    self.console.print(Markdown(descriptions))

        elif command == "/memory":
            if not self.agent or not self.agent.memory:
                self.console.print("[yellow]Memory not enabled[/yellow]")
            else:
                try:
                    memories = await self.agent.memory.recall("", limit=10)
                    if memories:
                        self.console.print("\n[bold]Recent Memories:[/bold]\n")
                        for i, mem in enumerate(memories, 1):
                            self.console.print(f"{i}. {mem.content[:100]}...")
                    else:
                        self.console.print("[yellow]No memories yet[/yellow]")
                except Exception as e:
                    self.console.print(f"[red]Error loading memories: {e}[/red]")

        elif command == "/clear":
            self.console.clear()
            self._display_welcome()

        else:
            self.console.print(f"[yellow]Unknown command: {command}[/yellow]")
            self.console.print("Type /help for available commands")

        return True

    async def start(self):
        """Start the interactive chat session."""
        # Initialize agent
        try:
            instructions = self._load_instructions()

            # Initialize memory if requested
            memory = None
            if self.use_memory:
                try:
                    from teotl.primitives.memory.local import LocalMemory

                    memory_dir = self.workspace_dir or (Path.home() / ".forge" / "chat-memory")
                    memory = LocalMemory(str(memory_dir))
                except Exception as e:
                    logger.warning(f"Failed to initialize memory: {e}")

            self.agent = Agent(
                provider=AnthropicProvider(),
                instructions=instructions,
                skills=self.skills,
                memory=memory,
                session_dir=self.session_dir,
            )

            logger.info(f"Chat session initialized: agent_id={self.agent_id}, skills={self.skills}")

        except Exception as e:
            self.console.print(f"[red]❌ Failed to initialize agent: {e}[/red]")
            sys.exit(1)

        # Display welcome
        self._display_welcome()

        # Chat loop
        try:
            while True:
                # Get user input
                try:
                    user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]").strip()
                except (KeyboardInterrupt, EOFError):
                    break

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    should_continue = await self._handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Send to agent
                try:
                    self.console.print("\n[bold magenta]Agent[/bold magenta] (thinking...)", end="")

                    response = await self.agent.run(user_input, ui=self.ui)

                    # Clear "thinking..." line
                    self.console.print("\r" + " " * 50 + "\r", end="")

                    # Display response
                    self.console.print("[bold magenta]Agent:[/bold magenta]")
                    self.console.print(
                        Panel(
                            Markdown(response.text),
                            border_style="magenta",
                            padding=(1, 2),
                        )
                    )

                    # Show cost if available
                    if hasattr(response, "cost") and response.cost:
                        self.console.print(f"[dim]Cost: ${response.cost:.4f}[/dim]")

                except KeyboardInterrupt:
                    self.console.print(
                        "\n[yellow]⏸️  Interrupted. Type /exit to quit or continue chatting.[/yellow]"
                    )
                    continue

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    self.console.print(f"\n[red]❌ Error: {e}[/red]")
                    self.console.print(
                        "[yellow]You can continue chatting or type /exit to quit[/yellow]"
                    )

        except KeyboardInterrupt:
            pass  # Clean exit

        finally:
            self.console.print("\n\n[bold cyan]👋 Chat session ended[/bold cyan]")
            if self.agent and self.agent.session:
                message_count = self.agent.session.message_count
                self.console.print(f"[dim]Messages exchanged: {message_count}[/dim]")


async def chat_command(
    agent_id: str | None = None,
    skills: list[str] | None = None,
    no_memory: bool = False,
) -> None:
    """Run interactive chat mode.

    Args:
        agent_id: Optional agent ID to load workspace files from
        skills: List of skills to enable
        no_memory: Disable memory system
    """
    session = ChatSession(
        agent_id=agent_id,
        skills=skills or [],
        use_memory=not no_memory,
    )

    await session.start()

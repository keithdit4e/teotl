"""Interactive onboarding wizard for Forge Agent.

This wizard provides an OpenClaw-style conversational setup experience,
guiding users through configuration without editing YAML files.

Usage:
    forge onboard
    python -m forge.cli.wizard
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from teotl.core.security import SecurityPolicy

console = Console()


class Color:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Color.BOLD}{Color.CYAN}{text}{Color.END}")
    print("=" * len(text))


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Color.GREEN}✅ {text}{Color.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Color.RED}❌ {text}{Color.END}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Color.BLUE}ℹ️  {text}{Color.END}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Color.YELLOW}⚠️  {text}{Color.END}")


def ask_question(question: str, default: str | None = None) -> str:
    """Ask a question and return the answer."""
    if default:
        prompt = f"{Color.BOLD}{question}{Color.END} [{default}]: "
    else:
        prompt = f"{Color.BOLD}{question}{Color.END}: "

    answer = input(prompt).strip()
    return answer if answer else (default or "")


def ask_choice(question: str, choices: list[str], default: str | None = None) -> str:
    """Ask user to choose from a list of options."""
    print(f"\n{Color.BOLD}{question}{Color.END}")
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")

    while True:
        answer = input(f"\nEnter your choice [1-{len(choices)}]: ").strip()

        if not answer and default:
            return default

        try:
            index = int(answer) - 1
            if 0 <= index < len(choices):
                return choices[index]
        except ValueError:
            pass

        print_error(f"Please enter a number between 1 and {len(choices)}")


def ask_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    answer = input(f"{Color.BOLD}{question}{Color.END} [{default_str}]: ").strip().lower()

    if not answer:
        return default

    return answer in ["y", "yes"]


def ask_multiselect(
    question: str, options: list[tuple[str, str]], defaults: list[str] | None = None
) -> list[str]:
    """Ask user to select multiple options.

    Args:
        question: Question to ask
        options: List of (key, description) tuples
        defaults: List of keys that should be selected by default

    Returns:
        List of selected option keys
    """
    defaults = defaults or []

    print(f"\n{Color.BOLD}{question}{Color.END}")
    print("(Enter numbers separated by spaces, or press Enter for defaults)")
    print()

    for i, (key, description) in enumerate(options, 1):
        default_marker = " (selected)" if key in defaults else ""
        print(f"  {i}. {Color.BOLD}{key}{Color.END}{default_marker}")
        print(f"     {description}")
        print()

    while True:
        answer = input(f"Select options [1-{len(options)}]: ").strip()

        # If empty, use defaults
        if not answer:
            return defaults if defaults else []

        # Parse selections
        try:
            selected_indices = [int(x.strip()) for x in answer.split()]

            # Validate all indices
            if all(1 <= idx <= len(options) for idx in selected_indices):
                return [options[idx - 1][0] for idx in selected_indices]
            else:
                print_error(f"Please enter numbers between 1 and {len(options)}")
        except ValueError:
            print_error("Please enter numbers separated by spaces (e.g., '1 3' or '2')")


def persist_api_key(key_name: str, key_value: str) -> tuple[bool, str]:
    """Persist API key to shell profile with automatic shell detection.

    Returns:
        (success, message) tuple
    """
    # Detect shell from environment
    shell = os.environ.get("SHELL", "")

    # Determine profile file based on shell
    profile_file = None
    shell_name = ""

    if "zsh" in shell:
        profile_file = Path.home() / ".zshrc"
        shell_name = "zsh"
    elif "bash" in shell:
        # Check for .bash_profile first (macOS), then .bashrc (Linux)
        bash_profile = Path.home() / ".bash_profile"
        bashrc = Path.home() / ".bashrc"
        profile_file = bash_profile if bash_profile.exists() else bashrc
        shell_name = "bash"
    elif "fish" in shell:
        profile_file = Path.home() / ".config" / "fish" / "config.fish"
        shell_name = "fish"
    else:
        # Unknown shell, try .bashrc as fallback
        profile_file = Path.home() / ".bashrc"
        shell_name = "bash (default)"

    # Create export line
    if shell_name == "fish":
        # Fish uses different syntax
        export_line = f'set -x {key_name} "{key_value}"'
    else:
        export_line = f'export {key_name}="{key_value}"'

    try:
        # Check if key already exists in file
        if profile_file.exists():
            with open(profile_file) as f:
                existing_content = f.read()

            # Check if this key is already set
            if f"{key_name}=" in existing_content or f"{key_name} " in existing_content:
                # Key exists - update it
                lines = existing_content.split("\n")
                updated = False
                new_lines = []

                for line in lines:
                    if line.strip().startswith(f"export {key_name}=") or line.strip().startswith(
                        f"set -x {key_name}"
                    ):
                        # Replace this line
                        new_lines.append(export_line)
                        updated = True
                    else:
                        new_lines.append(line)

                if updated:
                    with open(profile_file, "w") as f:
                        f.write("\n".join(new_lines))
                    return True, f"Updated {key_name} in {profile_file}"

        # Append to file
        profile_file.parent.mkdir(parents=True, exist_ok=True)

        with open(profile_file, "a") as f:
            # Add newline if file doesn't end with one
            if profile_file.exists() and profile_file.stat().st_size > 0:
                with open(profile_file, "rb") as check:
                    check.seek(-1, 2)
                    last_char = check.read(1)
                    if last_char != b"\n":
                        f.write("\n")

            # Add comment and export
            f.write("\n# Added by Forge Agent setup\n")
            f.write(f"{export_line}\n")

        return True, f"Added {key_name} to {profile_file}"

    except Exception as e:
        return False, f"Failed to persist key: {e}"


class OnboardingWizard:
    """Interactive onboarding wizard for Forge Agent."""

    def __init__(self):
        """Initialize the wizard."""
        self.config: dict[str, Any] = {}

    def run(self) -> dict[str, Any]:
        """Run the complete onboarding flow."""
        self._print_welcome()

        # 1. Choose execution pattern
        self._setup_execution_pattern()

        # 2. Choose provider(s) - conditional based on pattern
        self._setup_providers()

        # 3. Configure agent
        self._setup_agent()

        # 4. Configure memory & context management
        self._setup_memory()

        # 5. Configure skills
        self._setup_skills()

        # 6. Configure workspace
        self._setup_workspace()

        # 7. Configure security
        self._setup_security()

        # 8. Configure production features (harness)
        self._setup_harness_features()

        # 9. Setup daemon (if daemon pattern selected)
        if self.config.get("execution_pattern") in ["daemon", "hybrid"]:
            self._setup_daemon()

        # 10. Configure planner-worker (if planner-worker selected)
        if self.config.get("execution_pattern") in ["planner_worker", "hybrid"]:
            self._setup_planner_worker()

        # 11. Configure rate limits
        self._setup_rate_limits()

        # 12. Add tasks
        self._setup_tasks()

        # 13. Add missions
        self._setup_missions()

        # 14. Review and confirm
        if self._review_config():
            self._save_config()
            self._print_next_steps()

        return self.config

    def _print_welcome(self) -> None:
        """Print welcome message."""
        print("\n" + "=" * 60)
        print(f"{Color.BOLD}{Color.CYAN}🤖 Welcome to Forge Agent Onboarding!{Color.END}")
        print("=" * 60)
        print("\nThis wizard will help you set up your autonomous agent in just a few minutes.")
        print("You can always edit the generated config.yaml file later for advanced options.\n")

    def _setup_execution_pattern(self) -> None:
        """Choose execution pattern: daemon, planner-worker, or hybrid."""
        print_header("Step 1: Execution Pattern")

        print("\nHow will your agent work?")
        print()
        print(f"{Color.CYAN}1. Autonomous Background Agent (Daemon){Color.END}")
        print("   • Runs continuously in the background")
        print("   • Processes tasks and missions as they arrive")
        print("   • Good for: Email assistant, monitoring, scheduled tasks")
        print("   • Cost: Moderate (runs frequently)")
        print()
        print(f"{Color.CYAN}2. Planner-Worker for Complex Tasks{Color.END}")
        print("   • Creates detailed plan upfront (expensive model)")
        print("   • Executes steps systematically (cheap model)")
        print("   • Good for: Refactoring, migrations, complex features")
        print("   • Cost: Low (90% savings with smart planning)")
        print()
        print(f"{Color.CYAN}3. Hybrid (Both){Color.END}")
        print("   • Daemon handles routine work")
        print("   • Planner-Worker for complex tasks")
        print("   • Best of both worlds")
        print("   • Cost: Flexible based on usage")
        print()

        pattern = ask_choice(
            "Choose execution pattern:", ["daemon", "planner_worker", "hybrid"], default="daemon"
        )

        self.config["execution_pattern"] = pattern

        if pattern == "daemon":
            print_success("✅ Background daemon pattern selected")
        elif pattern == "planner_worker":
            print_success("✅ Planner-Worker pattern selected")
        else:
            print_success("✅ Hybrid pattern selected (daemon + planner-worker)")

    def _setup_providers(self) -> None:
        """Configure LLM provider(s) based on execution pattern."""
        pattern = self.config.get("execution_pattern", "daemon")

        if pattern == "daemon":
            # Single provider for daemon
            self._setup_daemon_provider()
        elif pattern == "planner_worker":
            # Two providers: planner and worker
            self._setup_planner_provider()
            self._setup_worker_provider()
        else:  # hybrid
            # All providers: daemon, planner, worker
            self._setup_daemon_provider()
            self._setup_planner_provider()
            self._setup_worker_provider()

    def _setup_daemon_provider(self) -> None:
        """Configure provider for daemon operations."""
        print_header("Step 2: Daemon Provider")

        print("\nForge supports multiple LLM providers. Each has different costs and capabilities:")
        print(f"{Color.CYAN}Anthropic{Color.END} - Claude models (recommended)")
        print("  • Cost: ~$0.60-1.50 per session")
        print("  • Best for: Complex reasoning, long conversations")
        print(f"\n{Color.CYAN}OpenAI{Color.END} - GPT models")
        print("  • Cost: ~$0.40-1.20 per session")
        print("  • Best for: General purpose, faster responses")
        print(f"\n{Color.CYAN}Ollama{Color.END} - Local models")
        print("  • Cost: $0 (runs on your machine)")
        print("  • Best for: Privacy, offline work, development")

        provider = ask_choice(
            "\nWhich provider would you like to use?",
            ["anthropic", "openai", "ollama"],
            default="anthropic",
        )

        self.config["provider"] = {"type": provider}

        if provider == "anthropic":
            self._setup_anthropic()
        elif provider == "openai":
            self._setup_openai()
        elif provider == "ollama":
            self._setup_ollama()

    def _setup_anthropic(self) -> None:
        """Configure Anthropic provider."""
        print_info("Setting up Anthropic (Claude)")

        # Model selection
        model = ask_choice(
            "\nWhich Claude model?",
            [
                "claude-sonnet-4-20250514 (recommended)",
                "claude-opus-4-20241113 (most capable)",
                "claude-haiku-4-20250401 (fastest)",
            ],
            default="claude-sonnet-4-20250514 (recommended)",
        )
        model_id = model.split(" ")[0]

        self.config["provider"]["model"] = model_id
        self.config["provider"]["api_key_env"] = "ANTHROPIC_API_KEY"

        # Check for API key
        if os.getenv("ANTHROPIC_API_KEY"):
            print_success("Found ANTHROPIC_API_KEY in environment")
        else:
            print_warning("ANTHROPIC_API_KEY not found in environment")
            print("\nTo get an API key:")
            print("  1. Go to https://console.anthropic.com/")
            print("  2. Sign up or log in")
            print("  3. Go to API Keys section")
            print("  4. Create a new API key")

            if ask_yes_no("\nDo you want to set it now?", default=True):
                api_key = ask_question("Enter your Anthropic API key")
                if api_key:
                    # Validate API key format
                    is_valid, error_msg = self._validate_api_key(api_key, "anthropic")
                    if not is_valid:
                        print_warning(f"⚠️  {error_msg}")
                        print_info("Continuing anyway, but verify your key is correct.")

                    # Set for current session
                    os.environ["ANTHROPIC_API_KEY"] = api_key
                    print_success("API key set for this session")

                    # Persist to shell profile
                    print()
                    if ask_yes_no(
                        "Save API key to your shell profile for future sessions?", default=True
                    ):
                        success, message = persist_api_key("ANTHROPIC_API_KEY", api_key)
                        if success:
                            print_success(message)
                            print_info(
                                "Restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
                            )
                        else:
                            print_error(message)
                            print_info("You can manually add it to your shell profile:")
                            print(f'  export ANTHROPIC_API_KEY="{api_key}"')

    def _setup_openai(self) -> None:
        """Configure OpenAI provider."""
        print_info("Setting up OpenAI (GPT)")

        model = ask_choice(
            "\nWhich GPT model?",
            ["gpt-4o (recommended)", "gpt-4-turbo", "gpt-4"],
            default="gpt-4o (recommended)",
        )
        model_id = model.split(" ")[0]

        self.config["provider"]["model"] = model_id
        self.config["provider"]["api_key_env"] = "OPENAI_API_KEY"

        if os.getenv("OPENAI_API_KEY"):
            print_success("Found OPENAI_API_KEY in environment")
        else:
            print_warning("OPENAI_API_KEY not found in environment")
            print("\nTo get an API key:")
            print("  1. Go to https://platform.openai.com/")
            print("  2. Sign up or log in")
            print("  3. Go to API Keys section")
            print("  4. Create a new API key")

            if ask_yes_no("\nDo you want to set it now?", default=True):
                api_key = ask_question("Enter your OpenAI API key")
                if api_key:
                    # Validate API key format
                    is_valid, error_msg = self._validate_api_key(api_key, "openai")
                    if not is_valid:
                        print_warning(f"⚠️  {error_msg}")
                        print_info("Continuing anyway, but verify your key is correct.")

                    # Set for current session
                    os.environ["OPENAI_API_KEY"] = api_key
                    print_success("API key set for this session")

                    # Persist to shell profile
                    print()
                    if ask_yes_no(
                        "Save API key to your shell profile for future sessions?", default=True
                    ):
                        success, message = persist_api_key("OPENAI_API_KEY", api_key)
                        if success:
                            print_success(message)
                            print_info(
                                "Restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
                            )
                        else:
                            print_error(message)
                            print_info("You can manually add it to your shell profile:")
                            print(f'  export OPENAI_API_KEY="{api_key}"')

    def _setup_ollama(self) -> None:
        """Configure Ollama provider."""
        print_info("Setting up Ollama (Local)")

        print("\nOllama runs models locally on your machine.")
        print("First, make sure Ollama is installed and running:")
        print("  • Install: https://ollama.ai/download")
        print("  • Run: ollama serve")

        model = ask_question("Which model would you like to use?", default="llama3.1:latest")
        self.config["provider"]["model"] = model

        print_info("\nMake sure you've pulled the model first:")
        print(f"  ollama pull {model}")

    def _setup_planner_provider(self) -> None:
        """Configure provider for planner (expensive, smart model)."""
        print_header("Step 2a: Planner Provider")

        print("\nThe planner creates detailed execution plans.")
        print("Use an expensive, capable model for best results.")
        print()
        print(f"{Color.CYAN}Recommended:{Color.END}")
        print("  • claude-sonnet-4 (best quality)")
        print("  • claude-opus-4 (most capable, slower)")
        print("  • gpt-4-turbo (OpenAI alternative)")
        print()

        provider_type = ask_choice(
            "Planner provider type:", ["anthropic", "openai"], default="anthropic"
        )

        if provider_type == "anthropic":
            model = ask_choice(
                "Planner model:", ["claude-sonnet-4", "claude-opus-4"], default="claude-sonnet-4"
            )

            # Get or reuse API key
            self._get_api_key("anthropic", "planner")

            self.config["planner_worker"] = self.config.get("planner_worker", {})
            self.config["planner_worker"]["planner"] = {
                "provider": model,
                "api_key_env": "ANTHROPIC_API_KEY",
            }
        else:  # openai
            model = ask_choice("Planner model:", ["gpt-4-turbo", "gpt-4"], default="gpt-4-turbo")

            self._get_api_key("openai", "planner")

            self.config["planner_worker"] = self.config.get("planner_worker", {})
            self.config["planner_worker"]["planner"] = {
                "provider": model,
                "api_key_env": "OPENAI_API_KEY",
            }

        print_success(f"✅ Planner configured: {model}")

    def _setup_worker_provider(self) -> None:
        """Configure provider for worker (cheap, fast model)."""
        print_header("Step 2b: Worker Provider")

        print("\nThe worker executes plan steps systematically.")
        print("Use a cheap, fast model to minimize costs.")
        print()
        print(f"{Color.CYAN}Recommended:{Color.END}")
        print("  • claude-haiku-4 (fastest, cheapest)")
        print("  • gpt-3.5-turbo (OpenAI alternative)")
        print()

        provider_type = ask_choice(
            "Worker provider type:", ["anthropic", "openai"], default="anthropic"
        )

        if provider_type == "anthropic":
            model = ask_choice(
                "Worker model:", ["claude-haiku-4", "claude-sonnet-4"], default="claude-haiku-4"
            )

            # Reuse API key from planner if same provider
            self._get_api_key("anthropic", "worker")

            self.config["planner_worker"]["worker"] = {
                "provider": model,
                "api_key_env": "ANTHROPIC_API_KEY",
            }
        else:  # openai
            model = ask_choice(
                "Worker model:", ["gpt-3.5-turbo", "gpt-4-turbo"], default="gpt-3.5-turbo"
            )

            self._get_api_key("openai", "worker")

            self.config["planner_worker"]["worker"] = {
                "provider": model,
                "api_key_env": "OPENAI_API_KEY",
            }

        print_success(f"✅ Worker configured: {model}")

    def _get_api_key(self, provider_type: str, role: str = "agent") -> str:
        """Get API key for a provider, reusing if already configured."""
        env_var = "ANTHROPIC_API_KEY" if provider_type == "anthropic" else "OPENAI_API_KEY"

        # Check if already have key from daemon provider
        if "provider" in self.config and self.config["provider"].get("type") == provider_type:
            if "api_key" in self.config["provider"]:
                print_info("Reusing API key from daemon provider")
                return self.config["provider"]["api_key"]

        # Check environment
        import os

        existing_key = os.environ.get(env_var)
        if existing_key:
            if ask_yes_no(f"\nFound {env_var} in environment. Use it?", default=True):
                print_success(f"✅ Using existing {env_var}")
                return existing_key

        # Ask for key
        print(f"\n{role.capitalize()} needs an API key for {provider_type}")
        key = ask_question(f"{env_var}:", default="")

        if key and ask_yes_no(f"\nSave {env_var} to shell profile?", default=True):
            success, msg = persist_api_key(env_var, key)
            if success:
                print_success(f"✅ {msg}")
            else:
                print_warning(f"⚠️  {msg}")

        return key

    def _setup_agent(self) -> None:
        """Configure agent settings."""
        print_header("Step 2: Agent Configuration")

        # Ask if single or multi-agent
        setup_type = ask_choice(
            "\nHow many agents do you want to set up?",
            ["Single agent (recommended for beginners)", "Multiple agents (advanced)"],
            default="Single agent (recommended for beginners)",
        )

        if "Multiple" in setup_type:
            self._setup_multiple_agents()
        else:
            self._setup_single_agent()

    def _setup_single_agent(self) -> None:
        """Configure a single agent."""
        # Agent ID
        default_id = "my-agent"
        agent_id = ask_question(
            "\nWhat should we call your agent? (lowercase, no spaces)", default=default_id
        )
        if not agent_id:
            agent_id = default_id

        # Instructions
        print("\nAgent instructions guide how your agent behaves.")
        print("Examples:")
        print("  • 'You are a helpful email assistant'")
        print("  • 'You are a code review bot'")
        print("  • 'You are a personal task manager'")

        instructions = ask_question(
            "\nWhat should your agent do?",
            default="You are a helpful AI assistant that helps with daily tasks",
        )

        # Ask about work management types
        print()
        work_types = ask_multiselect(
            "What will your agent work on? (select all that apply)",
            [
                (
                    "Goals",
                    "Continuous autonomous objectives - Agent decides what to do next\n     Example: 'Improve code quality' → agent picks specific improvements\n     Creates: GOALS.md (simple, editable)",
                ),
                (
                    "Missions",
                    "Scheduled recurring tasks - Runs on a timer (hourly, daily, weekly)\n     Example: 'Send status report every day at 9am'\n     Creates: MISSIONS.md",
                ),
                (
                    "Tasks",
                    "One-time priority-based work - Added manually or via API\n     Example: 'Fix critical bug' with URGENT priority\n     Creates: Task queue",
                ),
            ],
            defaults=["Goals"],  # Default to Goals for simplicity
        )

        self.config["agent"] = {
            "agent_id": agent_id,
            "instructions": instructions,
            "auto_approve": True,  # Required for autonomous execution
            "work_types": work_types,  # Store what types of work this agent does
        }

    def _setup_multiple_agents(self) -> None:
        """Configure multiple agents."""
        print_info("\nMulti-agent mode lets you run specialized agents that can work together.")
        print("\nCommon setups:")
        print("  • Personal + Work agents (separate contexts)")
        print("  • Email + Slack + GitHub agents (specialized skills)")
        print("  • Research + Writing + Editing agents (workflow)")

        agents = {}
        base_port = 8000

        # Suggest some common agent types
        if ask_yes_no("\nUse a preset multi-agent configuration?", default=True):
            preset = ask_choice(
                "Choose a preset",
                [
                    "Personal + Work (2 agents)",
                    "Personal + Work + Research (3 agents)",
                    "Custom (I'll configure each agent)",
                ],
                default="Personal + Work (2 agents)",
            )

            if "Personal + Work (2 agents)" in preset:
                agents = {
                    "personal": {
                        "agent_id": "personal",
                        "instructions": "You are my personal assistant. Help with personal tasks, emails, and scheduling.",
                        "workspace": "~/.forge/agents/personal",
                        "auto_approve": True,
                        "port": base_port,
                    },
                    "work": {
                        "agent_id": "work",
                        "instructions": "You are my work assistant. Help with work tasks, meetings, and professional communications.",
                        "workspace": "~/.forge/agents/work",
                        "auto_approve": True,
                        "port": base_port + 1,
                    },
                }
            elif "Personal + Work + Research" in preset:
                agents = {
                    "personal": {
                        "agent_id": "personal",
                        "instructions": "You are my personal assistant. Help with personal tasks and scheduling.",
                        "workspace": "~/.forge/agents/personal",
                        "auto_approve": True,
                        "port": base_port,
                        "work_types": ["Tasks"],  # Personal assistant uses tasks
                    },
                    "work": {
                        "agent_id": "work",
                        "instructions": "You are my work assistant. Help with work tasks and professional communications.",
                        "workspace": "~/.forge/agents/work",
                        "auto_approve": True,
                        "port": base_port + 1,
                        "work_types": [
                            "Tasks",
                            "Missions",
                        ],  # Work assistant uses tasks + scheduled reports
                    },
                    "research": {
                        "agent_id": "research",
                        "instructions": "You are my research assistant. Help gather information, summarize findings, and analyze data.",
                        "workspace": "~/.forge/agents/research",
                        "auto_approve": True,
                        "port": base_port + 2,
                        "work_types": ["Goals"],  # Research uses continuous goals
                    },
                }
            else:
                # Custom configuration
                agents = self._create_custom_agents(base_port)
        else:
            # Custom configuration
            agents = self._create_custom_agents(base_port)

        self.config["agents"] = agents

    def _create_custom_agents(self, base_port: int = 8000) -> dict:
        """Create custom agent configurations interactively."""
        agents = {}
        port_offset = 0

        print_info("\nLet's create your agents one by one.")

        while True:
            print()
            agent_id = ask_question(
                "Agent ID (lowercase, no spaces)", default=f"agent-{len(agents) + 1}"
            )

            if not agent_id:
                agent_id = f"agent-{len(agents) + 1}"

            # Check for duplicate IDs
            if agent_id in agents:
                print_warning(f"Agent ID '{agent_id}' already exists. Choose a different one.")
                continue

            instructions = ask_question(
                f"What should '{agent_id}' do?",
                default="You are a helpful AI assistant",
            )

            # Ask about work types
            print()
            work_types = ask_multiselect(
                f"What will '{agent_id}' work on?",
                [
                    ("Goals", "Continuous objectives"),
                    ("Missions", "Scheduled tasks"),
                    ("Tasks", "One-time priority work"),
                ],
                defaults=["Goals"],
            )

            workspace = ask_question(
                "Workspace directory",
                default=f"~/.forge/agents/{agent_id}",
            )

            agents[agent_id] = {
                "agent_id": agent_id,
                "instructions": instructions,
                "workspace": workspace,
                "auto_approve": True,
                "port": base_port + port_offset,
                "work_types": work_types,
            }

            port_offset += 1

            print_success(f"Added agent: {agent_id}")

            if not ask_yes_no("\nAdd another agent?", default=False):
                break

        if not agents:
            # If user didn't create any, create a default one
            print_warning("No agents created. Adding a default agent.")
            agents["main"] = {
                "agent_id": "main",
                "instructions": "You are a helpful AI assistant",
                "workspace": "~/.forge/agents/main",
                "auto_approve": True,
                "port": base_port,
                "work_types": ["Goals"],  # Default to Goals
            }

        return agents

    def _setup_memory(self) -> None:
        """Configure memory system and context management."""
        print_header("Step 3: Memory & Context Management")

        print("\nMemory helps your agent:")
        print("  • Remember past conversations and decisions")
        print("  • Learn from experience over time")
        print("  • Maintain context across sessions")
        print("  • Automatically manage context window (prevent token overflow)")
        print()
        print("Memory uses a local SQLite database stored in your agent's workspace.")

        if ask_yes_no("\nEnable memory for your agent?", default=True):
            # Configure memory
            memory_config = {
                "enabled": True,
                "backend": "local",
            }

            # Store in appropriate config section
            if "agent" in self.config:
                self.config["agent"]["memory"] = memory_config
            elif "agents" in self.config:
                # Enable for all agents
                for agent_id in self.config["agents"]:
                    self.config["agents"][agent_id]["memory"] = memory_config

            print_success("Memory enabled")

            # Janitor (context management) auto-enables with memory
            print()
            print_info("Context Management (Janitor) will be automatically enabled.")
            print("The janitor automatically compacts context to prevent token overflow.")
            print()
            print("Default settings:")
            print("  • Compact every 15 turns")
            print("  • Max context: Auto-detected from model")
            print("  • Decision logging: Enabled")

            if ask_yes_no("\nCustomize context management settings?", default=False):
                self._setup_janitor_advanced()
            else:
                # Use defaults
                if "agent" in self.config:
                    self.config["agent"]["janitor"] = {
                        "enabled": True,
                        "compact_every": 15,
                    }
                elif "agents" in self.config:
                    for agent_id in self.config["agents"]:
                        self.config["agents"][agent_id]["janitor"] = {
                            "enabled": True,
                            "compact_every": 15,
                        }

            print_success("Context management configured")
        else:
            print_info("Memory disabled. Agent will not persist context across sessions.")

    def _setup_janitor_advanced(self) -> None:
        """Advanced janitor configuration for power users."""
        print()
        print_info("Advanced Context Management Settings")

        # Compaction frequency
        compact_every = int(
            ask_question("\nCompact context every N turns (default: 15)", default="15")
        )

        # Context limit
        print("\nMax context tokens before compaction:")
        print("  • Auto-detect - Based on your model (recommended)")
        print("  • Custom - Set a specific limit")

        use_auto_limit = ask_yes_no("Use auto-detect?", default=True)

        janitor_config = {
            "enabled": True,
            "compact_every": compact_every,
        }

        if not use_auto_limit:
            max_tokens = int(ask_question("Max context tokens", default="100000"))
            janitor_config["max_context_tokens"] = max_tokens

        # Apply to agents
        if "agent" in self.config:
            self.config["agent"]["janitor"] = janitor_config
        elif "agents" in self.config:
            for agent_id in self.config["agents"]:
                self.config["agents"][agent_id]["janitor"] = janitor_config

    def _setup_skills(self) -> None:
        """Configure agent skills."""
        print_header("Step 4: Skills Configuration")

        print("\nSkills are capabilities your agent can use to interact with the world:")
        print()

        # Show available skills
        available_skills = [
            ("Filesystem", "Read/write files, create directories, search code"),
            ("Git", "Version control: commits, branches, diffs, merges"),
            ("Web", "Fetch URLs, search the web, scrape content"),
            ("Claude_Code", "AI coding assistant for refactoring, features, bug fixes"),
            ("Email", "Read and send emails (requires SMTP configuration)"),
            ("GitHub", "Create issues, PRs, review code, manage repositories"),
            ("Slack", "Send messages, read channels, manage workspace"),
            ("Database", "Query SQL databases, run migrations"),
        ]

        print("Available skills:")
        for name, desc in available_skills:
            print(f"  • {Color.CYAN}{name}{Color.END} - {desc}")

        print()
        skills = ask_multiselect(
            "Which skills should your agent have?", available_skills, defaults=["Filesystem", "Web"]
        )

        # Convert to lowercase for config
        skills_list = [s.lower() for s in skills]

        # Validate skills exist
        available_skills_check, missing_skills = self._validate_skills(skills_list)

        if missing_skills:
            print()
            print_warning("⚠️  The following skills are not available:")
            for skill in missing_skills:
                print(f"  • {skill}")
            print()
            print("These skills will be skipped. Ensure skill files exist in skills/ directory.")
            print()

            # Remove missing skills from list
            skills_list = available_skills_check

            if not skills_list:
                print_error("No valid skills selected. Agent will have no capabilities.")
                if not ask_yes_no("Continue anyway?", default=False):
                    sys.exit(1)

        # Apply to agents
        if "agent" in self.config:
            self.config["agent"]["skills"] = skills_list
        elif "agents" in self.config:
            # For multi-agent, ask per agent or apply to all
            if ask_yes_no("\nApply same skills to all agents?", default=True):
                for agent_id in self.config["agents"]:
                    self.config["agents"][agent_id]["skills"] = skills_list
            else:
                # Configure per agent
                for agent_id in self.config["agents"]:
                    print(f"\nSkills for agent '{agent_id}':")
                    agent_skills = ask_multiselect(
                        f"Skills for {agent_id}",
                        [name for name, _ in available_skills],
                        defaults=skills_list,
                    )
                    self.config["agents"][agent_id]["skills"] = [s.lower() for s in agent_skills]

        print_success(f"Configured skills: {', '.join(skills)}")

    def _setup_workspace(self) -> None:
        """Configure workspace directory."""
        print_header("Step 5: Workspace Configuration")

        print("\nYour workspace is where your agent can access your files and projects.")
        print("This helps your agent:")
        print("  • Understand your project structure")
        print("  • Access relevant files for context")
        print("  • Provide workspace-aware assistance")
        print()
        print("The agent will have READ access to this directory by default.")
        print("Write access is controlled by security policies.")

        default_workspace = str(Path.home() / "workspace")

        workspace = ask_question("\nWorkspace directory", default=default_workspace)

        # Expand and validate
        workspace_path = Path(workspace).expanduser()

        if not workspace_path.exists():
            if ask_yes_no(f"\n{workspace_path} doesn't exist. Create it?", default=True):
                workspace_path.mkdir(parents=True, exist_ok=True)
                print_success(f"Created workspace: {workspace_path}")
            else:
                print_warning("Workspace directory will be created when needed")

        # Store in config
        self.config["workspace"] = {
            "path": str(workspace_path),
            "read_access": True,
            "write_access": False,  # Controlled by security policy
        }

        print_success(f"Workspace configured: {workspace_path}")

    def _setup_harness_features(self) -> None:
        """Configure production safety features (harness)."""
        print_header("Step 7: Production Safety Features")

        print("\nProduction features provide safety and reliability for autonomous agents:")
        print()
        print(f"  {Color.CYAN}Cost Tracking{Color.END}")
        print("    • Real-time LLM cost monitoring")
        print("    • Per-hour, per-day, per-month budget limits")
        print("    • Automatic shutdown when budget exceeded")
        print()
        print(f"  {Color.CYAN}Checkpoints{Color.END}")
        print("    • Automatic progress snapshots")
        print("    • Recover from crashes or failures")
        print("    • Resume long-running tasks where they left off")
        print()
        print(f"  {Color.CYAN}Heartbeat Monitoring{Color.END}")
        print("    • Detect stuck or frozen agents")
        print("    • Alert on consecutive errors")
        print("    • Automatic recovery actions")
        print()
        print(f"  {Color.CYAN}State Management{Color.END}")
        print("    • Persistent agent state across restarts")
        print("    • Remember current phase and progress")
        print("    • Survive system reboots")

        if ask_yes_no("\nEnable production features?", default=True):
            # Default to enabling critical features
            default_features = ["Cost Tracking", "State Management"]

            features = ask_multiselect(
                "\nWhich features to enable?",
                ["Cost Tracking", "Checkpoints", "Heartbeat Monitoring", "State Management"],
                defaults=default_features,
            )

            harness_config = {
                "cost_tracking": "Cost Tracking" in features,
                "checkpoints": "Checkpoints" in features,
                "heartbeat": "Heartbeat Monitoring" in features,
                "state": "State Management" in features,
            }

            # Apply to agents
            if "agent" in self.config:
                self.config["agent"]["harness"] = harness_config
            elif "agents" in self.config:
                for agent_id in self.config["agents"]:
                    self.config["agents"][agent_id]["harness"] = harness_config

            enabled_features = [f for f in features]
            print_success(f"Enabled: {', '.join(enabled_features)}")
        else:
            print_info("Production features disabled (can be enabled later in config)")

    def _setup_security(self) -> None:
        """Configure security policy."""
        print_header("Step 6: Security & Compliance")

        print("\nForge provides defense-in-depth security with:")
        print(f"  {Color.BOLD}Policy Layer{Color.END} - Access control and intent validation")
        print(f"  {Color.BOLD}Sandbox Layer{Color.END} - OS-level isolation and enforcement")
        print(f"  {Color.BOLD}Compliance{Color.END} - GDPR, SOC2, HIPAA support")

        print("\n" + "─" * 60)
        print("\nSecurity presets (Policy + Sandbox):")
        print(f"\n  {Color.CYAN}Moderate (Recommended){Color.END}")
        print("    Policy:")
        print("      • Common domains allowed (GitHub, Google, Wikipedia)")
        print("      • Agent workspace + Documents (read-only)")
        print("      • Cost limits: $5/hour, $50/day")
        print("    Sandbox:")
        print("      • Filesystem isolation (allowed paths only)")
        print("      • Network filtering (domain allowlist)")
        print("      • Resource limits: 1GB RAM, 5min CPU")

        print(f"\n  {Color.YELLOW}Strict{Color.END}")
        print("    Policy:")
        print("      • Minimal network access (AI providers only)")
        print("      • Agent workspace + /tmp only")
        print("      • Lower cost limits: $1/hour, $10/day")
        print("    Sandbox:")
        print("      • Strict filesystem isolation")
        print("      • Strict network filtering")
        print("      • Lower resource limits: 512MB RAM, 3min CPU")

        print(f"\n  {Color.GREEN}Permissive{Color.END}")
        print("    Policy:")
        print("      • Most domains allowed")
        print("      • Broader filesystem access")
        print("      • Higher cost limits: $10/hour, $100/day")
        print("    Sandbox:")
        print("      • Resource limits only (no file/network sandbox)")
        print("      • Higher limits: 2GB RAM, 10min CPU")

        preset = ask_choice(
            "\nWhich security preset?",
            ["moderate (recommended)", "strict", "permissive"],
            default="moderate (recommended)",
        )

        # Extract preset name
        preset_name = preset.split()[0]  # "moderate", "strict", or "permissive"

        self.config["security"] = {"preset": preset_name}

        # Ask about compliance features
        print("\nCompliance features add specialized logging and controls:")

        if ask_yes_no("\nEnable compliance features?", default=False):
            print_info("Select compliance frameworks to enable:")

            compliance = {}

            if ask_yes_no("  GDPR (EU data privacy)?", default=False):
                compliance["gdpr_enabled"] = True

            if ask_yes_no("  SOC2 (security controls)?", default=False):
                compliance["soc2_enabled"] = True

            if ask_yes_no("  HIPAA (healthcare data)?", default=False):
                compliance["hipaa_enabled"] = True

            if compliance:
                self.config["security"]["compliance"] = compliance
                print_success(f"Enabled: {', '.join(k.split('_')[0].upper() for k in compliance)}")
        else:
            print_info("Compliance features disabled (can be enabled later)")

        # Ask about audit log level
        print("\nAudit log detail levels:")
        print("  • minimal - Only security violations")
        print("  • standard - Violations + tool calls + costs (recommended)")
        print("  • detailed - Standard + LLM prompts (PII redacted)")
        print("  • paranoid - Everything including full prompts")

        log_level = ask_choice(
            "\nAudit log level?",
            ["standard (recommended)", "minimal", "detailed", "paranoid"],
            default="standard (recommended)",
        )

        self.config["security"]["log_level"] = log_level.split()[0]

        print_success(f"Security configured: {preset_name} preset, {log_level.split()[0]} logging")

    def _setup_daemon(self) -> None:
        """Configure daemon settings."""
        print_header("Step 8: Daemon Configuration")

        print("\nThe daemon runs in the background and executes tasks autonomously.")

        # Poll interval
        print("\nPoll interval determines how often the daemon checks for work:")
        print("  • 30 seconds - Responsive (recommended)")
        print("  • 60 seconds - Balanced")
        print("  • 300 seconds - Battery-friendly")

        interval_choice = ask_choice(
            "\nHow often should the daemon check for work?",
            ["30 seconds (recommended)", "60 seconds", "300 seconds", "Custom"],
            default="30 seconds (recommended)",
        )

        if "Custom" in interval_choice:
            interval = int(ask_question("Enter interval in seconds", default="30"))
        else:
            interval = int(interval_choice.split()[0])

        # Data directory (only for single agent)
        if "agent" in self.config:
            default_dir = f"~/.forge/{self.config['agent']['agent_id']}"
            data_dir = ask_question("\nWhere should data be stored?", default=default_dir)
            self.config["daemon"] = {"poll_interval": interval, "data_dir": data_dir}
        else:
            # Multi-agent - each agent has its own workspace
            self.config["daemon"] = {"poll_interval": interval}
            print_info("Each agent will use its own workspace directory.")

    def _setup_planner_worker(self) -> None:
        """Configure planner-worker specific settings."""
        print_header("Step 9: Planner-Worker Configuration")

        print("\nPlanner-Worker uses two-phase execution:")
        print("  1. Planner creates detailed plan (expensive model, runs once)")
        print("  2. Worker executes steps (cheap model, runs many times)")
        print()
        print("This provides 90% cost savings for complex tasks!")
        print()

        # Ensure planner_worker config exists
        if "planner_worker" not in self.config:
            self.config["planner_worker"] = {}

        # Worker skills
        print(f"{Color.CYAN}Worker Skills{Color.END}")
        print("\nWhich skills should the worker have?")
        print("(The worker executes plan steps and may need various capabilities)")
        print()

        # Use same skill selection as before
        available_skills = [
            ("Filesystem", "Read/write files, create directories, search code"),
            ("Git", "Version control: commits, branches, diffs, merges"),
            ("Web", "Fetch URLs, search the web, scrape content"),
            ("Claude_Code", "AI coding assistant for refactoring, features, bug fixes"),
            ("Email", "Read and send emails (requires SMTP configuration)"),
            ("GitHub", "Create issues, PRs, review code, manage repositories"),
            ("Slack", "Send messages, read channels, manage workspace"),
            ("Database", "Query SQL databases, run migrations"),
        ]

        print("Available skills:")
        for name, desc in available_skills:
            print(f"  • {Color.CYAN}{name}{Color.END} - {desc}")

        print()
        worker_skills = ask_multiselect(
            "Worker skills:",
            [name for name, _ in available_skills],
            defaults=["Filesystem", "Git", "Claude_Code"],
        )

        # Convert to lowercase for config
        self.config["planner_worker"]["worker"]["skills"] = [s.lower() for s in worker_skills]

        print_success(f"✅ Worker skills: {', '.join(worker_skills)}")

        # Worker policy
        print()
        print(f"{Color.CYAN}Worker Security Policy{Color.END}")
        print("\nSecurity policy controls what the worker can do:")
        print()
        print("  • autonomous-dev (recommended for coding)")
        print("    - Read/write files in workspace")
        print("    - Run git commands")
        print("    - Execute builds and tests")
        print()
        print("  • strict (limited access, safe)")
        print("    - Read-only file access")
        print("    - No dangerous operations")
        print()
        print("  • permissive (full access, powerful)")
        print("    - All filesystem operations")
        print("    - System commands")
        print()

        policy = ask_choice(
            "Worker security policy:",
            ["autonomous-dev", "strict", "permissive"],
            default="autonomous-dev",
        )

        self.config["planner_worker"]["worker"]["policy"] = policy
        print_success(f"✅ Policy: {policy}")

        # spec-kit configuration
        print()
        print(f"{Color.CYAN}Formal Specifications with spec-kit{Color.END}")
        print("\nspec-kit creates formal specifications based on your project constitution.")
        print("This ensures plans align with project values, architecture, and standards.")
        print()
        print("Benefits:")
        print("  • Constitution-driven planning (values enforced automatically)")
        print("  • Structured task lists with acceptance criteria")
        print("  • Dependency analysis for execution order")
        print("  • Verification against requirements")
        print()

        use_spec_kit = ask_yes_no("Use spec-kit for formal specifications?", default=True)

        # Store spec-kit configuration
        if "planner" not in self.config["planner_worker"]:
            self.config["planner_worker"]["planner"] = {}

        self.config["planner_worker"]["planner"]["use_spec_kit"] = use_spec_kit

        if use_spec_kit:
            print_success("✅ spec-kit enabled for planner")

            # Ask about constitution files
            print()
            print("Constitution files define your project values:")
            print("  • CONSTITUTION.md - Core values and principles")
            print("  • ARCHITECTURE.md - Design patterns and structure")
            print("  • STANDARDS.md - Coding conventions and practices")
            print("  • SECURITY.md - Security policies and requirements")
            print()

            create_constitution = ask_yes_no("Create constitution template files?", default=True)

            self.config["planner_worker"]["planner"]["create_constitution_templates"] = (
                create_constitution
            )

            if create_constitution:
                print_success("✅ Constitution templates will be created")
        else:
            print_success("✅ Using standard planning (no spec-kit)")

        # Planner instructions (updated based on spec-kit)
        print()
        if ask_yes_no("Customize planner instructions?", default=False):
            print("\nPlanner instructions guide how plans are created.")

            if use_spec_kit:
                default_instructions = """You are an expert planner that creates formal specifications.

When planning features:
1. Read project constitution (CONSTITUTION.md, ARCHITECTURE.md, STANDARDS.md)
2. Use spec-kit to create formal specification
3. Extract structured task list from spec (with acceptance criteria)
4. Ensure tasks meet constitution requirements
5. Include verification criteria for each task

Use spec-kit commands:
- spec-kit create <feature> --constitution CONSTITUTION.md
- spec-kit extract-tasks <spec> --format json
- spec-kit verify <spec> --implementation src/"""
            else:
                default_instructions = "Create detailed, atomic execution plans with verification"

            print("\nDefault instructions:")
            print(f"{default_instructions}")
            print()

            planner_instructions = ask_question(
                "Planner instructions:", default=default_instructions
            )
            self.config["planner_worker"]["planner"]["instructions"] = planner_instructions
        else:
            if use_spec_kit:
                self.config["planner_worker"]["planner"][
                    "instructions"
                ] = """You are an expert planner that creates formal specifications.

When planning features:
1. Read project constitution (CONSTITUTION.md, ARCHITECTURE.md, STANDARDS.md)
2. Use spec-kit to create formal specification
3. Extract structured task list from spec (with acceptance criteria)
4. Ensure tasks meet constitution requirements
5. Include verification criteria for each task

Use spec-kit commands:
- spec-kit create <feature> --constitution CONSTITUTION.md
- spec-kit extract-tasks <spec> --format json
- spec-kit verify <spec> --implementation src/"""
            else:
                self.config["planner_worker"]["planner"]["instructions"] = (
                    "Create detailed, atomic execution plans with verification"
                )

        # Worker instructions (conditional on skills)
        has_claude_code = "claude_code" in [s.lower() for s in worker_skills]

        # Build default worker instructions based on skills
        if has_claude_code:
            default_worker_instructions = """Execute plan steps carefully and verify results.

When using claude_code skill for coding tasks:
1. Use /clear when starting a NEW FEATURE (unrelated to previous task)
2. Let complex tasks trigger plan mode automatically (multi-file changes)
3. Do NOT use /clear mid-feature or when tasks are related
4. Review changes before committing

Context management:
- /clear: Start fresh for new features
- Plan mode: Automatically used for complex multi-step tasks
- /diff: Review all changes before proceeding"""
        else:
            default_worker_instructions = "Execute plan steps carefully and verify results"

        if ask_yes_no("Customize worker instructions?", default=False):
            print("\nWorker instructions guide how steps are executed.")
            if has_claude_code:
                print("\nDefault (with claude_code skill):")
                print(default_worker_instructions)
            else:
                print(f"Default: '{default_worker_instructions}'")
            print()

            worker_instructions = ask_question(
                "Worker instructions:", default=default_worker_instructions
            )
            self.config["planner_worker"]["worker"]["instructions"] = worker_instructions
        else:
            self.config["planner_worker"]["worker"]["instructions"] = default_worker_instructions

        # Harness features
        print()
        print(f"{Color.CYAN}Harness Features{Color.END}")
        print("\nEnable production safety features?")
        print()

        harness_config = {}

        if ask_yes_no("Enable cost tracking?", default=True):
            harness_config["cost_tracking"] = True

        if ask_yes_no("Enable checkpoints (recovery from failures)?", default=True):
            harness_config["checkpoints"] = True

        if ask_yes_no("Enable heartbeat monitoring (stuck detection)?", default=True):
            harness_config["heartbeat"] = True

        if ask_yes_no("Enable state persistence?", default=True):
            harness_config["state"] = True

        self.config["planner_worker"]["harness"] = harness_config

        enabled_features = [k for k, v in harness_config.items() if v]
        if enabled_features:
            print_success(f"✅ Harness features: {', '.join(enabled_features)}")

        # Workflow settings
        print()
        print(f"{Color.CYAN}Workflow Settings{Color.END}")

        workflow_config = {}

        workflow_config["require_approval_for_plan"] = ask_yes_no(
            "\nRequire approval after plan creation?", default=False
        )

        workflow_config["require_approval_for_continuation"] = ask_yes_no(
            "Require approval every N steps?", default=False
        )

        workflow_config["halt_on_critical_escalation"] = ask_yes_no(
            "Halt execution on critical errors?", default=True
        )

        self.config["planner_worker"]["workflow"] = workflow_config

        print_success("✅ Planner-Worker configured!")

    def _setup_rate_limits(self) -> None:
        """Configure rate limits."""
        print_header("Step 9: Rate Limits")

        print("\nRate limits prevent runaway costs from your LLM provider.")
        print("These are safety limits to protect your budget.")

        if ask_yes_no("\nDo you want to set rate limits?", default=True):
            print("\nRecommended limits:")
            print("  • Requests: 10 per minute (prevents API abuse)")
            print("  • Cost: $0.50 per minute (prevents expensive mistakes)")

            use_defaults = ask_yes_no("\nUse recommended limits?", default=True)

            if use_defaults:
                max_requests = 10
                max_cost = 0.50
            else:
                max_requests = int(ask_question("Max requests per minute", default="10"))
                max_cost = float(ask_question("Max cost per minute ($)", default="0.50"))

            self.config["rate_limits"] = {
                "max_requests_per_minute": max_requests,
                "max_cost_per_minute": max_cost,
            }
        else:
            print_warning("Skipping rate limits (not recommended for production)")

    def _setup_tasks(self) -> None:
        """Configure initial tasks."""
        print_header("Step 10: Tasks")

        print("\nTasks are one-time work items with priorities:")
        print("  • CRITICAL - Interrupt everything")
        print("  • URGENT - Interrupt interruptible missions")
        print("  • HIGH - Run before missions")
        print("  • NORMAL - Run after missions")
        print("  • LOW - Run when nothing else is pending")

        self.config["tasks"] = []

        if ask_yes_no("\nDo you want to add some initial tasks?", default=True):
            while True:
                task = self._create_task()
                if task:
                    self.config["tasks"].append(task)
                    print_success(f"Added task: [{task['priority']}] {task['description']}")

                if not ask_yes_no("\nAdd another task?", default=False):
                    break

        if not self.config["tasks"]:
            # Add example tasks
            print_info("Adding example tasks for demonstration...")
            self.config["tasks"] = [
                {
                    "description": "Send a welcome message",
                    "priority": "HIGH",
                    "expires_minutes": 60,
                },
                {
                    "description": "Check system status",
                    "priority": "NORMAL",
                    "expires_minutes": 120,
                },
            ]

    def _create_task(self) -> dict[str, Any] | None:
        """Create a single task interactively."""
        print()
        description = ask_question("Task description")
        if not description:
            return None

        priority = ask_choice(
            "Priority",
            ["CRITICAL", "URGENT", "HIGH", "NORMAL", "LOW"],
            default="NORMAL",
        )

        # Expiration
        expires_choice = ask_choice(
            "Task expires in",
            ["1 hour", "24 hours", "7 days", "Never"],
            default="24 hours",
        )

        task: dict[str, Any] = {"description": description, "priority": priority}

        if "1 hour" in expires_choice:
            task["expires_minutes"] = 60
        elif "24 hours" in expires_choice:
            task["expires_minutes"] = 1440
        elif "7 days" in expires_choice:
            task["expires_days"] = 7

        # Context
        if ask_yes_no("Add context data?", default=False):
            print_info("Enter context as key=value pairs (empty line to finish)")
            context = {}
            while True:
                line = input("  ").strip()
                if not line:
                    break
                if "=" in line:
                    key, value = line.split("=", 1)
                    context[key.strip()] = value.strip()
            if context:
                task["context"] = context

        return task

    def _setup_missions(self) -> None:
        """Configure recurring missions."""
        print_header("Step 11: Missions")

        print("\nMissions are recurring scheduled work:")
        print("  • HOURLY - Runs every hour")
        print("  • DAILY - Runs once per day")
        print("  • WEEKLY - Runs once per week")

        self.config["missions"] = []

        if ask_yes_no("\nDo you want to add recurring missions?", default=True):
            while True:
                mission = self._create_mission()
                if mission:
                    self.config["missions"].append(mission)
                    print_success(
                        f"Added mission: {mission['description']} ({mission['interval']})"
                    )

                if not ask_yes_no("\nAdd another mission?", default=False):
                    break

        if not self.config["missions"]:
            # Add example mission
            print_info("Adding example mission for demonstration...")
            self.config["missions"] = [
                {
                    "description": "Check for updates and send status report",
                    "interval": "HOURLY",
                    "can_be_interrupted": True,
                    "interrupt_threshold": "URGENT",
                }
            ]

    def _create_mission(self) -> dict[str, Any] | None:
        """Create a single mission interactively."""
        print()
        description = ask_question("Mission description")
        if not description:
            return None

        interval = ask_choice(
            "How often should this run?",
            ["HOURLY", "DAILY", "WEEKLY"],
            default="HOURLY",
        )

        can_interrupt = ask_yes_no(
            "Can higher-priority tasks interrupt this mission?", default=True
        )

        interrupt_threshold = "URGENT"
        if can_interrupt:
            interrupt_threshold = ask_choice(
                "What priority level can interrupt?",
                ["CRITICAL", "URGENT", "HIGH"],
                default="URGENT",
            )

        return {
            "description": description,
            "interval": interval,
            "can_be_interrupted": can_interrupt,
            "interrupt_threshold": interrupt_threshold,
        }

    def _review_config(self) -> bool:
        """Review configuration and confirm."""
        print_header("Step 12: Review Configuration")

        print("\nYour configuration:")
        print(yaml.dump(self.config, default_flow_style=False, sort_keys=False))

        return ask_yes_no("\nLooks good? Save this configuration?", default=True)

    def _validate_config(self) -> list[str]:
        """Validate configuration before saving.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required fields
        if "execution_pattern" not in self.config:
            errors.append("Missing execution_pattern")
            return errors  # Can't validate further without pattern

        pattern = self.config.get("execution_pattern")

        # Pattern-specific validation
        if pattern in ["daemon", "hybrid"]:
            if "provider" not in self.config:
                errors.append("Daemon pattern requires provider configuration")
            if "agent" not in self.config:
                errors.append("Daemon pattern requires agent configuration")

        if pattern in ["planner_worker", "hybrid"]:
            if "planner_worker" not in self.config:
                errors.append("Planner-Worker pattern requires planner_worker configuration")
            else:
                pw = self.config.get("planner_worker", {})

                if "planner" not in pw or "provider" not in pw.get("planner", {}):
                    errors.append("Planner-Worker requires planner.provider")

                if "worker" not in pw or "provider" not in pw.get("worker", {}):
                    errors.append("Planner-Worker requires worker.provider")

                if "worker" not in pw or "skills" not in pw.get("worker", {}):
                    errors.append("Planner-Worker requires worker.skills")
                elif len(pw.get("worker", {}).get("skills", [])) == 0:
                    errors.append("Worker must have at least one skill")

        return errors

    def _validate_api_key(self, key: str, provider_type: str) -> tuple[bool, str]:
        """Validate API key format.

        Args:
            key: API key to validate
            provider_type: Provider type (anthropic, openai, etc.)

        Returns:
            (is_valid, error_message)
        """
        if not key or key.strip() == "":
            return False, "API key cannot be empty"

        if provider_type == "anthropic":
            if not key.startswith("sk-ant-"):
                return False, "Anthropic API keys should start with 'sk-ant-'"
            if len(key) < 20:
                return False, "Anthropic API key too short (minimum 20 characters)"

        elif provider_type == "openai":
            if not key.startswith("sk-"):
                return False, "OpenAI API keys should start with 'sk-'"
            if len(key) < 20:
                return False, "OpenAI API key too short (minimum 20 characters)"

        return True, ""

    def _validate_skills(self, skills: list[str]) -> tuple[list[str], list[str]]:
        """Validate that requested skills exist.

        Args:
            skills: List of skill names

        Returns:
            (available_skills, missing_skills)
        """
        available = []
        missing = []

        skills_dir = Path("skills")

        for skill in skills:
            skill_path = skills_dir / skill / "SKILL.md"
            if skill_path.exists():
                available.append(skill)
            else:
                missing.append(skill)

        return available, missing

    def _save_config(self) -> None:
        """Save configuration to file."""
        # Validate configuration first
        validation_errors = self._validate_config()

        if validation_errors:
            print()
            print_error("❌ Configuration validation failed:")
            print()
            for error in validation_errors:
                print(f"  • {error}")
            print()
            print("Please fix these issues and try again.")
            sys.exit(1)

        # Determine output path
        default_path = "config.yaml"
        output_path = ask_question("\nWhere should we save the config?", default=default_path)

        # Check if file exists
        if Path(output_path).exists():
            if not ask_yes_no(f"\n{output_path} already exists. Overwrite?", default=False):
                output_path = ask_question("Enter a different path")

        # Save
        try:
            with open(output_path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            print_success(f"Configuration saved to {output_path}")
            self.config["_output_path"] = output_path
        except Exception as e:
            print_error(f"Failed to save configuration: {e}")
            sys.exit(1)

        # Create workspace files
        self._create_workspace_files()

        # Generate runner scripts for planner-worker if applicable
        self._generate_runner_scripts()

        # Generate constitution templates if requested
        self._generate_constitution_templates()

        # Offer to auto-start daemon
        self._offer_auto_start()

    def _create_workspace_files(self) -> None:
        """Create workspace files (PERSONALITY.md, INSTRUCTIONS.md, etc.)."""
        print_header("Creating Workspace Files")

        # Determine workspaces to create
        workspaces = []

        if "agent" in self.config:
            # Single agent
            workspace_dir = Path(
                self.config.get("daemon", {}).get("data_dir", "~/.forge/my-agent")
            ).expanduser()
            agent_config = self.config["agent"]
            workspaces.append((agent_config["agent_id"], workspace_dir, agent_config))
        elif "agents" in self.config:
            # Multi-agent
            for agent_id, agent_config in self.config["agents"].items():
                workspace_dir = Path(
                    agent_config.get("workspace", f"~/.forge/agents/{agent_id}")
                ).expanduser()
                workspaces.append((agent_id, workspace_dir, agent_config))

        # Create files for each workspace with progress tracking
        total_tasks = len(workspaces) * 8  # 8 steps per workspace

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            main_task = progress.add_task("[cyan]Creating workspace files...", total=total_tasks)

            for agent_id, workspace_dir, agent_config in workspaces:
                # Create workspace directory
                progress.update(
                    main_task, description=f"[cyan]Creating directories for '{agent_id}'..."
                )
                workspace_dir.mkdir(parents=True, exist_ok=True)
                memory_dir = workspace_dir / "memory"
                memory_dir.mkdir(exist_ok=True)
                (memory_dir / "daily").mkdir(exist_ok=True)
                (memory_dir / "sessions").mkdir(exist_ok=True)
                progress.advance(main_task)

                # Get template directory
                template_dir = Path(__file__).parent.parent / "templates"

                # Create PERSONALITY.md
                progress.update(
                    main_task, description=f"[cyan]Creating PERSONALITY.md for '{agent_id}'..."
                )
                self._create_personality_file(workspace_dir, agent_config, template_dir)
                progress.advance(main_task)

                # Create INSTRUCTIONS.md
                progress.update(
                    main_task, description=f"[cyan]Creating INSTRUCTIONS.md for '{agent_id}'..."
                )
                self._create_instructions_file(workspace_dir, agent_config, template_dir)
                progress.advance(main_task)

                # Get work types for this agent
                work_types = agent_config.get("work_types", ["Goals"])

                # Create MISSIONS.md (only if Missions selected)
                if "Missions" in work_types:
                    progress.update(
                        main_task, description=f"[cyan]Creating MISSIONS.md for '{agent_id}'..."
                    )
                    self._create_missions_file(workspace_dir, template_dir)
                    progress.advance(main_task)

                # Create USER.md
                progress.update(
                    main_task, description=f"[cyan]Creating USER.md for '{agent_id}'..."
                )
                self._create_user_file(workspace_dir, template_dir)
                progress.advance(main_task)

                # Create SKILLS.md
                progress.update(
                    main_task, description=f"[cyan]Creating SKILLS.md for '{agent_id}'..."
                )
                self._create_skills_file(workspace_dir, template_dir)
                progress.advance(main_task)

                # Create GOALS.md (only if Goals selected)
                if "Goals" in work_types:
                    progress.update(
                        main_task, description=f"[cyan]Creating GOALS.md for '{agent_id}'..."
                    )
                    self._create_goals_file(workspace_dir, template_dir)
                    progress.advance(main_task)

                # Create security.yaml
                progress.update(
                    main_task, description=f"[cyan]Creating security.yaml for '{agent_id}'..."
                )
                self._create_security_file(workspace_dir, agent_id, agent_config)
                progress.advance(main_task)

                # Initialize database files for web dashboard
                progress.update(
                    main_task, description=f"[cyan]Initializing databases for '{agent_id}'..."
                )
                self._create_database_files(workspace_dir)
                progress.advance(main_task)

        print()
        print_success(f"Created workspace files for {len(workspaces)} agent(s)")
        print()
        print_info("Workspace files can be edited anytime to customize your agent's behavior.")
        print_info(
            "The agent will load these files at startup to understand its role and your preferences."
        )

    def _create_personality_file(
        self, workspace_dir: Path, agent_config: dict, template_dir: Path
    ) -> None:
        """Create PERSONALITY.md from template."""
        template_path = template_dir / "PERSONALITY.md"

        if not template_path.exists():
            print_warning("PERSONALITY.md template not found, skipping")
            return

        with open(template_path) as f:
            content = f.read()

        # Replace placeholders
        agent_name = agent_config.get("agent_id", "My Agent").title()
        instructions = agent_config.get("instructions", "You are a helpful AI assistant")

        # Extract role from instructions if possible
        agent_role = "AI Assistant"
        if "assistant" in instructions.lower():
            agent_role = "AI Assistant"
        elif "email" in instructions.lower():
            agent_role = "Email Assistant"
        elif "research" in instructions.lower():
            agent_role = "Research Assistant"
        elif "devops" in instructions.lower():
            agent_role = "DevOps Monitor"

        content = content.replace("{agent_name}", agent_name)
        content = content.replace("{agent_role}", agent_role)
        content = content.replace("{agent_description}", instructions)
        content = content.replace(
            "{communication_tone}", "Professional but warm, like a trusted colleague"
        )

        # Write file
        with open(workspace_dir / "PERSONALITY.md", "w") as f:
            f.write(content)

    def _create_instructions_file(
        self, workspace_dir: Path, agent_config: dict, template_dir: Path
    ) -> None:
        """Create INSTRUCTIONS.md from template."""
        # Check if this is an autonomous development agent
        instructions_str = agent_config.get("instructions", "").lower()
        is_autonomous_dev = any(
            keyword in instructions_str
            for keyword in ["autonomous", "development", "code", "improve"]
        )

        # Use specialized template for autonomous development agents
        if is_autonomous_dev and (template_dir / "INSTRUCTIONS_AUTONOMOUS.md").exists():
            template_path = template_dir / "INSTRUCTIONS_AUTONOMOUS.md"
        else:
            template_path = template_dir / "INSTRUCTIONS.md"

        if not template_path.exists():
            print_warning(f"{template_path.name} template not found, skipping")
            return

        with open(template_path) as f:
            content = f.read()

        # Get workspace path
        workspace_path = self.config.get("workspace", {}).get("path", "")
        if not workspace_path:
            workspace_path = str(Path.home() / "workspace")

        # Replace placeholders
        rate_limits = self.config.get("rate_limits", {})
        max_requests = rate_limits.get("max_requests_per_minute", 10)
        max_cost = rate_limits.get("max_cost_per_minute", 0.50)

        content = content.replace("{workspace_path}", workspace_path)
        content = content.replace("{max_requests_per_minute}", str(max_requests))
        content = content.replace("{max_cost_per_minute}", str(max_cost))

        # For generic template, add core responsibilities
        if "INSTRUCTIONS_AUTONOMOUS" not in template_path.name:
            instructions = agent_config.get("instructions", "You are a helpful AI assistant")
            core_responsibilities = f"- {instructions}\n- Execute tasks and missions autonomously\n- Learn and adapt to user preferences"
            content = content.replace("{core_responsibilities}", core_responsibilities)

        # Write file
        with open(workspace_dir / "INSTRUCTIONS.md", "w") as f:
            f.write(content)

    def _create_missions_file(self, workspace_dir: Path, template_dir: Path) -> None:
        """Create MISSIONS.md from template."""
        template_path = template_dir / "MISSIONS.md"

        if not template_path.exists():
            print_warning("MISSIONS.md template not found, skipping")
            return

        # Copy template as-is (contains examples and documentation)
        with open(template_path) as f:
            content = f.read()

        with open(workspace_dir / "MISSIONS.md", "w") as f:
            f.write(content)

    def _create_user_file(self, workspace_dir: Path, template_dir: Path) -> None:
        """Create USER.md from template."""
        template_path = template_dir / "USER.md"

        if not template_path.exists():
            print_warning("USER.md template not found, skipping")
            return

        with open(template_path) as f:
            content = f.read()

        # Replace with placeholder values - user will fill in
        replacements = {
            "{user_name}": "[Your Name]",
            "{user_role}": "[Your Role]",
            "{user_location}": "[Your Location]",
            "{user_timezone}": "[Your Timezone]",
            "{working_hours}": "9:00 AM - 6:00 PM weekdays",
            "{notification_times}": "9-11 AM, 2-4 PM",
            "{notification_threshold}": "URGENT and above",
            "{preferred_format}": "Bullet points and summaries",
            "{expected_response_time}": "Within 1-2 hours during work hours",
            "{communication_style}": "Professional and concise",
            "{focus_time}": "9-11 AM (avoid interruptions)",
            "{meeting_days}": "Tuesday, Thursday",
            "{deep_work_days}": "Monday, Wednesday, Friday mornings",
            "{review_time}": "Friday 4-5 PM",
            "{break_schedule}": "Coffee at 9 AM and 2 PM",
            "{project_name}": "[Project Name]",
            "{project_priority}": "HIGH",
            "{project_description}": "[Brief description]",
            "{project_focus}": "[Key focus areas]",
            "{project_deadline}": "[Deadline]",
            "{news_sources}": "HackerNews, ArXiv, etc.",
            "{topics_of_interest}": "[Your topics]",
            "{email_style}": "Professional but friendly",
            "{meeting_policy}": "No meetings before 10 AM or after 4 PM",
            "{tools_list}": "Email, Slack, GitHub, etc.",
            "{weekly_goal_1}": "[Goal 1]",
            "{weekly_goal_2}": "[Goal 2]",
            "{weekly_goal_3}": "[Goal 3]",
            "{monthly_goal_1}": "[Goal 1]",
            "{monthly_goal_2}": "[Goal 2]",
            "{monthly_goal_3}": "[Goal 3]",
            "{quarterly_goal_1}": "[Goal 1]",
            "{quarterly_goal_2}": "[Goal 2]",
            "{quarterly_goal_3}": "[Goal 3]",
            "{vip_person_1}": "[Name]",
            "{relationship}": "[Relationship]",
            "{vip_person_2}": "[Name]",
            "{important_date_1}": "[Date]",
            "{event}": "[Event]",
            "{important_date_2}": "[Date]",
            "{priority_1}": "[Priority 1]",
            "{priority_2}": "[Priority 2]",
            "{priority_3}": "[Priority 3]",
            "{appreciation_1}": "Clear, actionable communication",
            "{appreciation_2}": "Proactive problem-solving",
            "{avoid_1}": "Vague or ambiguous messages",
            "{avoid_2}": "Unnecessary interruptions",
            "{learning_preference}": "Hands-on with clear examples",
        }

        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        with open(workspace_dir / "USER.md", "w") as f:
            f.write(content)

    def _create_skills_file(self, workspace_dir: Path, template_dir: Path) -> None:
        """Create SKILLS.md from template."""
        template_path = template_dir / "SKILLS.md"

        if not template_path.exists():
            print_warning("SKILLS.md template not found, skipping")
            return

        # Copy template as-is (contains documentation)
        with open(template_path) as f:
            content = f.read()

        with open(workspace_dir / "SKILLS.md", "w") as f:
            f.write(content)

    def _create_goals_file(self, workspace_dir: Path, template_dir: Path) -> None:
        """Create GOALS.md from template with workspace context."""
        template_path = template_dir / "GOALS.md"

        if not template_path.exists():
            print_warning("GOALS.md template not found, skipping")
            return

        with open(template_path) as f:
            content = f.read()

        # Get workspace path from config
        workspace_path = self.config.get("workspace", {}).get("path", "")
        if not workspace_path:
            workspace_path = str(Path.home() / "workspace")

        # Get default goals - can be customized per agent type
        default_goals = """- Continuously improve code quality
- Add type hints to functions missing them
- Fix failing tests
- Add docstrings to public methods
- Improve test coverage"""

        # Replace placeholders
        content = content.replace("{workspace_path}", workspace_path)
        content = content.replace("{goals}", default_goals)

        with open(workspace_dir / "GOALS.md", "w") as f:
            f.write(content)

    def _create_security_file(self, workspace_dir: Path, agent_id: str, agent_config: dict) -> None:
        """Create security.yaml from configured preset."""
        # Get security config from wizard
        security_config = self.config.get("security", {})
        preset = security_config.get("preset", "moderate")
        log_level = security_config.get("log_level", "standard")
        compliance = security_config.get("compliance", {})

        # Auto-detect if autonomous-dev preset should be used
        # Check if this agent has Goals work type (indicator of autonomous operation)
        work_types = agent_config.get("work_types", [])
        if "Goals" in work_types and preset == "moderate":
            # Use autonomous-dev for better autonomous operation
            preset = "autonomous-dev"
            print_info("Auto-selected 'autonomous-dev' security preset for Goals-based agent")

        # Create policy from preset
        policy = SecurityPolicy.create_default(agent_id, preset)

        # Override log level if specified
        from teotl.core.security.audit import LogLevel

        policy.log_level = LogLevel(log_level)

        # Apply compliance settings
        if compliance:
            policy.compliance.gdpr_enabled = compliance.get("gdpr_enabled", False)
            policy.compliance.soc2_enabled = compliance.get("soc2_enabled", False)
            policy.compliance.hipaa_enabled = compliance.get("hipaa_enabled", False)

        # Save to workspace
        security_path = workspace_dir / "security.yaml"
        policy.to_yaml(security_path)

    def _create_database_files(self, workspace_dir: Path) -> None:
        """Initialize task and mission database files.

        These are required for the web dashboard to discover agents.
        """
        from teotl.primitives.missions import MissionStore
        from teotl.primitives.tasks import TaskStore

        # Create tasks.db
        task_store = TaskStore(workspace_dir / "tasks.db")
        task_store.close()

        # Create missions.db
        mission_store = MissionStore(workspace_dir / "missions.db")
        mission_store.close()

    def _generate_runner_scripts(self) -> None:
        """Generate runner scripts for planner-worker pattern."""
        pattern = self.config.get("execution_pattern")

        if pattern not in ["planner_worker", "hybrid"]:
            return  # Only generate for planner-worker patterns

        print_header("Generating Runner Scripts")

        config_path = self.config.get("_output_path", "config.yaml")
        config_dir = Path(config_path).parent

        # Generate run_planner_worker.py
        runner_script = config_dir / "run_planner_worker.py"

        # Get configuration
        planner_config = self.config.get("planner_worker", {})
        planner_provider_name = planner_config.get("planner", {}).get("provider", "claude-sonnet-4")
        worker_provider_name = planner_config.get("worker", {}).get("provider", "claude-haiku-4")
        worker_skills = planner_config.get("worker", {}).get("skills", ["filesystem", "git"])
        worker_policy = planner_config.get("worker", {}).get("policy", "autonomous-dev")
        planner_instructions = planner_config.get("planner", {}).get(
            "instructions", "Create detailed, atomic execution plans with verification"
        )
        use_spec_kit = planner_config.get("planner", {}).get("use_spec_kit", False)

        # Add spec_kit to worker skills if planner uses it
        if use_spec_kit and "spec_kit" not in worker_skills:
            worker_skills = list(worker_skills) + ["spec_kit"]

        # Determine workspace
        if "agent" in self.config:
            workspace_dir = self.config.get("daemon", {}).get("data_dir", "~/.forge/my-agent")
            agent_id = self.config["agent"]["agent_id"]
        else:
            workspace_dir = "~/workspace"
            agent_id = "planner-worker-agent"

        spec_kit_note = ""
        if use_spec_kit:
            spec_kit_note = """
spec-kit Integration:
- Planner uses spec-kit for formal specifications
- Constitution files: CONSTITUTION.md, ARCHITECTURE.md, STANDARDS.md
- Structured tasks with acceptance criteria
- Verification against requirements
"""

        script_content = f'''"""
Planner-Worker runner script generated by Forge wizard.

This script runs the Planner-Worker pattern for complex tasks:
1. Planner creates detailed execution plan
2. Worker executes steps systematically
3. 90% cost savings with smart planning
{spec_kit_note}
Usage:
    python3 run_planner_worker.py
"""
import asyncio
import os
import sys
import shutil
from pathlib import Path

from teotl.primitives.harness import PlannerWorkerHarness
from teotl.core.provider import AnthropicProvider, OpenAIProvider


def check_api_keys() -> dict[str, str]:
    """Validate API keys from environment.

    Returns:
        Dict mapping component to error message (empty string if valid)
    """
    errors = {{}}

    # Check planner API key
    planner_key = os.getenv("ANTHROPIC_API_KEY")
    if not planner_key:
        errors["planner"] = "Missing environment variable: ANTHROPIC_API_KEY"
    elif len(planner_key) < 20:
        errors["planner"] = "Invalid ANTHROPIC_API_KEY: too short"

    # Check worker API key (may be same as planner)
    worker_key = os.getenv("ANTHROPIC_API_KEY")
    if not worker_key:
        errors["worker"] = "Missing environment variable: ANTHROPIC_API_KEY"
    elif len(worker_key) < 20:
        errors["worker"] = "Invalid ANTHROPIC_API_KEY: too short"

    return errors


def check_cli_tools(worker_skills: list[str], use_spec_kit: bool) -> dict[str, bool]:
    """Check if required CLI tools are installed.

    Args:
        worker_skills: List of worker skills
        use_spec_kit: Whether spec-kit is enabled

    Returns:
        Dict mapping tool name to availability
    """
    tools = {{}}

    # Check claude-code if skill is enabled
    if "claude_code" in worker_skills:
        tools["claude-code"] = shutil.which("claude-code") is not None

    # Check spec-kit if enabled
    if use_spec_kit:
        tools["spec-kit"] = shutil.which("spec-kit") is not None

    return tools


def check_constitution_files(workspace_dir: Path, use_spec_kit: bool) -> tuple[list[str], list[str]]:
    """Check if constitution files exist (when spec-kit enabled).

    Args:
        workspace_dir: Workspace directory path
        use_spec_kit: Whether spec-kit is enabled

    Returns:
        (existing_files, missing_files)
    """
    if not use_spec_kit:
        return [], []

    required_files = [
        "CONSTITUTION.md",
        "ARCHITECTURE.md",
        "STANDARDS.md",
        "SECURITY.md",
    ]

    existing = []
    missing = []

    for filename in required_files:
        file_path = workspace_dir / filename
        if file_path.exists():
            existing.append(filename)
        else:
            missing.append(filename)

    return existing, missing


def print_startup_checks(
    api_errors: dict[str, str],
    cli_tools: dict[str, bool],
    missing_constitution: list[str]
):
    """Print startup validation results and exit if critical errors.

    Args:
        api_errors: Dict from check_api_keys()
        cli_tools: Dict from check_cli_tools()
        missing_constitution: Missing constitution files
    """
    has_errors = False

    # API key errors (CRITICAL - must exit)
    if api_errors:
        print("❌ API Key Validation Failed:")
        print()
        for component, error in api_errors.items():
            print(f"  • {{component}}: {{error}}")
        print()
        print("Set your API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print()
        has_errors = True

    # CLI tool warnings (WARNING - can continue)
    missing_tools = [name for name, available in cli_tools.items() if not available]
    if missing_tools:
        print("⚠️  WARNING: Missing CLI tools:")
        print()
        for tool in missing_tools:
            if tool == "claude-code":
                print(f"  • {{tool}} - Required for claude_code skill")
                print(f"    Install: https://github.com/anthropics/claude-code")
            elif tool == "spec-kit":
                print(f"  • {{tool}} - Required for spec-kit planning")
                print(f"    Install: npm install -g spec-kit")
        print()
        print("Agent will continue but these skills will not function.")
        print()

    # Constitution file warnings (WARNING - can continue)
    if missing_constitution:
        print("⚠️  WARNING: Missing constitution files:")
        print()
        for filename in missing_constitution:
            print(f"  • {{filename}}")
        print()
        print("Planner will continue but constitution-driven planning may be limited.")
        print("Create these files or re-run wizard to generate templates.")
        print()

    # Exit if critical errors
    if has_errors:
        sys.exit(1)


async def main():
    """Run planner-worker harness."""

    # Configuration from wizard
    workspace_dir = Path("{workspace_dir}").expanduser()
    agent_id = "{agent_id}"
    worker_skills = {worker_skills}
    use_spec_kit = {str(use_spec_kit)}

    # Perform startup validation checks
    print("🔍 Validating environment...")
    print()

    api_errors = check_api_keys()
    cli_tools = check_cli_tools(worker_skills, use_spec_kit)
    existing_constitution, missing_constitution = check_constitution_files(workspace_dir, use_spec_kit)

    print_startup_checks(api_errors, cli_tools, missing_constitution)

    if not api_errors:
        print("✅ All validation checks passed")
        print()

    # Provider configuration
    planner_model = "{planner_provider_name}"
    worker_model = "{worker_provider_name}"

    # Determine provider classes
    if "claude" in planner_model:
        planner_provider = AnthropicProvider(model=planner_model)
    elif "gpt" in planner_model:
        planner_provider = OpenAIProvider(model=planner_model)
    else:
        planner_provider = AnthropicProvider(model=planner_model)

    if "claude" in worker_model:
        worker_provider = AnthropicProvider(model=worker_model)
    elif "gpt" in worker_model:
        worker_provider = OpenAIProvider(model=worker_model)
    else:
        worker_provider = AnthropicProvider(model=worker_model)

    # Create harness
    print(f"🚀 Starting Planner-Worker harness...")
    print(f"   Agent ID: {{agent_id}}")
    print(f"   Workspace: {{workspace_dir}}")
    print(f"   Planner: {{planner_model}}")
    print(f"   Worker: {{worker_model}}")
    print()

    harness = PlannerWorkerHarness(
        agent_id=agent_id,
        planner_provider=planner_provider,
        worker_provider=worker_provider,
        workspace_dir=workspace_dir,
        worker_skills={worker_skills},
        worker_policy="{worker_policy}",
        planner_instructions="""{planner_instructions}""",
        enable_janitor=True,
        enable_heartbeat=True,
        enable_cost_tracking=True,
        enable_state=True,
    )

    # Load goals
    goals_file = Path("GOALS.md")
    if goals_file.exists():
        goals = goals_file.read_text()
        print(f"📋 Loaded goals from GOALS.md")
    else:
        goals = input("Enter your goal or task:\\n> ")

    print()

    # Phase 1: Create plan
    print("=" * 70)
    print("PHASE 1: PLANNING")
    print("=" * 70)
    print()
    print("Creating execution plan...")

    plan = await harness.plan(goals=goals)

    print()
    print(f"✅ Plan created with {{len(plan.steps)}} steps")
    print(f"📄 Review plan in: {{workspace_dir}}/PLAN.md")
    print()

    # Show plan summary
    print("Plan steps:")
    for i, step in enumerate(plan.steps[:5], 1):
        print(f"  {{i}}. {{step.description[:60]}}...")
    if len(plan.steps) > 5:
        print(f"  ... and {{len(plan.steps) - 5}} more steps")
    print()

    # Ask for approval
    response = input("Proceed with execution? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Execution cancelled. Plan saved to PLAN.md")
        return

    # Phase 2: Execute plan
    print()
    print("=" * 70)
    print("PHASE 2: EXECUTION")
    print("=" * 70)
    print()

    completed = 0
    failed = 0

    while not harness.is_complete():
        result = await harness.execute_next_step()

        if result.success:
            status = "✅"
            completed += 1
        else:
            status = "❌"
            failed += 1

        print(f"{{status}} Step {{result.step.number}}/{{len(plan.steps)}}: {{result.step.description[:50]}}...")

        if not result.success:
            print(f"   Error: {{result.error}}")
            if not input("   Continue anyway? (yes/no): ").lower().startswith("y"):
                break

    # Summary
    print()
    print("=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)
    print()
    print(f"✅ Completed: {{completed}} steps")
    if failed > 0:
        print(f"❌ Failed: {{failed}} steps")
    print()
    print(f"📊 Progress: {{workspace_dir}}/PROGRESS.md")
    print(f"📄 Plan: {{workspace_dir}}/PLAN.md")
    print()

    if harness.cost_tracker:
        total_cost = harness.cost_tracker.get_total_cost()
        print(f"💰 Total cost: ${{total_cost:.2f}}")
        print()

    print("🎉 All done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\\n\\n❌ Error: {{e}}")
        import traceback
        traceback.print_exc()
'''

        # Write script
        try:
            with open(runner_script, "w") as f:
                f.write(script_content)

            # Make executable
            import stat

            runner_script.chmod(
                runner_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

            print_success(f"✅ Generated: {runner_script}")
            print_info("   Run with: python3 run_planner_worker.py")
            print()
        except Exception as e:
            print_warning(f"⚠️  Failed to generate runner script: {e}")

    def _generate_constitution_templates(self) -> None:
        """Generate constitution template files if requested."""
        pattern = self.config.get("execution_pattern")

        # Only for planner-worker patterns
        if pattern not in ["planner_worker", "hybrid"]:
            return

        planner_config = self.config.get("planner_worker", {}).get("planner", {})
        create_templates = planner_config.get("create_constitution_templates", False)

        if not create_templates:
            return

        print_header("Generating Constitution Templates")

        # Determine workspace directory
        if "agent" in self.config:
            workspace_dir = Path(
                self.config.get("daemon", {}).get("data_dir", "~/.forge/my-agent")
            ).expanduser()
        else:
            workspace_dir = Path("~/workspace").expanduser()

        workspace_dir.mkdir(parents=True, exist_ok=True)

        # CONSTITUTION.md
        constitution_content = """# Project Constitution

This document defines the core values, principles, and guidelines for this project.
All features, code changes, and decisions should align with these principles.

## Core Values

### 1. Quality First
- **Code Quality**: All code must be clean, maintainable, and well-tested
- **User Experience**: Features must provide clear value to users
- **Security**: Security is never compromised for convenience

### 2. Transparency
- **Clear Documentation**: All features must be documented
- **Explicit Behavior**: No hidden side effects or magic
- **Open Communication**: Decisions are communicated clearly

### 3. Sustainability
- **Performance**: Code should be efficient and scalable
- **Maintainability**: Future developers should understand the code
- **Technical Debt**: Address technical debt proactively

## Development Principles

### Testing
- All features require unit tests
- Critical paths require integration tests
- Test coverage minimum: 80%

### Code Review
- All changes require review before merging
- Security-sensitive changes require two reviews
- Breaking changes require team discussion

### Documentation
- All public APIs must be documented
- Complex algorithms require explanation
- Breaking changes must update migration guides

## Security Policies

### Authentication & Authorization
- All endpoints require authentication by default
- Use principle of least privilege
- Regular security audits required

### Data Protection
- Encrypt sensitive data at rest and in transit
- Never log sensitive information
- Comply with GDPR/privacy regulations

### Dependencies
- Keep dependencies up to date
- Security patches applied within 48 hours
- Review third-party code before integration

## Architecture Guidelines

See ARCHITECTURE.md for detailed architectural patterns and decisions.

## Coding Standards

See STANDARDS.md for language-specific coding conventions.

## Security Requirements

See SECURITY.md for detailed security policies and practices.
"""

        # ARCHITECTURE.md
        architecture_content = """# Architecture

This document describes the architectural patterns, design decisions, and structure of this project.

## System Architecture

### High-Level Design
```
┌─────────────────┐
│   Presentation  │  (UI Layer)
├─────────────────┤
│   Application   │  (Business Logic)
├─────────────────┤
│   Domain        │  (Core Models)
├─────────────────┤
│   Infrastructure│  (External Services)
└─────────────────┘
```

## Design Patterns

### Recommended Patterns
- **Repository Pattern**: For data access abstraction
- **Service Layer**: For business logic encapsulation
- **Dependency Injection**: For loose coupling
- **Factory Pattern**: For object creation
- **Observer Pattern**: For event handling

### Anti-Patterns to Avoid
- God Objects (classes that do too much)
- Tight Coupling (direct dependencies between layers)
- Premature Optimization
- Magic Numbers/Strings

## Module Structure

### Directory Organization
```
src/
  ├── core/         # Core domain models
  ├── services/     # Business logic services
  ├── api/          # API endpoints
  ├── db/           # Database access
  └── utils/        # Utility functions

tests/
  ├── unit/         # Unit tests
  ├── integration/  # Integration tests
  └── e2e/          # End-to-end tests
```

## Data Flow

### Request-Response Flow
1. Client sends request to API
2. API validates request
3. Service layer processes business logic
4. Repository layer accesses data
5. Response flows back through layers

### Event-Driven Flow
1. Event emitted by service
2. Event bus routes to handlers
3. Handlers process event asynchronously
4. State updated accordingly

## Database Design

### Schema Principles
- Use UUIDs for primary keys
- Index foreign keys and frequently queried fields
- Use soft deletes (deleted_at) instead of hard deletes
- Include created_at and updated_at timestamps

### Migrations
- Never modify existing migrations
- Test migrations in both directions (up and down)
- Include seed data for development

## API Design

### RESTful Conventions
- Use standard HTTP methods (GET, POST, PUT, DELETE)
- Use plural nouns for resource names
- Version APIs (/api/v1/...)
- Use proper status codes

### Error Handling
- Return consistent error format
- Include error codes for client handling
- Log errors with context

## Scalability Considerations

### Horizontal Scaling
- Stateless services (no session state in memory)
- Use external cache (Redis)
- Database read replicas

### Performance
- Cache frequently accessed data
- Use pagination for large datasets
- Optimize database queries

## Security Architecture

See SECURITY.md for detailed security architecture.
"""

        # STANDARDS.md
        standards_content = """# Coding Standards

This document defines the coding conventions and best practices for this project.

## General Principles

### Code Style
- **Consistency**: Follow project conventions consistently
- **Readability**: Code should be self-documenting
- **Simplicity**: Prefer simple solutions over clever ones

### Naming Conventions
- **Variables**: Use descriptive names (e.g., `user_count` not `uc`)
- **Functions**: Use verbs (e.g., `get_user()`, `create_order()`)
- **Classes**: Use nouns (e.g., `UserService`, `OrderRepository`)
- **Constants**: Use SCREAMING_SNAKE_CASE

## Python Standards

### Code Style
- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Use f-strings for string formatting

### Example
```python
def calculate_total_price(
    items: list[dict],
    discount_percentage: float = 0.0
) -> float:
    '''Calculate total price with optional discount.

    Args:
        items: List of items with 'price' keys
        discount_percentage: Discount as percentage (0-100)

    Returns:
        Total price after discount
    '''
    subtotal = sum(item["price"] for item in items)
    discount = subtotal * (discount_percentage / 100)
    return subtotal - discount
```

### Testing Standards
- One test file per module
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies

## JavaScript/TypeScript Standards

### Code Style
- Use TypeScript for type safety
- Follow ESLint configuration
- Use async/await instead of promises
- Prefer const over let, never use var

### Example
```typescript
interface User {
  id: string;
  name: string;
  email: string;
}

async function fetchUser(userId: string): Promise<User> {
  const response = await fetch(`/api/users/${userId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch user: ${response.status}`);
  }

  return await response.json();
}
```

## Git Conventions

### Commit Messages
Format: `<type>(<scope>): <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/config changes

Example:
```
feat(auth): add JWT token refresh mechanism

- Implement token refresh endpoint
- Add refresh token to user session
- Update client to handle token expiration
```

### Branch Naming
- `feature/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation

## Documentation Standards

### Code Comments
- Explain WHY, not WHAT
- Document complex algorithms
- Keep comments up to date
- Remove commented-out code

### API Documentation
- Document all public endpoints
- Include request/response examples
- Document error responses
- Keep OpenAPI/Swagger spec updated

### README Requirements
- Project description
- Setup instructions
- Usage examples
- Contribution guidelines

## Error Handling

### Principles
- Fail fast and loudly
- Provide helpful error messages
- Log errors with context
- Never swallow exceptions silently

### Example
```python
try:
    user = get_user(user_id)
except UserNotFoundError:
    logger.error(f"User not found: {user_id}")
    raise HTTPException(
        status_code=404,
        detail=f"User {user_id} not found"
    )
except Exception as e:
    logger.exception(f"Unexpected error fetching user {user_id}")
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

## Performance Guidelines

### General
- Profile before optimizing
- Optimize for readability first
- Use appropriate data structures
- Cache expensive computations

### Database
- Use indexes for foreign keys
- Avoid N+1 queries
- Use pagination for large datasets
- Use database connection pooling

## Code Review Checklist

Before submitting for review:
- [ ] Tests pass
- [ ] Code follows style guide
- [ ] No console.log/print statements
- [ ] Error handling implemented
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance considered
"""

        # SECURITY.md
        security_content = """# Security Standards

This document defines security policies, practices, and requirements for this project.

## Security Principles

### Defense in Depth
- Multiple layers of security controls
- No single point of failure
- Assume all input is malicious

### Least Privilege
- Grant minimum necessary permissions
- Regularly review and revoke unused access
- Time-limited elevated privileges

### Secure by Default
- Secure defaults in all configurations
- Opt-in for permissive behaviors
- Fail securely on errors

## Authentication & Authorization

### Password Requirements
- Minimum 12 characters
- Must include uppercase, lowercase, numbers, symbols
- Use bcrypt/argon2 for hashing
- Never store passwords in plain text

### JWT Tokens
- Use RS256 (not HS256) for signing
- Short expiration (15 minutes for access tokens)
- Rotate refresh tokens
- Revoke tokens on logout

### API Keys
- Generate cryptographically secure keys
- Store hashed in database
- Rate limit per key
- Allow key rotation

### Multi-Factor Authentication
- Required for administrative accounts
- Support TOTP (not SMS)
- Backup codes for recovery

## Data Protection

### Encryption
- TLS 1.3 for data in transit
- AES-256 for data at rest
- Use established crypto libraries
- Never implement custom crypto

### Sensitive Data
- Encrypt PII (Personally Identifiable Information)
- Never log sensitive data
- Mask sensitive fields in logs
- Comply with GDPR/privacy laws

### Data Retention
- Define retention policies
- Automated data deletion
- Secure data disposal
- Audit trail for deletions

## Input Validation

### All Input is Untrusted
- Validate on server (never trust client)
- Whitelist valid inputs
- Reject unexpected formats
- Sanitize before use

### SQL Injection Prevention
- Use parameterized queries
- Use ORM query builders
- Never concatenate SQL strings
- Validate input types

### XSS Prevention
- Escape HTML output
- Use Content Security Policy
- Sanitize user-generated content
- Use framework protections

### CSRF Prevention
- Use CSRF tokens
- SameSite cookie attribute
- Verify origin headers

## Dependency Management

### Third-Party Dependencies
- Regular security audits
- Automated vulnerability scanning
- Update dependencies monthly
- Review before adding new dependencies

### Security Patches
- Apply critical patches within 24 hours
- Apply high-severity patches within 1 week
- Test patches in staging first

### License Compliance
- Only use approved licenses
- Track all dependencies
- Regular license audits

## Logging & Monitoring

### Security Logging
- Log authentication attempts
- Log authorization failures
- Log sensitive operations
- Include user context

### Never Log
- Passwords or tokens
- Credit card numbers
- Social security numbers
- Other PII

### Monitoring
- Alert on suspicious patterns
- Monitor failed login attempts
- Track API rate limits
- Detect anomalies

## Incident Response

### Preparation
- Documented incident response plan
- Designated security team
- Regular security drills
- Contact information updated

### Detection
- Automated monitoring alerts
- Security audit logs
- User reports
- Penetration testing

### Response
1. Contain the incident
2. Assess the damage
3. Notify affected parties
4. Document the incident
5. Review and improve

## Code Security

### Secure Coding Practices
- Input validation
- Output encoding
- Parameterized queries
- Proper error handling

### Code Review
- Security-focused code reviews
- Automated static analysis
- Regular penetration testing
- Bug bounty program

### Secrets Management
- Never commit secrets to git
- Use environment variables
- Use secrets management service
- Rotate secrets regularly

## Deployment Security

### Infrastructure
- Firewall configured
- Unnecessary ports closed
- Regular security patches
- Isolated environments

### Access Control
- SSH key authentication only
- Disable root login
- Use bastion hosts
- VPN for internal access

### Backup & Recovery
- Encrypted backups
- Offsite backup storage
- Regular restore testing
- Disaster recovery plan

## Compliance

### Regulations
- GDPR (EU data protection)
- CCPA (California privacy)
- HIPAA (healthcare data)
- PCI DSS (payment data)

### Auditing
- Regular compliance audits
- Document security controls
- Maintain audit trails
- Annual security review

## Security Training

### Required Training
- Security awareness for all staff
- Secure coding for developers
- Incident response for security team
- Annual refresher training

## Reporting Security Issues

If you discover a security vulnerability:
1. **DO NOT** open a public issue
2. Email security@example.com
3. Include detailed description
4. Allow 90 days for fix before disclosure
"""

        templates = [
            ("CONSTITUTION.md", constitution_content),
            ("ARCHITECTURE.md", architecture_content),
            ("STANDARDS.md", standards_content),
            ("SECURITY.md", security_content),
        ]

        created_files = []

        for filename, content in templates:
            file_path = workspace_dir / filename

            try:
                # Don't overwrite existing files
                if file_path.exists():
                    print_info(f"⏭️  {filename} already exists, skipping")
                    continue

                with open(file_path, "w") as f:
                    f.write(content)

                created_files.append(filename)
                print_success(f"✅ Generated: {file_path}")

            except Exception as e:
                print_warning(f"⚠️  Failed to generate {filename}: {e}")

        if created_files:
            print()
            print_success(f"Created {len(created_files)} constitution template(s)")
            print_info("📝 Customize these files to match your project values")
            print()

    def _offer_auto_start(self) -> None:
        """Offer to start the agent daemon immediately with proper daemonization."""
        print()

        if not ask_yes_no("Start your agent now?", default=True):
            return

        print_info("Starting agent daemon...")

        # Determine which agent to start and how
        output_path = self.config.get("_output_path", "config.yaml")
        output_path = Path(output_path).resolve()
        workspace_dir = output_path.parent

        # Create logs directory
        logs_dir = workspace_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Single agent case
        if "agent" in self.config:
            agent_id = self.config["agent"]["agent_id"]
            self._start_single_agent(agent_id, output_path, logs_dir, workspace_dir)

        # Multi-agent case
        elif "agents" in self.config:
            agent_ids = list(self.config["agents"].keys())

            if len(agent_ids) == 1:
                # Only one agent - start it directly
                agent_id = agent_ids[0]
                cmd = [
                    sys.executable,
                    "-m",
                    "teotl.daemon.run",
                    "--config",
                    str(output_path),
                    "--agent-id",
                    agent_id,
                ]
                self._start_daemon_process(
                    agent_id, cmd, logs_dir / f"{agent_id}.log", workspace_dir
                )
            else:
                # Multiple agents - offer to start all or choose one
                print()
                choice = ask_choice(
                    "What would you like to start?",
                    ["All agents", "Choose one agent"],
                    default="All agents",
                )

                if choice == "All agents":
                    # Start all agents
                    print_info(f"Starting {len(agent_ids)} agents...")
                    print()

                    for agent_id in agent_ids:
                        cmd = [
                            sys.executable,
                            "-m",
                            "teotl.daemon.run",
                            "--config",
                            str(output_path),
                            "--agent-id",
                            agent_id,
                        ]
                        self._start_daemon_process(
                            agent_id, cmd, logs_dir / f"{agent_id}.log", workspace_dir
                        )
                        time.sleep(0.5)  # Brief delay between starts

                    print()
                    print_success("✨ All agents started!")
                else:
                    # Choose specific agent
                    agent_id = ask_choice("Which agent to start?", agent_ids, default=agent_ids[0])
                    cmd = [
                        sys.executable,
                        "-m",
                        "teotl.daemon.run",
                        "--config",
                        str(output_path),
                        "--agent-id",
                        agent_id,
                    ]
                    self._start_daemon_process(
                        agent_id, cmd, logs_dir / f"{agent_id}.log", workspace_dir
                    )
        else:
            print_error("No agent configuration found")
            return

    def _start_single_agent(
        self, agent_id: str, config_path: Path, logs_dir: Path, workspace_dir: Path
    ) -> None:
        """Start a single agent daemon."""
        log_file = logs_dir / "daemon.log"

        cmd = [
            sys.executable,
            "-m",
            "teotl.daemon.run",
            "--config",
            str(config_path),
        ]

        self._start_daemon_process(agent_id, cmd, log_file, workspace_dir)

    def _start_daemon_process(
        self, agent_id: str, cmd: list[str], log_file: Path, workspace_dir: Path
    ) -> None:
        """Start daemon process with proper daemonization and logging.

        Args:
            agent_id: Agent identifier
            cmd: Command to execute
            log_file: Path to log file
            workspace_dir: Workspace directory (for PID file)
        """
        try:
            # Use nohup to detach from terminal (if available on the system)
            # For cross-platform compatibility, we'll check if nohup exists
            import shutil

            has_nohup = shutil.which("nohup") is not None

            if has_nohup:
                # Unix-like systems - use nohup for proper daemonization
                full_cmd = ["nohup"] + cmd
            else:
                # Windows or systems without nohup - use direct subprocess
                full_cmd = cmd

            # Open log file for writing
            with open(log_file, "a") as log:
                # Show spinner while starting
                with console.status(f"[bold cyan]Starting agent '{agent_id}'...", spinner="dots"):
                    # Start process detached from terminal
                    subprocess.Popen(
                        full_cmd,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,  # Detach from process group
                        cwd=workspace_dir,
                    )

                    # Wait for initialization
                    time.sleep(3)

            # Check PID file (daemon writes this on successful start)
            pid_file = workspace_dir / "daemon.pid"

            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())

                    # Verify process is actually running
                    if self._is_process_running(pid):
                        print_success(f"✅ Agent '{agent_id}' started successfully (PID: {pid})")
                        print()
                        print_info("Monitor your agent:")
                        print(f"  📋 Logs:  tail -f {log_file}")
                        print(f"  🛑 Stop:  kill {pid}")
                        print()
                        return
                except (ValueError, FileNotFoundError):
                    pass

            # Startup failed - show error from logs
            print_error(f"❌ Agent '{agent_id}' failed to start")
            print_info(f"Check logs: {log_file}")
            print()

            # Show last few lines of log for debugging
            if log_file.exists():
                with open(log_file) as f:
                    lines = f.readlines()
                    if lines:
                        print("Last 10 log lines:")
                        print("-" * 60)
                        for line in lines[-10:]:
                            print(f"  {line.rstrip()}")
                        print("-" * 60)
                        print()

            print_info("Try starting manually:")
            print(f"  python -m teotl.daemon.run --config {workspace_dir / 'config.yaml'}")
            print()

        except Exception as e:
            print_error(f"Failed to start daemon: {e}")
            print_info("You can start it manually with:")
            print(f"  python -m teotl.daemon.run --config {workspace_dir / 'config.yaml'}")
            print()

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running.

        Args:
            pid: Process ID to check

        Returns:
            True if process exists and is running
        """
        try:
            # Try psutil first (more reliable)
            import psutil

            return psutil.pid_exists(pid)
        except ImportError:
            # Fallback to os.kill with signal 0 (doesn't actually kill)
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

    def _print_next_steps(self) -> None:
        """Print next steps for user."""
        print_header("🎉 Setup Complete!")

        output_path = self.config.get("_output_path", "config.yaml")
        is_multi_agent = "agents" in self.config

        if is_multi_agent:
            print(
                f"\n{Color.GREEN}Your {len(self.config['agents'])} agents are ready to start!{Color.END}\n"
            )
        else:
            print(f"\n{Color.GREEN}Your agent is ready to start!{Color.END}\n")

        print(f"{Color.BOLD}Next steps:{Color.END}\n")

        # Check if API key is set
        api_key_env = self.config.get("provider", {}).get("api_key_env")
        if api_key_env and not os.getenv(api_key_env):
            print(f"1. {Color.YELLOW}Set your API key:{Color.END}")
            print(f"   export {api_key_env}='your-key-here'\n")
        else:
            print(f"1. {Color.GREEN}✓ API key is set{Color.END}\n")

        # Install dependencies
        provider_type = self.config["provider"]["type"]
        if provider_type == "anthropic":
            deps = "anthropic pyyaml aiohttp"
        elif provider_type == "openai":
            deps = "openai pyyaml aiohttp"
        else:  # ollama
            deps = "ollama pyyaml aiohttp"

        print(f"2. {Color.YELLOW}Install dependencies:{Color.END}")
        print(f"   pip install {deps}\n")

        # Start agent(s)
        if is_multi_agent:
            print(f"3. {Color.YELLOW}Start your agents:{Color.END}")
            config_dir = Path(output_path).parent
            if config_dir.name and str(config_dir) != ".":
                print(f"   cd {config_dir}")
            print("   forge start                    # Start all agents")
            print("   forge status                   # Check agent status")
            print()
            print(f"   {Color.CYAN}Or start individual agents:{Color.END}")
            for agent_id in list(self.config["agents"].keys())[:3]:  # Show first 3
                print(f"   forge start {agent_id}")
            if len(self.config["agents"]) > 3:
                print("   ...")
            print()
        else:
            print(f"3. {Color.YELLOW}Start your agent:{Color.END}")
            config_dir = Path(output_path).parent
            if config_dir.name and str(config_dir) != ".":
                print(f"   cd {config_dir}")
            print(f"   python -m teotl.daemon.run --config {Path(output_path).name}\n")

        print(f"{Color.BOLD}Customize your agent:{Color.END}")
        print(f"  • Edit config: {output_path}")

        # Show workspace locations
        if "agent" in self.config:
            workspace = Path(
                self.config.get("daemon", {}).get("data_dir", "~/.forge/my-agent")
            ).expanduser()
            work_types = self.config.get("agent", {}).get("work_types", [])

            print(f"  • Workspace: {workspace}/")
            print("    - PERSONALITY.md  (agent voice and values)")
            print("    - INSTRUCTIONS.md (operating procedures)")

            # Show work-type specific files
            if "Goals" in work_types:
                print("    - GOALS.md        (autonomous objectives)")
            if "Missions" in work_types:
                print("    - MISSIONS.md     (recurring tasks)")

            print("    - USER.md         (your preferences)")
            print("    - SKILLS.md       (available capabilities)")
            print("    - security.yaml   (security policy)")
        elif "agents" in self.config:
            print("  • Agent workspaces:")
            for agent_id, agent_config in list(self.config["agents"].items())[:3]:
                workspace = Path(
                    agent_config.get("workspace", f"~/.forge/agents/{agent_id}")
                ).expanduser()
                print(f"    - {agent_id}: {workspace}/")
            if len(self.config["agents"]) > 3:
                print(f"    ... and {len(self.config['agents']) - 3} more")

        print()
        print(f"{Color.BOLD}Documentation:{Color.END}")
        print("  • Full docs: docs/")
        if is_multi_agent:
            print("  • Multi-agent guide: docs/MULTI_AGENT.md")
        print("  • Workspace files: docs/WORKSPACE_FILES.md\n")

        print(f"{Color.CYAN}Happy automating! 🤖{Color.END}\n")


def main() -> None:
    """Main entry point."""
    try:
        wizard = OnboardingWizard()
        wizard.run()
    except KeyboardInterrupt:
        print(f"\n\n{Color.YELLOW}Setup cancelled.{Color.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

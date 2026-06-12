"""Tests for the onboarding wizard."""

from unittest.mock import MagicMock, patch

import pytest

from teotl.cli.wizard import OnboardingWizard, ask_choice, ask_question, ask_yes_no


class TestAskFunctions:
    """Test the helper ask functions."""

    @patch("builtins.input", return_value="test answer")
    def test_ask_question_with_input(self, mock_input):
        """Test asking a question with user input."""
        result = ask_question("What is your name?")
        assert result == "test answer"
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="")
    def test_ask_question_with_default(self, mock_input):
        """Test asking a question with default value."""
        result = ask_question("What is your name?", default="John")
        assert result == "John"

    @patch("builtins.input", return_value="1")
    def test_ask_choice_with_number(self, mock_input):
        """Test choosing from options with number."""
        result = ask_choice("Pick one", ["apple", "banana", "cherry"])
        assert result == "apple"

    @patch("builtins.input", return_value="")
    def test_ask_choice_with_default(self, mock_input):
        """Test choosing from options with default."""
        result = ask_choice("Pick one", ["apple", "banana"], default="banana")
        assert result == "banana"

    @patch("builtins.input", side_effect=["5", "2"])
    def test_ask_choice_with_invalid_then_valid(self, mock_input):
        """Test choosing with invalid input then valid."""
        result = ask_choice("Pick one", ["apple", "banana"])
        assert result == "banana"
        assert mock_input.call_count == 2

    @patch("builtins.input", return_value="y")
    def test_ask_yes_no_yes(self, mock_input):
        """Test yes/no question with yes."""
        result = ask_yes_no("Proceed?")
        assert result is True

    @patch("builtins.input", return_value="n")
    def test_ask_yes_no_no(self, mock_input):
        """Test yes/no question with no."""
        result = ask_yes_no("Proceed?")
        assert result is False

    @patch("builtins.input", return_value="")
    def test_ask_yes_no_default(self, mock_input):
        """Test yes/no question with default."""
        result = ask_yes_no("Proceed?", default=True)
        assert result is True


class TestOnboardingWizard:
    """Test the onboarding wizard."""

    def test_wizard_initialization(self):
        """Test wizard initializes correctly."""
        wizard = OnboardingWizard()
        assert wizard.config == {}

    @patch("builtins.input", side_effect=["1"])  # Choose model
    @patch("os.getenv", return_value="test-key")
    @patch("builtins.print")
    def test_setup_anthropic(self, mock_print, mock_getenv, mock_input):
        """Test setting up Anthropic provider."""
        wizard = OnboardingWizard()
        wizard.config["provider"] = {"type": "anthropic"}
        wizard._setup_anthropic()

        assert wizard.config["provider"]["type"] == "anthropic"
        assert "model" in wizard.config["provider"]
        assert wizard.config["provider"]["api_key_env"] == "ANTHROPIC_API_KEY"

    @patch("builtins.input", side_effect=["1"])  # Choose gpt-4o
    @patch("os.getenv", return_value="test-key")
    @patch("builtins.print")
    def test_setup_openai(self, mock_print, mock_getenv, mock_input):
        """Test setting up OpenAI provider."""
        wizard = OnboardingWizard()
        wizard.config["provider"] = {"type": "openai"}
        wizard._setup_openai()

        assert wizard.config["provider"]["type"] == "openai"
        assert "model" in wizard.config["provider"]
        assert wizard.config["provider"]["api_key_env"] == "OPENAI_API_KEY"

    @patch("builtins.input", side_effect=["llama3.1"])  # Model name
    @patch("builtins.print")
    def test_setup_ollama(self, mock_print, mock_input):
        """Test setting up Ollama provider."""
        wizard = OnboardingWizard()
        wizard.config["provider"] = {"type": "ollama"}
        wizard._setup_ollama()

        assert wizard.config["provider"]["type"] == "ollama"
        assert wizard.config["provider"]["model"] == "llama3.1"

    @patch(
        "builtins.input",
        side_effect=[
            "1",  # Single agent
            "my-agent",  # Agent ID
            "You are a helpful assistant",  # Instructions
            "",  # Work types (use defaults)
        ],
    )
    def test_setup_agent(self, mock_input):
        """Test setting up agent configuration."""
        wizard = OnboardingWizard()
        wizard._setup_agent()

        assert wizard.config["agent"]["agent_id"] == "my-agent"
        assert "helpful assistant" in wizard.config["agent"]["instructions"]
        assert wizard.config["agent"]["auto_approve"] is True
        assert "work_types" in wizard.config["agent"]

    @patch("builtins.input", side_effect=["1", "~/.teotl/test-agent"])  # 30 seconds
    def test_setup_daemon(self, mock_input):
        """Test setting up daemon configuration."""
        wizard = OnboardingWizard()
        wizard.config["agent"] = {"agent_id": "test-agent"}
        wizard._setup_daemon()

        assert wizard.config["daemon"]["poll_interval"] == 30
        assert "~/.teotl/test-agent" in wizard.config["daemon"]["data_dir"]

    @patch("builtins.input", side_effect=["y", "y"])  # Use rate limits, use defaults
    def test_setup_rate_limits_defaults(self, mock_input):
        """Test setting up default rate limits."""
        wizard = OnboardingWizard()
        wizard._setup_rate_limits()

        assert wizard.config["rate_limits"]["max_requests_per_minute"] == 10
        assert wizard.config["rate_limits"]["max_cost_per_minute"] == 0.50

    @patch("builtins.input", return_value="n")  # Skip rate limits
    @patch("builtins.print")
    def test_setup_rate_limits_skip(self, mock_print, mock_input):
        """Test skipping rate limits."""
        wizard = OnboardingWizard()
        wizard._setup_rate_limits()

        assert "rate_limits" not in wizard.config

    @patch(
        "builtins.input",
        side_effect=[
            "y",  # Add tasks
            "Test task",  # description
            "3",  # HIGH priority (3rd in list)
            "1",  # 1 hour expiration
            "n",  # No context
            "n",  # Don't add another
        ],
    )
    def test_setup_tasks(self, mock_input):
        """Test setting up tasks."""
        wizard = OnboardingWizard()
        wizard._setup_tasks()

        assert len(wizard.config["tasks"]) == 1
        assert wizard.config["tasks"][0]["description"] == "Test task"
        assert wizard.config["tasks"][0]["priority"] == "HIGH"
        assert wizard.config["tasks"][0]["expires_minutes"] == 60

    @patch("builtins.input", return_value="n")  # Skip tasks
    @patch("builtins.print")
    def test_setup_tasks_examples(self, mock_print, mock_input):
        """Test creating example tasks when none added."""
        wizard = OnboardingWizard()
        wizard._setup_tasks()

        assert len(wizard.config["tasks"]) == 2  # Example tasks added

    @patch(
        "builtins.input",
        side_effect=[
            "y",  # Add missions
            "Check status",  # description
            "1",  # HOURLY
            "y",  # Can be interrupted
            "2",  # URGENT threshold
            "n",  # Don't add another
        ],
    )
    def test_setup_missions(self, mock_input):
        """Test setting up missions."""
        wizard = OnboardingWizard()
        wizard._setup_missions()

        assert len(wizard.config["missions"]) == 1
        assert wizard.config["missions"][0]["description"] == "Check status"
        assert wizard.config["missions"][0]["interval"] == "HOURLY"
        assert wizard.config["missions"][0]["can_be_interrupted"] is True
        assert wizard.config["missions"][0]["interrupt_threshold"] == "URGENT"

    @patch("builtins.input", return_value="n")  # Skip missions
    @patch("builtins.print")
    def test_setup_missions_examples(self, mock_print, mock_input):
        """Test creating example missions when none added."""
        wizard = OnboardingWizard()
        wizard._setup_missions()

        assert len(wizard.config["missions"]) == 1  # Example mission added

    @patch("builtins.input", return_value="n")  # Don't save
    @patch("builtins.print")
    def test_review_config_reject(self, mock_print, mock_input):
        """Test rejecting configuration."""
        wizard = OnboardingWizard()
        wizard.config = {"provider": {"type": "anthropic"}}

        result = wizard._review_config()
        assert result is False

    @patch("builtins.input", return_value="y")  # Save
    @patch("builtins.print")
    def test_review_config_accept(self, mock_print, mock_input):
        """Test accepting configuration."""
        wizard = OnboardingWizard()
        wizard.config = {"provider": {"type": "anthropic"}}

        result = wizard._review_config()
        assert result is True

    @patch("teotl.cli.wizard.OnboardingWizard._offer_auto_start")  # Skip auto-start
    @patch("teotl.cli.wizard.OnboardingWizard._create_workspace_files")  # Skip file creation
    @patch("builtins.input", side_effect=["test_config.yaml", "y"])  # Path, overwrite
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.print")
    def test_save_config(
        self, mock_print, mock_exists, mock_open, mock_input, mock_create_workspace, mock_auto_start
    ):
        """Test saving configuration to file."""
        wizard = OnboardingWizard()
        # Provide minimal valid config for daemon pattern
        wizard.config = {
            "execution_pattern": "daemon",
            "provider": {"type": "anthropic"},
            "agent": {"agent_id": "test-agent"},
        }

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        wizard._save_config()

        assert "_output_path" in wizard.config
        mock_file.write.assert_called()  # Config was written
        mock_create_workspace.assert_called_once()  # Workspace creation called
        mock_auto_start.assert_called_once()  # Auto-start offer called

    @patch("teotl.cli.wizard.OnboardingWizard._offer_auto_start")  # Skip auto-start
    @patch("teotl.cli.wizard.OnboardingWizard._create_workspace_files")  # Skip file creation
    @patch("builtins.input", side_effect=["test_config.yaml", "n", "other.yaml"])
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.print")
    def test_save_config_different_path(
        self, mock_print, mock_exists, mock_open, mock_input, mock_create_workspace, mock_auto_start
    ):
        """Test saving to different path when rejecting overwrite."""
        wizard = OnboardingWizard()
        # Provide minimal valid config for daemon pattern
        wizard.config = {
            "execution_pattern": "daemon",
            "provider": {"type": "anthropic"},
            "agent": {"agent_id": "test-agent"},
        }

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        wizard._save_config()

        assert mock_input.call_count == 3  # Asked for path twice + overwrite once


class TestWizardIntegration:
    """Integration tests for full wizard flow."""

    @pytest.mark.skip(
        reason="Wizard flow has changed - needs complete test rewrite with updated question flow"
    )
    @patch("teotl.cli.wizard.OnboardingWizard._validate_skills")
    @patch("builtins.input")
    @patch("builtins.open", create=True)
    @patch("os.getenv", return_value="test-key")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("builtins.print")
    def test_full_wizard_flow_anthropic(
        self, mock_print, mock_exists, mock_getenv, mock_open, mock_input, mock_validate_skills
    ):
        """Test complete wizard flow with Anthropic."""
        # Simulate user inputs for entire flow
        mock_input.side_effect = [
            "1",  # Execution pattern: Daemon
            "1",  # Provider: Anthropic
            "1",  # Model: claude-sonnet-4 (recommended)
            "1",  # Single agent
            "test-agent",  # Agent ID
            "Test agent instructions",  # Instructions
            "",  # Work types (use defaults: Goals)
            "n",  # Enable memory? No
            "",  # Skills (use defaults: Filesystem, Web)
            "",  # Default workspace
            "n",  # Skip security config
            "n",  # Skip harness features
            "1",  # 30s poll interval
            "",  # Default data dir
            "y",  # Use rate limits
            "y",  # Use rate limit defaults
            "n",  # Skip tasks (use examples)
            "n",  # Skip missions (use examples)
            "n",  # Skip goals
            "y",  # Save config
            "test_config.yaml",  # Output path
        ]

        # Mock skills validation to return all skills as valid
        mock_validate_skills.return_value = (["filesystem", "web"], [])

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        wizard = OnboardingWizard()
        config = wizard.run()

        # Verify complete configuration
        assert config["execution_pattern"] == "daemon"
        assert config["provider"]["type"] == "anthropic"
        assert config["agent"]["agent_id"] == "test-agent"
        assert config["daemon"]["poll_interval"] == 30
        assert "rate_limits" in config

    @pytest.mark.skip(
        reason="Wizard flow has changed - needs complete test rewrite with updated question flow"
    )
    @patch("teotl.cli.wizard.OnboardingWizard._validate_skills")
    @patch("builtins.input")
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.exists", return_value=False)
    @patch("builtins.print")
    def test_full_wizard_flow_ollama(
        self, mock_print, mock_exists, mock_open, mock_input, mock_validate_skills
    ):
        """Test complete wizard flow with Ollama."""
        mock_input.side_effect = [
            "1",  # Execution pattern: Daemon
            "3",  # Provider: Ollama
            "",  # Model: llama3.1:latest (default)
            "1",  # Single agent
            "local-agent",  # Agent ID
            "",  # Default instructions
            "",  # Work types (use defaults: Goals)
            "n",  # Enable memory? No
            "",  # Skills (use defaults: Filesystem, Web)
            "",  # Default workspace
            "n",  # Skip security config
            "n",  # Skip harness features
            "2",  # 60s poll interval
            "",  # Default data dir
            "n",  # Skip rate limits
            "n",  # Skip tasks
            "n",  # Skip missions
            "n",  # Skip goals
            "y",  # Save config
            "ollama_config.yaml",  # Output path
        ]

        # Mock skills validation to return all skills as valid
        mock_validate_skills.return_value = (["filesystem", "web"], [])

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        wizard = OnboardingWizard()
        config = wizard.run()

        assert config["execution_pattern"] == "daemon"
        assert config["provider"]["type"] == "ollama"
        assert config["agent"]["agent_id"] == "local-agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

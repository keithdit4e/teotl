"""Integration tests for guardrails in the agent loop."""

import pytest

from teotl.core.agent import Agent
from teotl.core.types import CompletionResult, ToolCall


class MockProvider:
    """Mock provider that returns bash tool calls."""

    def __init__(self, command: str = "ls -la"):
        self.command = command
        self.complete_calls = []
        self.call_count = 0

    async def complete(self, **kwargs):
        """Return a mock tool call on first call, then done on subsequent calls."""
        self.complete_calls.append(kwargs)
        self.call_count += 1

        # First call: return tool call
        if self.call_count % 2 == 1:
            return CompletionResult(
                content="",
                tool_calls=[
                    ToolCall(
                        id=f"test_call_{self.call_count}",
                        name="bash",
                        args={"command": self.command},
                    )
                ],
                done=False,  # Continue after tool execution
                usage={"input_tokens": 100, "output_tokens": 50},
                raw={},
            )
        # Second call (after tool execution): return completion
        else:
            return CompletionResult(
                content="Task completed",
                tool_calls=[],
                done=True,  # Indicate completion
                usage={"input_tokens": 100, "output_tokens": 50},
                raw={},
            )

    @property
    def context_window(self) -> int:
        return 8192

    @property
    def model_name(self) -> str:
        return "mock-model"

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class MockUI:
    """Mock UI for testing confirmations."""

    def __init__(self, auto_approve: bool = True):
        self.auto_approve = auto_approve
        self.confirmations = []

    async def confirm(self, message: str, *, title: str = "") -> bool:
        self.confirmations.append({"message": message, "title": title})
        return self.auto_approve

    async def display(self, message: str) -> None:
        pass

    async def input(self, prompt: str = "") -> str:
        return ""

    async def error(self, message: str) -> None:
        pass


class TestGuardrailsIntegration:
    """Test guardrails integration with agent loop."""

    @pytest.mark.asyncio
    async def test_guardrails_initialized_by_default(self):
        """Test that guardrails are initialized with default policy."""
        provider = MockProvider()
        agent = Agent(provider=provider, policy="standard")

        assert agent.guardrails is not None
        assert agent.guardrails.policy is not None

    @pytest.mark.asyncio
    async def test_safe_action_allowed(self):
        """Test that safe bash commands are allowed."""
        provider = MockProvider(command="ls -la")  # Safe read command
        agent = Agent(provider=provider, policy="standard")
        ui = MockUI(auto_approve=True)

        # Register bash tool
        call_count = 0

        async def bash_handler(command: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"Output: {command}"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        # Run the agent
        await agent.run("List files", ui=ui)

        # Tool should have been called (safe action)
        assert call_count > 0

        # Should not have asked for confirmation (safe action)
        assert len(ui.confirmations) == 0

    @pytest.mark.asyncio
    async def test_write_action_requires_confirmation(self):
        """Test that write commands require confirmation."""
        provider = MockProvider(command="echo 'test' > file.txt")  # Write command
        agent = Agent(provider=provider, policy="standard")
        ui = MockUI(auto_approve=True)

        call_count = 0

        async def bash_handler(command: str) -> str:
            nonlocal call_count
            call_count += 1
            return "File written"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        await agent.run("Write to file", ui=ui)

        # Tool should have been called (user approved)
        assert call_count > 0

        # Should have asked for confirmation
        assert len(ui.confirmations) > 0
        assert "🛡️" in ui.confirmations[0]["message"]

    @pytest.mark.asyncio
    async def test_destructive_action_blocked(self):
        """Test that destructive commands are blocked."""
        provider = MockProvider(command="rm -rf /")  # Destructive command
        agent = Agent(provider=provider, policy="standard")
        ui = MockUI(auto_approve=True)

        call_count = 0

        async def bash_handler(command: str) -> str:
            nonlocal call_count
            call_count += 1
            return "Should not execute"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        await agent.run("Delete everything", ui=ui)

        # Tool should NOT have been called (blocked)
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_user_denial_blocks_action(self):
        """Test that user denial blocks the action."""
        provider = MockProvider(command="echo 'test' > file.txt")
        agent = Agent(provider=provider, policy="standard")
        ui = MockUI(auto_approve=False)  # User denies

        call_count = 0

        async def bash_handler(command: str) -> str:
            nonlocal call_count
            call_count += 1
            return "File written"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        await agent.run("Write to file", ui=ui)

        # Tool should NOT have been called (user denied)
        assert call_count == 0

        # Should have asked for confirmation
        assert len(ui.confirmations) > 0

    @pytest.mark.asyncio
    async def test_strict_policy_more_restrictive(self):
        """Test that strict policy requires confirmation for more actions."""
        provider = MockProvider(command="ls -la")
        agent = Agent(provider=provider, policy="strict")
        ui = MockUI(auto_approve=True)

        call_count = 0

        async def bash_handler(command: str) -> str:
            nonlocal call_count
            call_count += 1
            return "Output"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        await agent.run("List files", ui=ui)

        # With strict policy, even ls requires confirmation
        assert len(ui.confirmations) > 0

    @pytest.mark.asyncio
    async def test_permissive_policy_allows_writes(self):
        """Test that permissive policy allows write operations."""
        provider = MockProvider(command="echo 'test' > file.txt")
        agent = Agent(provider=provider, policy="permissive")
        ui = MockUI(auto_approve=True)

        call_count = 0

        async def bash_handler(command: str) -> str:
            nonlocal call_count
            call_count += 1
            return "File written"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        await agent.run("Write to file", ui=ui)

        # Tool should have been called
        assert call_count > 0

        # With permissive policy, writes don't require confirmation
        # (unless they're particularly dangerous)

    @pytest.mark.asyncio
    async def test_trust_building(self):
        """Test that trust builds over repeated approvals."""
        provider = MockProvider(command="echo 'test' > file.txt")
        agent = Agent(provider=provider, policy="standard")
        ui = MockUI(auto_approve=True)

        async def bash_handler(command: str) -> str:
            return "File written"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        # Run multiple times with same action
        for i in range(5):
            ui.confirmations = []  # Reset
            await agent.run(f"Write to file {i}", ui=ui)

            if i < 3:
                # First 3 times should ask for confirmation
                assert len(ui.confirmations) > 0, f"Should ask confirmation on iteration {i}"
            else:
                # After 3 approvals, should auto-approve (trust threshold)
                assert len(ui.confirmations) == 0, f"Should auto-approve on iteration {i}"

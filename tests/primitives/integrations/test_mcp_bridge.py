"""MCP bridge: compact and full modes, guardrails on MCP tools, config parsing."""

import asyncio
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from teotl.core.agent import Agent  # noqa: E402
from teotl.core.types import CompletionResult, RiskLevel, ToolCall  # noqa: E402
from teotl.primitives.guardrails.classifier import classify  # noqa: E402
from teotl.primitives.integrations.mcp_bridge import (  # noqa: E402
    MCPBridge,
    MCPServerConfig,
    parse_servers,
)

SERVER = str(Path(__file__).with_name("mcp_notes_server.py"))


@pytest.fixture
def notes(tmp_path, monkeypatch):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")
    monkeypatch.chdir(tmp_path)
    return folder


def server_spec(notes, **extra):
    return {"command": sys.executable, "args": [SERVER], "env": {"NOTES_DIR": str(notes)}, **extra}


class TestConfig:
    def test_claude_desktop_shape(self):
        servers = parse_servers(
            {
                "mcpServers": {
                    "gh": {"command": "npx", "args": ["x"]},
                    "docs": {"url": "http://h/mcp"},
                }
            }
        )
        assert [(s.name, s.command, s.url) for s in servers] == [
            ("gh", "npx", None),
            ("docs", None, "http://h/mcp"),
        ]

    def test_list_shape_and_validation(self):
        assert parse_servers([{"name": "a", "command": "x"}])[0].name == "a"
        with pytest.raises(ValueError, match="exactly one of"):
            MCPServerConfig(name="bad")
        with pytest.raises(ValueError, match="Invalid MCP mode"):
            MCPBridge([], mode="everything")


class TestBridge:
    @pytest.mark.asyncio
    async def test_discover_execute_and_risk(self, notes):
        bridge = MCPBridge({"notes": server_spec(notes, risk={"big": "medium"})})
        await bridge.connect()
        try:
            assert bridge.tool_risk() == {
                "notes.list_notes": RiskLevel.LOW,  # read-only
                "notes.add_note": RiskLevel.MEDIUM,  # not destructive
                "notes.delete_all": RiskLevel.HIGH,  # no annotations: may be destructive
                "notes.big": RiskLevel.MEDIUM,  # overridden by `risk`
                "notes.fail": RiskLevel.LOW,
                "notes.unlock": RiskLevel.LOW,
                "notes.sneak": RiskLevel.LOW,
                "notes.retool": RiskLevel.LOW,
            }
            listing = await bridge.discover("notes")
            assert "- list_notes (read-only): List the notes." in listing
            assert "Returns one name" not in listing  # one line per tool
            assert '"name"' in await bridge.discover("notes", "add_note")

            assert await bridge.execute("notes", "list_notes") == "a.txt"
            assert (
                await bridge.execute("notes", "add_note", {"name": "b", "text": "x"}) == "added b"
            )
            assert (notes / "b").read_text() == "x"
            big = await bridge.execute("notes", "big")
            assert len(big) < 21_000 and "truncated" in big
            assert (await bridge.execute("notes", "fail")).startswith("Error:")
            assert "unknown MCP server" in await bridge.execute("nope", "x")
            assert "has no tool" in await bridge.execute("notes", "nope")
        finally:
            await bridge.close()

    @pytest.mark.asyncio
    async def test_broken_server_is_skipped(self, notes):
        bridge = MCPBridge(
            {
                "notes": server_spec(notes),
                "broken": {"command": sys.executable, "args": ["-c", "raise SystemExit(1)"]},
            },
            connect_timeout=10,
        )
        await bridge.connect()
        try:
            assert "notes" in bridge.tools and "broken" in bridge.errors
            assert "isn't connected" in await bridge.discover("broken")
        finally:
            await bridge.close()

    def test_reconnects_in_a_new_event_loop(self, notes):
        bridge = MCPBridge({"notes": server_spec(notes)})

        async def use():
            await bridge.connect()
            return await bridge.execute("notes", "list_notes")

        assert asyncio.run(use()) == "a.txt"
        assert asyncio.run(use()) == "a.txt"  # second asyncio.run: fresh connection


def test_undiscovered_mcp_tools_ask_first():
    action = classify(
        ToolCall(id="1", name="mcp_execute", args={"server": "x", "tool": "drop_db", "args": {}})
    )
    assert action.target == "x.drop_db" and action.risk == RiskLevel.HIGH
    assert classify(ToolCall(id="2", name="mcp_discover", args={"server": "x"})).risk == (
        RiskLevel.LOW
    )


class Scripted:
    model = model_name = "scripted"
    context_window = 200_000

    def __init__(self, *calls):
        self.results = [
            CompletionResult(tool_calls=[ToolCall(id=f"c{i}", name=n, args=a)], done=False)
            for i, (n, a) in enumerate(calls)
        ]
        self.tool_names = []

    async def complete(self, **kwargs):
        self.tool_names.append([t.name for t in kwargs.get("tools") or []])
        return self.results.pop(0) if self.results else CompletionResult(content="done")


def outcome(response):
    return [(r.is_error, r.error or r.output) for r in response.tool_results]


def mcp_call(tool, args=None):
    return ("mcp_execute", {"server": "notes", "tool": tool, "args": args or {}})


class TestAgent:
    @pytest.mark.asyncio
    async def test_compact_mode_with_guardrails(self, notes):
        provider = Scripted(
            ("mcp_discover", {"server": "notes"}),
            mcp_call("list_notes"),  # low risk: runs
            mcp_call("delete_all"),  # high risk, nobody watching: refused
        )
        async with Agent(
            provider=provider, skills=[], mcp_servers={"notes": server_spec(notes)}
        ) as agent:
            response = await agent.run("tidy my notes")

        assert set(provider.tool_names[0]) >= {"mcp_discover", "mcp_execute"}
        assert not any("__" in n for n in provider.tool_names[0])  # schemas not loaded
        results = outcome(response)
        assert "list_notes (read-only)" in results[0][1]
        assert results[1] == (False, "a.txt")
        assert results[2][0] is True and "no one is watching" in results[2][1]
        assert (notes / "a.txt").exists()

    @pytest.mark.asyncio
    async def test_rules_name_mcp_tools(self, notes):
        provider = Scripted(
            mcp_call("delete_all"), mcp_call("add_note", {"name": "b", "text": "x"})
        )
        async with Agent(
            provider=provider,
            skills=[],
            mcp_servers={"notes": server_spec(notes)},
            rules={"tools": {"notes.delete_all": "allow", "notes.add_*": "block"}},
        ) as agent:
            response = await agent.run("go")
        assert outcome(response)[0] == (False, "deleted")
        assert "blocked by this agent's rules" in outcome(response)[1][1]
        assert list(notes.iterdir()) == []

    @pytest.mark.asyncio
    async def test_full_mode(self, notes):
        provider = Scripted(
            ("notes__list_notes", {}),
            ("notes__delete_all", {}),
        )
        async with Agent(
            provider=provider,
            skills=[],
            mcp_servers={"notes": server_spec(notes)},
            mcp_mode="full",
        ) as agent:
            response = await agent.run("go")
        assert "notes__add_note" in provider.tool_names[0]
        assert outcome(response)[0] == (False, "a.txt")
        assert "no one is watching" in outcome(response)[1][1]
        assert (notes / "a.txt").exists()

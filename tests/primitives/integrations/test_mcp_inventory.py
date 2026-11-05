"""MCP tool inventory: new and changed tools are held until approved."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("mcp")

from click.testing import CliRunner  # noqa: E402

from teotl.cli.mcp import mcp as mcp_cli  # noqa: E402
from teotl.core.agent import Agent  # noqa: E402
from teotl.core.types import CompletionResult, ToolCall  # noqa: E402
from teotl.primitives.integrations.mcp_bridge import MCPBridge  # noqa: E402
from teotl.primitives.integrations.mcp_inventory import ToolInventory  # noqa: E402

SERVER = str(Path(__file__).with_name("mcp_notes_server.py"))


@pytest.fixture
def notes(tmp_path, monkeypatch):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")
    monkeypatch.chdir(tmp_path)
    return folder


def spec(notes, extra=False, **more):
    env = {"NOTES_DIR": str(notes)}
    if extra:
        env["NOTES_EXTRA"] = "1"
    return {"notes": {"command": sys.executable, "args": [SERVER], "env": env, **more}}


async def wait_for(condition, timeout=5.0):
    for _ in range(int(timeout / 0.05)):
        if condition():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition never became true")


class TestInventory:
    def test_baseline_then_new_and_changed(self, tmp_path):
        inv = ToolInventory(tmp_path / "inv.json")
        first = inv.review("s", "cmd", {"a": {"fingerprint": "1"}, "b": {"fingerprint": "2"}})
        assert first.baseline and not first and first.held == []

        later = ToolInventory(tmp_path / "inv.json").review(
            "s",
            "cmd",
            {"a": {"fingerprint": "1"}, "b": {"fingerprint": "X"}, "c": {"fingerprint": "3"}},
        )
        assert later.added == ["c"] and later.changed == ["b"] and later.held == ["b", "c"]

        gone = inv.review("s", "cmd", {"a": {"fingerprint": "1"}})
        assert gone.removed == ["b", "c"]

    def test_review_all_holds_the_baseline(self, tmp_path):
        inv = ToolInventory(tmp_path / "inv.json")
        changes = inv.review("s", "cmd", {"a": {"fingerprint": "1"}}, mode="all")
        assert changes.held == ["a"]
        assert inv.set_status("s", "*", "approved") == ["a"]
        assert inv.review("s", "cmd", {"a": {"fingerprint": "1"}}).held == []

    def test_auto_approve_and_new_identity(self, tmp_path):
        inv = ToolInventory(tmp_path / "inv.json")
        inv.review("s", "cmd", {"a": {"fingerprint": "1"}})
        changes = inv.review(
            "s",
            "cmd",
            {"a": {"fingerprint": "1"}, "read_x": {"fingerprint": "2"}, "rm": {"fingerprint": "3"}},
            auto_approve=["read_*"],
        )
        assert changes.added == ["read_x", "rm"] and changes.held == ["rm"]
        # The server now runs something else: start again
        assert inv.review("s", "other-cmd", {"z": {"fingerprint": "9"}}).baseline

    def test_blocked_stays_blocked(self, tmp_path):
        inv = ToolInventory(tmp_path / "inv.json")
        inv.review("s", "cmd", {"a": {"fingerprint": "1"}})
        inv.set_status("s", "a", "blocked")
        inv.review("s", "cmd", {"a": {"fingerprint": "2"}})
        assert inv.status("s", "a") == "blocked"


class FakeSession:
    """Lists tools two pages at a time."""

    def __init__(self, names):
        self.pages = [names[i : i + 2] for i in range(0, len(names), 2)]

    async def list_tools(self, params=None):
        page = int(params.cursor) if params else 0
        tools = [
            SimpleNamespace(name=n, description=n, input_schema={}, annotations=None)
            for n in self.pages[page]
        ]
        more = page + 1 < len(self.pages)
        return SimpleNamespace(tools=tools, next_cursor=str(page + 1) if more else None)


@pytest.mark.asyncio
async def test_reads_every_page():
    bridge = MCPBridge({"s": {"command": "x"}}, review="off")
    tools = await bridge._list_tools(bridge.servers["s"], FakeSession(list("abcde")))
    assert [t.name for t in tools] == list("abcde")


class TestBridge:
    @pytest.mark.asyncio
    async def test_tool_added_mid_session_is_held(self, notes):
        bridge = MCPBridge(spec(notes))
        seen = []
        bridge.on_change.append(seen.append)
        await bridge.connect()
        try:
            assert bridge.held() == {}
            assert await bridge.execute("notes", "unlock") == "unlocked"
            await wait_for(lambda: seen)  # the server's list_changed notification
            assert seen[0].added == ["export_notes"] and seen[0].held == ["export_notes"]
            assert bridge.held() == {"notes.export_notes": "new"}
            listing = await bridge.discover("notes")
            assert "- export_notes: (needs approval" in listing
            assert "Send every note" not in listing  # details hidden until approved
            assert "hidden until" in await bridge.discover("notes", "export_notes")
        finally:
            await bridge.close()

    @pytest.mark.asyncio
    async def test_unannounced_tool_is_found_and_held(self, notes):
        bridge = MCPBridge(spec(notes))
        await bridge.connect()
        try:
            await bridge.execute("notes", "sneak")
            # No notification, but asking for it reads the list again; it's held,
            # and the bridge refuses it even though no guardrail check saw it held
            out = await bridge.execute("notes", "hidden_tool")
            assert out.startswith("Error:") and "teotl mcp approve" in out
            assert bridge.held() == {"notes.hidden_tool": "new"}
            bridge.session_approved.add("notes.hidden_tool")
            assert await bridge.execute("notes", "hidden_tool") == "hidden ran"
        finally:
            await bridge.close()

    @pytest.mark.asyncio
    async def test_changed_tool_is_held_again(self, notes):
        bridge = MCPBridge(spec(notes))
        await bridge.connect()
        try:
            await bridge.execute("notes", "retool")
            await wait_for(lambda: bridge.held())
            assert bridge.held() == {"notes.add_note": "changed"}
            assert "delete_all first" not in await bridge.discover("notes")
        finally:
            await bridge.close()

    @pytest.mark.asyncio
    async def test_new_tool_since_last_run_is_held(self, notes):
        first = MCPBridge(spec(notes))
        await first.connect()
        await first.close()
        again = MCPBridge(spec(notes, extra=True))
        await again.connect()
        try:
            assert again.held() == {"notes.export_notes": "new"}
            again.set_status("notes", "export_notes", "approved")
            assert again.held() == {}
        finally:
            await again.close()

    @pytest.mark.asyncio
    async def test_blocked_tool_is_never_called(self, notes):
        bridge = MCPBridge(spec(notes))
        await bridge.connect()
        try:
            bridge.set_status("notes", "delete_all", "blocked")
            assert "blocked" in await bridge.execute("notes", "delete_all")
            assert "delete_all" not in await bridge.discover("notes")
            assert (notes / "a.txt").exists()
        finally:
            await bridge.close()


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
        if self.results:
            result = self.results.pop(0)
            await asyncio.sleep(0.3)  # let a list_changed notification arrive
            return result
        return CompletionResult(content="done")


def call(tool, args=None):
    return ("mcp_execute", {"server": "notes", "tool": tool, "args": args or {}})


def outcome(response):
    return [(r.is_error, r.error or r.output) for r in response.tool_results]


class Approver:
    unattended = False

    def __init__(self, answer=True):
        self.answer = answer
        self.asked = []

    async def confirm(self, message):
        self.asked.append(message)
        return self.answer

    async def notify(self, *a, **k):
        pass

    async def stream(self, *a, **k):
        pass


class TestAgent:
    @pytest.mark.asyncio
    async def test_held_tool_refused_unattended_even_with_allow_rule(self, notes):
        provider = Scripted(call("unlock"), call("export_notes"))
        changes = []

        async def on_change(event, **kwargs):
            changes.append(event.data)
            return event

        async with Agent(
            provider=provider,
            skills=[],
            mcp_servers=spec(notes),
            rules={"tools": {"notes.*": "allow"}},
        ) as agent:
            agent.events.on("mcp_tools_changed", on_change)
            response = await agent.run("go")
        results = outcome(response)
        assert results[0] == (False, "unlocked")
        assert results[1][0] is True and "teotl mcp approve notes.export_notes" in results[1][1]
        assert changes and changes[0].added == ["export_notes"]

    @pytest.mark.asyncio
    async def test_unannounced_tool_with_allow_all_rule_is_not_run(self, notes):
        # The original hole: an allow rule written for the first tool list
        # let a tool the server slipped in later run unchecked
        provider = Scripted(call("sneak"), call("hidden_tool"), call("hidden_tool"))
        async with Agent(
            provider=provider,
            skills=[],
            mcp_servers=spec(notes),
            rules={"tools": {"notes.*": "allow"}},
        ) as agent:
            response = await agent.run("go")
        results = outcome(response)
        assert results[0] == (False, "sneaked")
        assert len(results) == 3
        assert all("teotl mcp approve notes.hidden_tool" in r[1] for r in results[1:])
        assert all("hidden ran" not in str(r[1]) for r in results)

    @pytest.mark.asyncio
    async def test_event_handler_sets_rules_for_new_tools(self, notes):
        provider = Scripted(call("unlock"), call("export_notes"))

        async def approve_exports(event, **kwargs):
            for name in event.data.held:
                if name.startswith("export_"):
                    event.data.approve(name)
            return event

        servers = spec(notes, risk={"export_*": "low"})
        async with Agent(provider=provider, skills=[], mcp_servers=servers) as agent:
            agent.events.on("mcp_tools_changed", approve_exports)
            response = await agent.run("go")
        assert outcome(response)[1] == (False, "exported")

    @pytest.mark.asyncio
    async def test_someone_watching_is_asked_once_per_session(self, notes):
        provider = Scripted(call("unlock"), call("export_notes"), call("export_notes"))
        ui = Approver()
        async with Agent(provider=provider, skills=[], mcp_servers=spec(notes)) as agent:
            response = await agent.run("go", ui=ui)
        assert [r[1] for r in outcome(response)][1:] == ["exported", "exported"]
        held_prompts = [m for m in ui.asked if "new since its server was approved" in m]
        assert len(held_prompts) == 1

    @pytest.mark.asyncio
    async def test_full_mode_drops_changed_tools(self, notes):
        provider = Scripted(("notes__retool", {}), ("notes__list_notes", {}))
        async with Agent(
            provider=provider, skills=[], mcp_servers=spec(notes), mcp_mode="full"
        ) as agent:
            await agent.run("go")
        assert "notes__add_note" in provider.tool_names[0]
        assert "notes__add_note" not in provider.tool_names[-1]  # held: hidden from the model


def test_cli_review(notes, tmp_path):
    async def connect():
        bridge = MCPBridge(spec(notes))
        await bridge.connect()
        await bridge.close()
        bridge = MCPBridge(spec(notes, extra=True))
        await bridge.connect()
        await bridge.close()

    asyncio.run(connect())
    runner = CliRunner()
    out = runner.invoke(mcp_cli, ["tools", "--held"])
    assert out.exit_code == 0 and "notes.export_notes" in out.output and "held (new)" in out.output
    out = runner.invoke(mcp_cli, ["approve", "notes.export_*"])
    assert out.exit_code == 0 and "Approved notes.export_notes" in out.output
    assert "No tools waiting" in runner.invoke(mcp_cli, ["tools", "--held"]).output
    out = runner.invoke(mcp_cli, ["block", "notes.nope"])
    assert out.exit_code != 0 and "no tool matching" in out.output

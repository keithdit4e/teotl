"""Long-lived sandbox sessions: state between commands, timeouts, named Docker sessions."""

import asyncio
import os
import uuid

import pytest

from teotl.core.agent import Agent
from teotl.core.tools.bash import BashTool
from teotl.core.tools.os_sandbox import Bubblewrap, DockerSandbox, MacSandbox, SandboxSettings
from teotl.core.tools.sandbox_session import (
    container_name,
    list_sessions,
    reset_session,
    stop_session,
)
from teotl.core.types import CompletionResult, ToolCall

needs_native = pytest.mark.skipif(
    not (MacSandbox.available() or Bubblewrap.available()),
    reason="no OS sandbox (sandbox-exec or bwrap) on this machine",
)
needs_docker = pytest.mark.skipif(
    not os.environ.get("TEOTL_TEST_DOCKER") or not DockerSandbox.available(),
    reason="set TEOTL_TEST_DOCKER=1 (and TEOTL_TEST_DOCKER_IMAGE) with Docker running",
)
IMAGE = os.environ.get("TEOTL_TEST_DOCKER_IMAGE", "python:3.12-slim")


@pytest.fixture
def zone(tmp_path, monkeypatch):
    z = (tmp_path / "zone").resolve()
    (z / "sub").mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    monkeypatch.chdir(z)
    return z


def tool(zone, **settings):
    settings.setdefault("mode", "on")
    return BashTool(working_dir=zone, os_sandbox=SandboxSettings(zones=[zone], **settings))


def test_named_sessions_need_docker():
    with pytest.raises(ValueError, match="needs sandbox='docker'"):
        SandboxSettings(mode="on", session="site-dev")
    with pytest.raises(ValueError, match="Invalid sandbox session name"):
        SandboxSettings(mode="docker", session="bad name!")
    SandboxSettings(mode="on", session="agent")  # fine


@needs_native
class TestNativeSession:
    @pytest.mark.asyncio
    async def test_state_carries_over(self, zone):
        bash = tool(zone, session="agent")
        try:
            await bash.execute("cd sub && export GREETING=hi && echo x > here.txt")
            out = await bash.execute('pwd; echo "$GREETING"')
            assert str(zone / "sub") in out and "hi" in out
            assert (zone / "sub" / "here.txt").exists()
        finally:
            await bash.os_sandbox.close()

    @pytest.mark.asyncio
    async def test_background_process_keeps_running_until_close(self, zone):
        bash = tool(zone, session="agent")
        await bash.execute("(i=0; while true; do i=$((i+1)); echo $i > beat; sleep 0.1; done) &")
        await asyncio.sleep(0.5)
        first = (zone / "beat").read_text()
        await asyncio.sleep(0.5)
        assert (zone / "beat").read_text() != first  # still running between commands
        await bash.os_sandbox.close()
        await asyncio.sleep(0.4)
        stopped = (zone / "beat").read_text()
        await asyncio.sleep(0.5)
        assert (zone / "beat").read_text() == stopped  # killed with the session

    @pytest.mark.asyncio
    async def test_still_sandboxed(self, zone):
        bash = tool(zone, session="agent")
        try:
            await bash.execute("cd .. && echo bad > outside/x.txt")
            await bash.execute("python3 -c \"open('../outside/y.txt', 'w')\"")
            assert list((zone.parent / "outside").iterdir()) == []
        finally:
            await bash.os_sandbox.close()

    @pytest.mark.asyncio
    async def test_timeout_ends_the_session(self, zone):
        bash = tool(zone, session="agent")
        try:
            await bash.execute("cd sub")
            out = await bash.execute("sleep 30", timeout=1)
            assert "Timed out after 1s" in out
            out = await bash.execute("pwd")
            assert str(zone) in out and str(zone / "sub") not in out
            assert "new sandbox session" in out
        finally:
            await bash.os_sandbox.close()

    @pytest.mark.asyncio
    async def test_exit_restarts_cleanly(self, zone):
        bash = tool(zone, session="agent")
        try:
            out = await bash.execute("echo bye; exit 3")
            assert "ended the shell" in out
            assert "ok" in await bash.execute("echo ok")
        finally:
            await bash.os_sandbox.close()

    @pytest.mark.asyncio
    async def test_agent_keeps_one_session(self, zone):
        class Scripted:
            model = model_name = "scripted"
            context_window = 200_000

            def __init__(self, *commands):
                self.results = [
                    CompletionResult(
                        tool_calls=[ToolCall(id=f"c{i}", name="bash", args={"command": c})],
                        done=False,
                    )
                    for i, c in enumerate(commands)
                ]

            async def complete(self, **kwargs):
                return self.results.pop(0) if self.results else CompletionResult(content="done")

        async with Agent(
            provider=Scripted("cd sub", "pwd > where.txt"),
            skills=["filesystem"],
            sandbox="on",
            sandbox_session="agent",
            safe_zone=[zone],
        ) as agent:
            await agent.run("go")
        assert (zone / "sub" / "where.txt").read_text().strip() == str(zone / "sub")


@needs_docker
class TestNamedDockerSession:
    @pytest.fixture
    def name(self):
        session = f"test-{uuid.uuid4().hex[:8]}"
        yield session
        reset_session(session)

    @pytest.mark.asyncio
    async def test_survives_close_stop_and_restart(self, zone, name):
        bash = tool(zone, mode="docker", image=IMAGE, session=name)
        out = await bash.execute(
            "echo installed > ~/tool.txt && echo hi > in_zone.txt && cat ~/tool.txt"
        )
        assert "installed" in out and (zone / "in_zone.txt").exists()
        await bash.os_sandbox.close()  # a named session outlives the agent

        assert any(r["name"] == name and r["state"] == "running" for r in list_sessions())
        stop_session(name)
        assert any(r["name"] == name and r["state"] == "exited" for r in list_sessions())

        again = tool(zone, mode="docker", image=IMAGE, session=name)
        try:
            out = await again.execute("cat ~/tool.txt")  # restarted automatically
            assert "installed" in out
        finally:
            await again.os_sandbox.close()

        reset_session(name)
        fresh = tool(zone, mode="docker", image=IMAGE, session=name)
        try:
            out = await fresh.execute("cat ~/tool.txt 2>&1 || true")
            assert "No such file" in out
            assert (zone / "in_zone.txt").exists()  # reset never touches the safe zone
        finally:
            await fresh.os_sandbox.close()

    @pytest.mark.asyncio
    async def test_changed_settings_need_a_reset(self, zone, name):
        bash = tool(zone, mode="docker", image=IMAGE, session=name)
        await bash.execute("true")
        await bash.os_sandbox.close()
        changed = tool(zone, mode="docker", image=IMAGE, session=name, network=True)
        out = await changed.execute("true")
        assert "different settings" in out and f"teotl sandbox reset {name}" in out

    @pytest.mark.asyncio
    async def test_agent_scoped_docker_session_is_removed(self, zone):
        bash = tool(zone, mode="docker", image=IMAGE, session="agent")
        await bash.execute("cd sub")
        assert str(zone / "sub") in await bash.execute("pwd")
        container = bash.os_sandbox._session.container
        await bash.os_sandbox.close()
        assert container_name(container.removeprefix("teotl-session-")) == container
        assert not any(
            r["name"] == container.removeprefix("teotl-session-") for r in list_sessions()
        )

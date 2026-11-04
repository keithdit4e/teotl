"""OS sandbox for shell commands: backends, mode selection, and escape attempts."""

import os
from pathlib import Path

import pytest

from teotl.core.agent import Agent
from teotl.core.tools import os_sandbox
from teotl.core.tools.bash import BashTool
from teotl.core.tools.os_sandbox import (
    RUN_UNATTENDED,
    Bubblewrap,
    DockerSandbox,
    MacSandbox,
    SandboxSettings,
    SandboxSpec,
    scrub_env,
)
from teotl.core.types import CompletionResult, ToolCall

needs_native = pytest.mark.skipif(
    not (MacSandbox.available() or Bubblewrap.available()),
    reason="no OS sandbox (sandbox-exec or bwrap) on this machine",
)


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    zone, outside, secret = tmp_path / "zone", tmp_path / "outside", tmp_path / "secret"
    for d in (zone, outside, secret):
        d.mkdir()
    (secret / "id_ed25519").write_text("PRIVATE KEY")
    (zone / "link").symlink_to(outside)
    monkeypatch.chdir(zone)
    return zone.resolve(), outside.resolve(), secret.resolve()


def tool_for(zone, secret, mode="on", network=False):
    settings = SandboxSettings(mode=mode, zones=[zone], network=network)
    settings.spec = lambda cwd: SandboxSpec(  # also deny the test's fake secret folder
        writable=[zone], cwd=cwd, network=network, deny_read=[secret]
    )
    return BashTool(working_dir=zone, os_sandbox=settings)


class TestUnits:
    def test_scrub_env(self):
        env = scrub_env(
            {"PATH": "/bin", "ANTHROPIC_API_KEY": "x", "GITHUB_TOKEN": "y", "DB_PASSWORD": "z"}
        )
        assert env == {"PATH": "/bin"}

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="Invalid sandbox mode"):
            SandboxSettings(mode="maybe")
        with pytest.raises(ValueError, match="Invalid sandbox mode"):
            Agent(provider=Scripted(), skills=[], sandbox="maybe")

    def test_mac_profile(self, tmp_path):
        spec = SandboxSpec(writable=[tmp_path], cwd=tmp_path, deny_read=[tmp_path / "s"])
        profile = MacSandbox.profile(spec, tmp_path / "tmp")
        assert "(deny file-write*)" in profile
        assert f'(subpath "{tmp_path.resolve()}")' in profile
        assert "(deny network-outbound (remote ip))" in profile
        assert "docker.sock" in profile
        assert "(remote ip))" not in MacSandbox.profile(
            SandboxSpec(writable=[tmp_path], cwd=tmp_path, network=True), tmp_path
        )

    def test_bwrap_arguments(self, tmp_path):
        (tmp_path / "s").mkdir()
        spec = SandboxSpec(writable=[tmp_path], cwd=tmp_path, deny_read=[tmp_path / "s"])
        args = Bubblewrap.arguments(spec, tmp_path / "tmp")
        assert args[:4] == ["bwrap", "--ro-bind", "/", "/"]
        assert ["--bind", str(tmp_path.resolve()), str(tmp_path.resolve())] == args[
            args.index(str(tmp_path.resolve())) - 1 : args.index(str(tmp_path.resolve())) + 2
        ]
        assert "--unshare-net" in args
        assert ["--tmpfs", str((tmp_path / "s").resolve())] == args[
            args.index(str((tmp_path / "s").resolve())) - 1 : args.index(
                str((tmp_path / "s").resolve())
            )
            + 1
        ]

    def test_docker_arguments(self, tmp_path):
        spec = SandboxSpec(writable=[tmp_path], cwd=tmp_path, image="img:1")
        args = DockerSandbox.arguments(spec, "teotl-sbx-x")
        assert args[args.index("--network") : args.index("--network") + 2] == ["--network", "none"]
        assert f"{tmp_path.resolve()}:{tmp_path.resolve()}" in args
        assert "/Users" not in " ".join(a for a in args if a.startswith("-v"))
        assert args[-1] == "img:1"

    def test_mode_selection(self, monkeypatch):
        fake = MacSandbox()
        monkeypatch.setattr(os_sandbox, "backend_for", lambda mode: fake)
        assert SandboxSettings("auto").choose(unattended=True) == (fake, None)
        assert SandboxSettings("auto").choose(unattended=False) == (None, None)
        assert SandboxSettings("on").choose(unattended=False) == (fake, None)
        assert SandboxSettings("off").choose(unattended=True) == (None, None)

    def test_fails_closed_without_a_sandbox(self, monkeypatch, caplog):
        monkeypatch.setattr(os_sandbox, "backend_for", lambda mode: None)
        backend, refusal = SandboxSettings("on").choose(unattended=True)
        assert backend is None and "can't run safely" in refusal
        assert "Docker isn't running" in SandboxSettings("docker").choose(True)[1]
        # auto: warn once and fall back to guardrails only
        settings = SandboxSettings("auto")
        assert settings.choose(True) == (None, None)
        assert settings.choose(True) == (None, None)
        assert caplog.text.count("No OS sandbox on this machine") == 1

    @pytest.mark.asyncio
    async def test_refusal_reaches_the_model(self, monkeypatch, tmp_path):
        monkeypatch.setattr(os_sandbox, "backend_for", lambda mode: None)
        tool = BashTool(working_dir=tmp_path, os_sandbox=SandboxSettings("on", zones=[tmp_path]))
        out = await tool.execute("touch x")
        assert out.startswith("Error: Refused: sandbox='on'")
        assert not (tmp_path / "x").exists()


@needs_native
class TestEscapes:
    """Commands the guardrails might let through; the OS must still stop them."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "command",
        [
            "echo bad > {outside}/x.txt",
            "python3 -c \"open('{outside}/x.txt', 'w').write('bad')\"",
            "cp /etc/hosts {outside}/x.txt",
            "echo bad > link/x.txt",  # symlink inside the zone pointing outside
            "cd .. && touch outside/x.txt",
        ],
    )
    async def test_cannot_write_outside(self, dirs, command):
        zone, outside, secret = dirs
        await tool_for(zone, secret).execute(command.format(outside=outside))
        assert list(outside.iterdir()) == []

    @pytest.mark.asyncio
    async def test_can_work_inside(self, dirs):
        zone, _, secret = dirs
        out = await tool_for(zone, secret).execute(
            'mkdir -p src && echo ok > src/a.txt && echo t > "$TMPDIR/t" && cat src/a.txt'
        )
        assert "ok" in out and (zone / "src" / "a.txt").exists()

    @pytest.mark.asyncio
    async def test_cannot_read_secrets(self, dirs):
        zone, _, secret = dirs
        out = await tool_for(zone, secret).execute(f"cat {secret}/id_ed25519")
        assert "PRIVATE KEY" not in out

    @pytest.mark.asyncio
    async def test_no_api_keys_in_environment(self, dirs, monkeypatch):
        zone, _, secret = dirs
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
        out = await tool_for(zone, secret).execute("env")
        assert "sk-test-not-real" not in out

    @pytest.mark.asyncio
    async def test_no_network(self, dirs):
        zone, _, secret = dirs
        # A non-routable address: refused by the sandbox at once, never sent
        out = await tool_for(zone, secret).execute(
            "python3 -c \"import socket; socket.create_connection(('10.255.255.1', 80), "
            'timeout=2)"'
        )
        assert "Operation not permitted" in out or "unreachable" in out


class Scripted:
    model = model_name = "scripted"
    context_window = 200_000

    def __init__(self, *commands):
        self.results = [
            CompletionResult(
                tool_calls=[ToolCall(id=f"c{i}", name="bash", args={"command": c})], done=False
            )
            for i, c in enumerate(commands)
        ]

    async def complete(self, **kwargs):
        return self.results.pop(0) if self.results else CompletionResult(content="done")


@needs_native
@pytest.mark.asyncio
async def test_sandbox_stops_what_approve_mode_lets_through(dirs):
    """unattended='approve' runs `python -c` without asking; the sandbox contains it."""
    zone, outside, _ = dirs
    agent = Agent(
        provider=Scripted(
            f"python3 -c \"open('{outside}/stolen.txt', 'w').write('x')\"",
            "python3 -c \"open('inside.txt', 'w').write('x')\"",
        ),
        skills=["filesystem"],
        unattended="approve",
        sandbox="on",
        safe_zone=[zone],
    )
    response = await agent.run("go")
    assert len(response.auto_approved) == 2  # the guardrails let both run
    assert list(outside.iterdir()) == []  # the OS stopped the escape
    assert (zone / "inside.txt").exists()


@needs_native
@pytest.mark.asyncio
async def test_auto_mode_sandboxes_only_unattended_runs(dirs):
    zone, outside, _ = dirs
    target = outside / "x.txt"
    command = f"python3 -c \"open('{target}', 'w').write('x')\""

    class YesUI:
        async def confirm(self, message, *, title=""):
            return True

        async def display(self, m): ...
        async def input(self, p=""):
            return ""

        async def error(self, m): ...

    watched = Agent(provider=Scripted(command), skills=["filesystem"], safe_zone=[zone])
    await watched.run("go", ui=YesUI())  # a person approved it: not sandboxed
    assert target.exists()
    target.unlink()

    unattended = Agent(
        provider=Scripted(command), skills=["filesystem"], unattended="approve", safe_zone=[zone]
    )
    await unattended.run("go")
    assert not target.exists()
    assert RUN_UNATTENDED.get() is True


@pytest.mark.skipif(
    not os.environ.get("TEOTL_TEST_DOCKER") or not DockerSandbox.available(),
    reason="set TEOTL_TEST_DOCKER=1 (and TEOTL_TEST_DOCKER_IMAGE) with Docker running",
)
@pytest.mark.asyncio
async def test_docker_backend(dirs):
    zone, outside, _ = dirs
    settings = SandboxSettings(
        mode="docker",
        zones=[zone],
        image=os.environ.get("TEOTL_TEST_DOCKER_IMAGE", os_sandbox.DEFAULT_IMAGE),
    )
    tool = BashTool(working_dir=zone, os_sandbox=settings)
    out = await tool.execute(f"echo ok > a.txt && ls {outside} 2>&1; ls /Users 2>&1")
    assert (zone / "a.txt").exists()
    assert "No such file" in out
    assert Path(zone / "a.txt").read_text().strip() == "ok"

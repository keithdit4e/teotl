"""Unattended runs: safe_zone (default), refuse and approve modes, and per-agent rules."""

import logging
from pathlib import Path

import pytest

from teotl.core.agent import Agent
from teotl.core.types import CompletionResult, ToolCall
from teotl.primitives.guardrails.unattended import inside_safe_zone, resolve_safe_zone


@pytest.fixture
def project(tmp_path, monkeypatch):
    proj = tmp_path / "project"
    (proj / "build").mkdir(parents=True)
    (proj / "build" / "old.txt").write_text("x")
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "important.txt").write_text("keep me")
    monkeypatch.chdir(proj)
    return proj


class TestSafeZoneChecker:
    @pytest.mark.parametrize(
        "command",
        [
            "rm -rf build",
            "rm -rf build/*",
            "rm build/old.txt",
            "mkdir -p dist && touch dist/a.txt",
            "echo hi > notes.txt",
            "cat build/old.txt >> notes.txt",
            "cd build && rm old.txt",
            "mv build/old.txt build/new.txt",
            "sed -i 's/a/b/' build/old.txt",
            "cat > calc.py << 'EOF'\ndef add(a, b):\n    return a + b  # /etc/hosts\nEOF",
        ],
    )
    def test_inside(self, project, command):
        inside, why = inside_safe_zone("bash", {"command": command}, [project.resolve()])
        assert inside, why

    @pytest.mark.parametrize(
        "command,reason",
        [
            ("rm -rf ../elsewhere", "outside the safe zone"),
            ("rm -rf build ../elsewhere", "outside the safe zone"),  # one path outside
            ("cd .. && rm -rf elsewhere", "outside the safe zone"),
            ("rm -rf ~/Documents", "outside the safe zone"),
            ("rm -rf $TARGET", "can't be determined"),
            ("rm -rf $(cat list.txt)", "command substitution"),
            ("git push origin main", "isn't a plain file operation"),
            ("pip install requests", "isn't a plain file operation"),
            ("sed 's/a/b/' build/old.txt", "doesn't change files"),
            ("cat > ~/.bashrc << 'EOF'\nalias x=y\nEOF", "outside the safe zone"),
            ("rm build/old.txt\nrm -rf ../elsewhere", "multi-line"),
        ],
    )
    def test_outside(self, project, command, reason):
        inside, why = inside_safe_zone("bash", {"command": command}, [project.resolve()])
        assert not inside
        assert reason in why

    def test_file_tools(self, project):
        zones = [project.resolve()]
        assert inside_safe_zone("write_file", {"path": "src/app.py"}, zones)[0]
        assert not inside_safe_zone("write_file", {"path": "../elsewhere/x"}, zones)[0]
        assert not inside_safe_zone("send_email", {"to": "x"}, zones)[0]

    def test_home_or_root_is_never_a_safe_zone(self, caplog):
        with caplog.at_level(logging.WARNING):
            assert resolve_safe_zone([Path.home()]) == []
            assert resolve_safe_zone(["/"]) == []
            assert resolve_safe_zone([Path.home().parent]) == []  # contains home
        assert "Ignoring safe zone" in caplog.text


class Scripted:
    model = model_name = "scripted"
    context_window = 200_000

    def __init__(self, *calls):
        self.results = [
            CompletionResult(tool_calls=[ToolCall(id=f"c{i}", name=n, args=a)], done=False)
            for i, (n, a) in enumerate(calls)
        ]

    async def complete(self, **kwargs):
        return self.results.pop(0) if self.results else CompletionResult(content="done")


def bash(command):
    return ("bash", {"command": command})


def agent_with(*calls, **kwargs):
    ran = []
    agent = Agent(provider=Scripted(*calls), skills=[], policy="standard", **kwargs)
    agent.register_tool("bash", "Shell", lambda command: ran.append(command) or "ok")
    agent.register_tool(
        "send_email", "Email", lambda to: ran.append(f"email {to}") or "sent", risk="medium"
    )
    return agent, ran


def outcome(response):
    return [
        (c.args.get("command") or c.name, r.is_error, r.error or "")
        for c, r in zip(response.tool_calls_made, response.tool_results, strict=True)
    ]


class TestModes:
    @pytest.mark.asyncio
    async def test_safe_zone_default(self, project):
        agent, ran = agent_with(
            bash("rm -rf build"),  # inside: allowed
            bash("rm -rf ../elsewhere"),  # outside: refused
            bash("git push origin main"),  # not a file op: refused
            ("send_email", {"to": "customer@example.com"}),  # risk=medium tool: refused
            bash("rm -rf ~"),  # critical: blocked in every mode
        )
        response = await agent.run("clean up")  # no ui= -> unattended

        assert ran == ["rm -rf build"]
        results = outcome(response)
        assert results[0][1] is False
        assert all(err for _, err, _ in results[1:])
        assert "outside the safe zone" in results[1][2]
        assert "no one is watching" in results[2][2]
        assert "Destructive action blocked" in results[4][2]
        assert response.auto_approved == []

    @pytest.mark.asyncio
    async def test_refuse_mode_refuses_even_inside(self, project):
        agent, ran = agent_with(bash("rm -rf build"), unattended="refuse")
        response = await agent.run("clean up")
        assert ran == []
        assert "unattended: refuse" in outcome(response)[0][2]

    @pytest.mark.asyncio
    async def test_approve_mode_runs_unblocked_actions_with_warning(self, project, caplog):
        with caplog.at_level(logging.WARNING, logger="teotl.core.agent"):
            agent, ran = agent_with(
                bash("rm -rf ../elsewhere"),
                ("send_email", {"to": "customer@example.com"}),
                bash("rm -rf ~"),  # still blocked
                unattended="approve",
            )
        assert "unattended='approve'" in caplog.text

        response = await agent.run("clean up")

        assert ran == ["rm -rf ../elsewhere", "email customer@example.com"]
        assert [c.name for c in response.auto_approved] == ["bash", "send_email"]
        assert outcome(response)[2][1] is True  # rm -rf ~ blocked

    @pytest.mark.asyncio
    async def test_person_watching_is_still_asked(self, project):
        asked = []

        class UI:
            async def confirm(self, message, *, title=""):
                asked.append(message)
                return False

            async def display(self, m): ...
            async def input(self, p=""):
                return ""

            async def error(self, m): ...

        agent, ran = agent_with(bash("rm -rf build"))
        await agent.run("clean up", ui=UI())
        assert len(asked) == 1 and ran == []  # asked (even inside the safe zone), declined

    @pytest.mark.asyncio
    async def test_unattended_runs_do_not_build_trust(self, project):
        from teotl.primitives.guardrails.classifier import classify

        agent, _ = agent_with(*[bash("rm -rf build") for _ in range(5)])
        await agent.run("clean up")  # allowed by the safe zone, not approved by a person
        action = classify(ToolCall(id="x", name="bash", args={"command": "rm -rf build"}))
        assert not agent.guardrails.trust.is_trusted(action)

    def test_invalid_mode(self, project):
        with pytest.raises(ValueError, match="Invalid unattended mode"):
            Agent(provider=Scripted(), skills=[], unattended="yolo")


class TestRules:
    @pytest.mark.asyncio
    async def test_allow_rules_open_specific_actions(self, project):
        agent, ran = agent_with(
            bash("git push origin main"),
            bash("git push --force origin main"),
            ("send_email", {"to": "team@dit4e.com"}),
            rules={
                "commands": {"allow": ["git push origin main"], "block": ["git push --force*"]},
                "tools": {"send_email": "allow"},
            },
        )
        response = await agent.run("ship it")
        assert ran == ["git push origin main", "email team@dit4e.com"]
        assert "blocked by this agent's rules" in outcome(response)[1][2]

    @pytest.mark.asyncio
    async def test_allow_rules_cannot_unblock(self, project):
        agent, ran = agent_with(bash("rm -rf ~"), rules={"commands": {"allow": ["rm -rf ~"]}})
        await agent.run("go")
        assert ran == []

    @pytest.mark.asyncio
    async def test_block_rules_apply_when_watching_too(self, project):
        class YesUI:
            async def confirm(self, message, *, title=""):
                return True

            async def display(self, m): ...
            async def input(self, p=""):
                return ""

            async def error(self, m): ...

        agent, ran = agent_with(bash("ls"), rules={"commands": {"block": ["ls*"]}})
        await agent.run("list", ui=YesUI())
        assert ran == []


def test_harness_passes_settings_to_worker(project):
    from teotl.primitives.harness import PlannerWorkerHarness

    harness = PlannerWorkerHarness(
        agent_id="t",
        planner_provider=Scripted(),
        worker_provider=Scripted(),
        workspace_dir=project / ".ws",
        unattended="refuse",
        worker_rules={"tools": {"send_email": "block"}},
    )
    engine = harness.worker.agent.guardrails
    assert engine.unattended_mode == "refuse"
    assert engine.rules == {"tools": {"send_email": "block"}}

    default = PlannerWorkerHarness(
        agent_id="t2",
        planner_provider=Scripted(),
        worker_provider=Scripted(),
        workspace_dir=project / ".ws2",
    )
    assert default.worker.agent.guardrails.safe_zone == [project.resolve()]


def test_config_settings_and_deprecated_auto_approve(project, caplog):
    from unittest.mock import MagicMock

    from teotl.config import AgentConfig
    from teotl.config.factory import create_agent_from_config

    provider = MagicMock()
    provider.model = "claude-sonnet-5-5"
    config = AgentConfig(
        agent_id="bot",
        auto_approve=True,
        safe_zone=[str(project)],
        rules={"commands": {"allow": ["npm run build"]}},
    )
    with caplog.at_level(logging.WARNING):
        agent = create_agent_from_config(config, provider)
    assert "`auto_approve` is deprecated and ignored" in caplog.text
    assert agent.unattended == "safe_zone"  # not switched to approve
    assert agent.guardrails.safe_zone == [project.resolve()]
    assert agent.guardrails.rules["commands"]["allow"] == ["npm run build"]

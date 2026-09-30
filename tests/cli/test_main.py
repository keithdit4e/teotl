"""Tests for the top-level `teotl` CLI group."""

import logging

from click.testing import CliRunner

from teotl import __version__
from teotl.cli import main
from teotl.core.agent import Agent


def test_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_commands_registered():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for command in ("chat", "onboard", "wizard", "security", "memory"):
        assert command in result.output


def test_memory_subcommands():
    result = CliRunner().invoke(main, ["memory", "--help"])
    assert result.exit_code == 0
    for sub in ("list", "search", "stats", "delete", "cleanup", "export", "import-memories"):
        assert sub in result.output


class _Provider:
    model = "mock-model"
    context_window = 8192
    model_name = "mock-model"


def test_unknown_policy_warns_and_disables_guardrails(caplog):
    with caplog.at_level(logging.WARNING, logger="teotl.core.agent"):
        agent = Agent(provider=_Provider(), policy="permissive")
    assert agent.guardrails is None
    assert "Guardrails DISABLED" in caplog.text


def test_known_policy_enables_guardrails():
    for policy in ("minimal", "standard", "strict"):
        assert Agent(provider=_Provider(), policy=policy).guardrails is not None


def test_security_subcommands_reach_argparse(tmp_path):
    result = CliRunner().invoke(main, ["security", "status", "--workspace", str(tmp_path)])
    assert "unexpected extra argument" not in result.output


def test_daemon_runner_imports():
    import teotl.daemon.run  # noqa: F401  (used to fail: teotl.daemon.heartbeat didn't exist)


def test_harness_worker_has_guardrails(tmp_path):
    from teotl.primitives.harness import PlannerWorkerHarness

    class P(_Provider):
        max_tokens = 1024

    for preset, level in [("autonomous-dev", "standard"), ("strict", "strict"), ("permissive", "minimal")]:
        harness = PlannerWorkerHarness(
            agent_id="t",
            planner_provider=P(),
            worker_provider=P(),
            workspace_dir=tmp_path / preset,
            worker_policy=preset,
        )
        assert harness.worker.agent.guardrails is not None
        assert harness.worker.agent.guardrails.policy.level == level

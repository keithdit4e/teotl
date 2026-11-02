"""`teotl demo` runs offline and the real guardrails/heartbeat stop every bad action."""

import asyncio

from click.testing import CliRunner
from rich.console import Console

from teotl.cli import main
from teotl.demo import run_demo


def test_demo_blocks_everything_dangerous(monkeypatch):
    executed = []
    import teotl.demo as demo

    original = demo._fake_bash

    def tracking_fake_bash(store):
        executed.append(store)
        return original(store)

    monkeypatch.setattr(demo, "_fake_bash", tracking_fake_bash)
    console = Console(record=True, width=120)
    asyncio.run(run_demo(console))
    text = console.export_text()

    assert text.count("BLOCKED") == 3  # rm -rf ~, curl | sh, cat ~/.ssh/...
    assert "declined send_email" in text
    assert "Stopped by the heartbeat monitor after 3 consecutive failures" in text
    # The only bash commands that reached a (stand-in) tool were harmless
    ran = [cmd for store in executed for cmd in store]
    assert ran == ["du -sh ~/Downloads"]


def test_demo_cli_saves_svg(tmp_path):
    out = tmp_path / "demo.svg"
    result = CliRunner().invoke(main, ["demo", "--save-svg", str(out)])
    assert result.exit_code == 0, result.output
    assert out.read_text().startswith("<svg")

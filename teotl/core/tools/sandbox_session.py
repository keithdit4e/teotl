"""Long-lived sandbox sessions: one shell that keeps its state between commands.

Without a session, every command gets a fresh sandbox. Files persist (they live
in the safe zone), but `cd`, environment variables, activated virtualenvs and
background processes (a dev server, a watcher) don't.

``Agent(sandbox_session=...)``:

- ``"agent"``: one sandboxed shell for the agent's lifetime (a planner-worker
  mission shares it across steps). Closed by ``agent.close()``.
- any other name (with ``sandbox="docker"``): a **named Docker session**. The
  container keeps its files and installed packages across runs and days:

  - ``teotl sandbox stop NAME`` stops it, and the next command starts it again
    (running processes don't survive a stop);
  - it also stops itself after ``sandbox_idle_minutes`` without commands;
  - ``teotl sandbox reset NAME`` throws the container away (the safe zone is
    never touched).

Guardrails still check every command. A command that times out ends the session
(and everything it started); the next command starts a fresh one.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from teotl.core.tools.os_sandbox import DockerSandbox, SandboxSpec, scrub_env

if TYPE_CHECKING:
    from teotl.core.tools.os_sandbox import Backend

logger = logging.getLogger(__name__)

AGENT_SCOPE = "agent"
LABEL = "teotl.session"
CONTAINER_PREFIX = "teotl-session-"
DEFAULT_IDLE_MINUTES = 240
_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$")
_SHELL = "if command -v bash >/dev/null 2>&1; then exec bash --noprofile --norc; else exec sh; fi"
_LIVE: set[ShellSession] = set()


def validate_session(value: str | None, sandbox_mode: str) -> str | None:
    if value is None:
        return None
    if not _NAME_RE.match(value):
        raise ValueError(
            f"Invalid sandbox session name {value!r}: use letters, digits, '_', '-' or '.'"
        )
    if value != AGENT_SCOPE and sandbox_mode != "docker":
        raise ValueError(
            f"Named sandbox session {value!r} needs sandbox='docker': only a container can "
            "keep installed software between runs. Use sandbox_session='agent' otherwise."
        )
    return value


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    return_code: int
    note: str = ""


class ShellSession:
    """A shell inside a sandbox, fed commands one at a time."""

    def __init__(self, io_host: Path, io_inner: str, max_output: int = 1024 * 1024) -> None:
        self.io_host = io_host
        self.io_inner = io_inner
        self.max_output = max_output
        self.process: asyncio.subprocess.Process | None = None
        self._token = secrets.token_hex(8)
        self._lock = asyncio.Lock()
        self._had_session = False

    # Subclasses: the argv/env that starts the shell, and how to clean up
    async def _shell_command(self) -> tuple[list[str], dict[str, str], Path]:
        raise NotImplementedError

    async def _after_kill(self) -> None:
        """Extra cleanup after a timeout kill."""

    @property
    def alive(self) -> bool:
        return self.process is not None and self.process.returncode is None

    async def _start(self, cwd: Path) -> None:
        argv, env, start_cwd = await self._shell_command()
        self.process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=str(start_cwd),
            env=env,
            start_new_session=True,  # its own process group, so a kill gets everything
        )
        _LIVE.add(self)

    async def run(self, command: str, cwd: Path, timeout: float) -> CommandResult:
        async with self._lock:
            note = ""
            if not self.alive:
                if self._had_session:
                    note = "(A new sandbox session was started: the last one had ended.)"
                await self._start(cwd)
                self._had_session = True
                command = f"cd {_quote(str(cwd))} || exit 1\n{command}"
            assert self.process and self.process.stdin and self.process.stdout
            script = self.io_host / "cmd.sh"
            script.write_text(command + "\n")
            for name in ("out", "err"):
                (self.io_host / name).write_text("")
            (self.io_host / "last").touch()
            io = self.io_inner
            marker = f"__TEOTL_DONE_{self._token}__"
            line = (
                f". {io}/cmd.sh </dev/null >{io}/out 2>{io}/err; "
                f"printf '\\n{marker} %s\\n' \"$?\"\n"
            )
            try:
                self.process.stdin.write(line.encode())
                await self.process.stdin.drain()
                return_code = await asyncio.wait_for(self._wait_for(marker), timeout)
            except TimeoutError:
                await self.kill()
                return CommandResult(
                    *self._read_outputs(),
                    return_code=124,
                    note=(
                        f"Timed out after {timeout:g}s. The sandbox session was ended, with "
                        "everything it started; the next command starts a fresh one "
                        "(working directory and variables are reset)."
                    ),
                )
            except (BrokenPipeError, ConnectionResetError):
                return_code = None
            stdout, stderr = self._read_outputs()
            if return_code is None:
                await self.kill()
                return CommandResult(
                    stdout,
                    stderr,
                    1,
                    note="The command ended the shell (for example with `exit`). The next "
                    "command starts a fresh sandbox session.",
                )
            return CommandResult(stdout, stderr, return_code, note=note)

    async def _wait_for(self, marker: str) -> int | None:
        assert self.process and self.process.stdout
        while True:
            raw = await self.process.stdout.readline()
            if not raw:
                return None  # the shell exited
            text = raw.decode("utf-8", errors="replace").strip()
            if text.startswith(marker):
                try:
                    return int(text.split()[-1])
                except ValueError:
                    return 1

    def _read_outputs(self) -> tuple[str, str]:
        parts = []
        for name in ("out", "err"):
            path = self.io_host / name
            try:
                with path.open("rb") as f:
                    data = f.read(self.max_output // 2 + 1)
            except OSError:
                data = b""
            text = data.decode("utf-8", errors="replace")
            if len(data) > self.max_output // 2:
                text = text[: self.max_output // 2] + "\n...(truncated)"
            parts.append(text)
        return parts[0], parts[1]

    async def kill(self) -> None:
        """End the shell and everything it started."""
        process, self.process = self.process, None
        _LIVE.discard(self)
        if process is not None and process.returncode is None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGKILL)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(process.wait(), 5)
        await self._after_kill()

    def kill_now(self) -> None:
        """Synchronous kill, for interpreter exit."""
        if self.process is not None and self.process.returncode is None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(self.process.pid, signal.SIGKILL)

    async def close(self) -> None:
        await self.kill()


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


class NativeSession(ShellSession):
    """A shell under sandbox-exec or bubblewrap; it lives as long as the agent."""

    def __init__(self, backend: Backend, spec: SandboxSpec, env: dict[str, str], **kw) -> None:
        self.backend, self.spec, self.env = backend, spec, env
        self._prepared = backend.prepare(_SHELL, spec, env)
        tmp = self._prepared.tmpdir or Path(tempfile.mkdtemp(prefix="teotl-sess-"))
        io = tmp / ".teotl-io"
        io.mkdir(exist_ok=True)
        super().__init__(io_host=io, io_inner=_quote(str(io)), **kw)

    async def _shell_command(self) -> tuple[list[str], dict[str, str], Path]:
        return (self._prepared.argv, self._prepared.env, self._prepared.cwd)

    async def close(self) -> None:
        await super().close()
        self._prepared.cleanup()


# -- Docker sessions ----------------------------------------------------------


def _docker(*args: str, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def container_name(session: str) -> str:
    return f"{CONTAINER_PREFIX}{session}"


def sessions_root() -> Path:
    from teotl.core.paths import teotl_home

    return teotl_home() / "sandboxes"


class DockerSession(ShellSession):
    """A shell in a long-lived container.

    Named sessions keep the container (files outside the safe zone, installed
    packages) until `teotl sandbox reset`. Agent-scoped ones are removed on close.
    """

    def __init__(
        self,
        spec: SandboxSpec,
        name: str | None = None,
        idle_minutes: int = DEFAULT_IDLE_MINUTES,
        root: bool = False,
        **kw,
    ) -> None:
        self.spec = spec
        self.named = name is not None
        self.session = name or f"agent-{secrets.token_hex(4)}"
        self.container = container_name(self.session)
        self.idle_minutes = idle_minutes
        self.root = root
        if self.named:
            io = sessions_root() / self.session / "io"
            io.mkdir(parents=True, exist_ok=True)
        else:
            io = Path(tempfile.mkdtemp(prefix="teotl-sess-")) / "io"
            io.mkdir()
        super().__init__(io_host=io.resolve(), io_inner="/teotl-io", **kw)

    def _config_hash(self) -> str:
        config = {
            "image": self.spec.image,
            "zones": [str(z) for z in self.spec.writable],
            "network": self.spec.network,
            "root": self.root,
        }
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]

    def _create_args(self) -> list[str]:
        spec = self.spec
        args = [
            "run", "-d",
            "--name", self.container,
            "--label", f"{LABEL}={self.session}",
            "--label", f"teotl.config={self._config_hash()}",
            "--label", f"teotl.named={'yes' if self.named else 'no'}",
            "--network", "bridge" if spec.network else "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "1024",
            "-e", "HOME=/home/teotl",
            "-e", "TMPDIR=/tmp",
            "-e", "PIP_USER=1",
            "-e", "PYTHONUSERBASE=/home/teotl/.local",
            "-e", "npm_config_prefix=/home/teotl/.npm-global",
            "-e", "PATH=/home/teotl/.local/bin:/home/teotl/.npm-global/bin:"
                  "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "-v", f"{self.io_host}:/teotl-io",
        ]  # fmt: skip
        if not self.root and hasattr(os, "getuid"):
            args += ["--user", f"{os.getuid()}:{os.getgid()}"]
        for path in spec.writable:
            args += ["-v", f"{path}:{path}"]
        # PID 1 stops the container after idle_minutes without a command
        idle = (
            "trap 'exit 0' TERM INT; touch /teotl-io/last; "
            f'while [ -z "$(find /teotl-io/last -mmin +{int(self.idle_minutes)} 2>/dev/null)" ]; '
            "do sleep 30 & wait $!; done"
        )
        return [*args, "--entrypoint", "sh", spec.image, "-c", idle]

    def _state(self) -> dict | None:
        result = _docker("inspect", self.container, timeout=30)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)[0]

    def ensure_container(self) -> None:
        """Create the container, or start it again if it was stopped."""
        state = self._state()
        if state is not None:
            labels = state.get("Config", {}).get("Labels") or {}
            if labels.get("teotl.config") != self._config_hash():
                raise RuntimeError(
                    f"Sandbox session {self.session!r} was created with different settings "
                    "(image, safe zone, network or user). Run "
                    f"`teotl sandbox reset {self.session}` to recreate it."
                )
            if not state.get("State", {}).get("Running"):
                (self.io_host / "last").touch()
                started = _docker("start", self.container)
                if started.returncode != 0:
                    raise RuntimeError(f"Couldn't start {self.container}: {started.stderr.strip()}")
                logger.info(f"Restarted sandbox session {self.session}")
            return
        created = _docker(*self._create_args(), timeout=600)
        if created.returncode != 0:
            raise RuntimeError(f"Couldn't create {self.container}: {created.stderr.strip()}")
        # A home folder the (non-root) user can write, for pip/npm installs
        _docker(
            "exec", "-u", "0", self.container,
            "sh", "-c", "mkdir -p /home/teotl && chmod 777 /home/teotl",
        )  # fmt: skip
        logger.info(f"Created sandbox session {self.session} ({self.spec.image})")

    async def _shell_command(self) -> tuple[list[str], dict[str, str], Path]:
        await asyncio.to_thread(self.ensure_container)
        argv = [
            "docker",
            "exec",
            "-i",
            "-w",
            str(self.spec.cwd),
            self.container,
            "sh",
            "-c",
            _SHELL,
        ]
        if not any(self.spec.cwd.is_relative_to(z) for z in self.spec.writable):
            argv[3:5] = ["-w", "/home/teotl"]
        return (argv, scrub_env(dict(os.environ)), Path.cwd())

    async def _after_kill(self) -> None:
        # A killed `docker exec` leaves its processes running in the container;
        # stopping the container ends them (files and installs are kept)
        await asyncio.to_thread(_docker, "kill", self.container)

    async def close(self) -> None:
        process = self.process
        self.process = None
        _LIVE.discard(self)
        if process is not None and process.returncode is None:
            with contextlib.suppress(Exception):
                process.stdin.close()  # the shell exits; background jobs keep running
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGKILL)
        if not self.named:
            await asyncio.to_thread(_docker, "rm", "-f", self.container)
            shutil.rmtree(self.io_host.parent, ignore_errors=True)


def open_session(
    scope: str,
    backend: Backend,
    spec: SandboxSpec,
    env: dict[str, str],
    idle_minutes: int = DEFAULT_IDLE_MINUTES,
    docker_root: bool = False,
) -> ShellSession:
    if isinstance(backend, DockerSandbox):
        return DockerSession(
            spec,
            name=None if scope == AGENT_SCOPE else scope,
            idle_minutes=idle_minutes,
            root=docker_root,
        )
    return NativeSession(backend, spec, env)


# -- managing named sessions (teotl sandbox ...) -------------------------------


def list_sessions() -> list[dict[str, str]]:
    result = _docker(
        "ps", "-a",
        "--filter", f"label={LABEL}",
        "--format", "{{json .}}",
    )  # fmt: skip
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker ps failed")
    rows = []
    for line in result.stdout.splitlines():
        info = json.loads(line)
        labels = dict(
            item.split("=", 1) for item in (info.get("Labels") or "").split(",") if "=" in item
        )
        rows.append(
            {
                "name": labels.get(LABEL, info.get("Names", "")),
                "state": info.get("State", ""),
                "status": info.get("Status", ""),
                "image": info.get("Image", ""),
                "named": labels.get("teotl.named", ""),
            }
        )
    return rows


def stop_session(name: str) -> str:
    result = _docker("stop", "-t", "5", container_name(name))
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return f"Stopped {name}. Files and installed packages are kept; the next command restarts it."


def start_session(name: str) -> str:
    result = _docker("start", container_name(name))
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return f"Started {name}."


def reset_session(name: str) -> str:
    result = _docker("rm", "-f", container_name(name))
    if result.returncode != 0 and "No such container" not in result.stderr:
        raise RuntimeError(result.stderr.strip())
    shutil.rmtree(sessions_root() / name, ignore_errors=True)
    return (
        f"Reset {name}: the container and its installs are gone; the next run starts clean. "
        "Files in the safe zone weren't touched."
    )


@atexit.register
def _kill_live_sessions() -> None:
    for session in list(_LIVE):
        session.kill_now()
        if isinstance(session, DockerSession) and not session.named:
            with contextlib.suppress(Exception):
                _docker("rm", "-f", session.container, timeout=20)

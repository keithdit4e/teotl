"""Run shell commands inside an operating-system sandbox.

Guardrails decide from the command text. They can't see what a script or
`python -c` does once it runs. The sandbox is the second layer: the OS itself
stops the command from writing outside the agent's safe zone, reading secrets,
or using the network, whatever code it runs.

Modes (``Agent(sandbox=...)``):

- ``auto`` (default): sandbox unattended runs when this machine has a sandbox
  (macOS ``sandbox-exec``, Linux ``bwrap``). Without one, warn once and rely on
  the guardrails alone. Runs with a person watching aren't sandboxed.
- ``on``: sandbox every command. If no sandbox is available, refuse to run
  commands (fail closed).
- ``docker``: run every command in a throwaway Docker container that can only
  see the safe zone. Strongest isolation, but the container has its own tools.
- ``off``: no sandbox.

Only the ``bash`` tool is sandboxed. Tools you register in Python run inside
your own process and aren't covered.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODES = ("auto", "on", "off", "docker")
DEFAULT_IMAGE = "python:3.12-slim"

# Read access to these (relative to home) is denied inside the sandbox
SECRET_PATHS = (
    ".ssh",
    ".aws",
    ".gnupg",
    ".azure",
    ".kube",
    ".docker",
    ".netrc",
    ".pypirc",
    ".npmrc",
    ".git-credentials",
    ".config/gh",
    ".config/gcloud",
    ".teotl/auth",
    ".forge/auth",
    "Library/Keychains",
)
# Talking to these sockets would let a command start containers outside the sandbox
DOCKER_SOCKETS = ("/var/run/docker.sock", "/run/docker.sock", "~/.docker/run/docker.sock")

# Environment variables that look like credentials are not passed to sandboxed commands
_SECRET_ENV = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH|SESSION", re.I)


def validate_mode(mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"Invalid sandbox mode {mode!r}: use one of {', '.join(MODES)}")
    return mode


def scrub_env(env: dict[str, str]) -> dict[str, str]:
    """Drop credential-looking variables (API keys, tokens, passwords)."""
    return {k: v for k, v in env.items() if not _SECRET_ENV.search(k)}


def default_secret_paths() -> list[Path]:
    home = Path.home()
    paths = [home / p for p in SECRET_PATHS]
    teotl_home = os.environ.get("TEOTL_HOME")
    if teotl_home:
        paths.append(Path(teotl_home) / "auth")
    return paths


@dataclass
class SandboxSpec:
    """What a sandboxed command may touch."""

    writable: list[Path]  # safe zone folders; a private temp folder is added
    cwd: Path
    network: bool = False
    deny_read: list[Path] = field(default_factory=default_secret_paths)
    image: str = DEFAULT_IMAGE

    def __post_init__(self) -> None:
        self.writable = [Path(p).resolve() for p in self.writable]
        self.cwd = Path(self.cwd).resolve()
        self.deny_read = [Path(os.path.expanduser(str(p))).resolve() for p in self.deny_read]


@dataclass
class Prepared:
    """A command ready to run: argv, environment, and how to clean up after a timeout."""

    argv: list[str]
    env: dict[str, str]
    cwd: Path
    kill_argv: list[str] | None = None
    tmpdir: Path | None = None

    def cleanup(self) -> None:
        if self.tmpdir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)


class Backend:
    name = "none"

    @classmethod
    def available(cls) -> bool:
        raise NotImplementedError

    def prepare(self, command: str, spec: SandboxSpec, env: dict[str, str]) -> Prepared:
        raise NotImplementedError

    @staticmethod
    def _private_tmp() -> Path:
        return Path(tempfile.mkdtemp(prefix="teotl-sbx-")).resolve()


def _sbpl_quote(path: Path | str) -> str:
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


class MacSandbox(Backend):
    """macOS `sandbox-exec` with a generated profile.

    Apple marks `sandbox-exec` as deprecated, but it ships with every macOS
    release and is what Apple's own tools and other agent sandboxes use.
    """

    name = "sandbox-exec"
    BINARY = "/usr/bin/sandbox-exec"

    @classmethod
    def available(cls) -> bool:
        return platform.system() == "Darwin" and Path(cls.BINARY).exists()

    @staticmethod
    def profile(spec: SandboxSpec, tmpdir: Path) -> str:
        writable = [*spec.writable, tmpdir]
        lines = [
            "(version 1)",
            "(allow default)",
            # Writes: only the safe zone, a private temp folder, and harmless devices
            "(deny file-write*)",
            "(allow file-write*",
            *[f"  (subpath {_sbpl_quote(p)})" for p in writable],
            '  (literal "/dev/null") (literal "/dev/zero") (literal "/dev/tty")',
            '  (literal "/dev/dtracehelper") (regex #"^/dev/fd/")',
            '  (literal "/dev/stdout") (literal "/dev/stderr"))',
        ]
        if spec.deny_read:
            lines.append("(deny file-read* file-write*")
            lines += [f"  (subpath {_sbpl_quote(p)})" for p in spec.deny_read]
            lines.append(")")
        sockets = [Path(os.path.expanduser(s)) for s in DOCKER_SOCKETS]
        lines.append("(deny network-outbound")
        lines += [f"  (remote unix-socket (path-literal {_sbpl_quote(s)}))" for s in sockets]
        lines.append(")")
        if not spec.network:
            lines += [
                "(deny network-outbound (remote ip))",
                '(allow network-outbound (remote ip "localhost:*"))',
                "(deny network-bind (local ip))",
                '(allow network-bind (local ip "localhost:*"))',
            ]
        return "\n".join(lines) + "\n"

    def prepare(self, command: str, spec: SandboxSpec, env: dict[str, str]) -> Prepared:
        tmpdir = self._private_tmp()
        argv = [self.BINARY, "-p", self.profile(spec, tmpdir), "/bin/sh", "-c", command]
        env = {**scrub_env(env), "TMPDIR": str(tmpdir)}
        return Prepared(argv=argv, env=env, cwd=spec.cwd, tmpdir=tmpdir)


class Bubblewrap(Backend):
    """Linux bubblewrap (`bwrap`): a read-only view of the system plus the safe zone."""

    name = "bwrap"

    @classmethod
    def available(cls) -> bool:
        if platform.system() != "Linux" or not shutil.which("bwrap"):
            return False
        # User namespaces can be disabled (some distros, unprivileged containers)
        try:
            probe = subprocess.run(
                ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "true"],
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return probe.returncode == 0

    @staticmethod
    def arguments(spec: SandboxSpec, tmpdir: Path) -> list[str]:
        args = [
            "bwrap",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            "--bind", str(tmpdir), str(tmpdir),
        ]  # fmt: skip
        for path in spec.writable:
            args += ["--bind", str(path), str(path)]
        for path in spec.deny_read:
            if path.is_dir():
                args += ["--tmpfs", str(path)]
            elif path.exists():
                args += ["--ro-bind", "/dev/null", str(path)]
        for sock in DOCKER_SOCKETS:
            sock_path = Path(os.path.expanduser(sock))
            if sock_path.exists():
                args += ["--ro-bind", "/dev/null", str(sock_path)]
        if not spec.network:
            args.append("--unshare-net")
        args += [
            "--unshare-pid",
            "--unshare-ipc",
            "--die-with-parent",
            "--new-session",
            "--chdir", str(spec.cwd),
        ]  # fmt: skip
        return args

    def prepare(self, command: str, spec: SandboxSpec, env: dict[str, str]) -> Prepared:
        tmpdir = self._private_tmp()
        argv = [*self.arguments(spec, tmpdir), "/bin/sh", "-c", command]
        env = {**scrub_env(env), "TMPDIR": str(tmpdir)}
        return Prepared(argv=argv, env=env, cwd=spec.cwd, tmpdir=tmpdir)


class DockerSandbox(Backend):
    """A throwaway container that sees only the safe zone (mounted at the same path)."""

    name = "docker"

    @classmethod
    def available(cls) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            probe = subprocess.run(["docker", "info"], capture_output=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return probe.returncode == 0

    @staticmethod
    def arguments(spec: SandboxSpec, name: str) -> list[str]:
        cwd = spec.cwd
        if not any(cwd == p or cwd.is_relative_to(p) for p in spec.writable):
            cwd = spec.writable[0] if spec.writable else Path("/tmp")
        args = [
            "docker", "run", "--rm", "-i",
            "--name", name,
            "--network", "bridge" if spec.network else "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "512",
            "-e", "HOME=/tmp",
            "-e", "TMPDIR=/tmp",
        ]  # fmt: skip
        if hasattr(os, "getuid"):
            args += ["--user", f"{os.getuid()}:{os.getgid()}"]
        for path in spec.writable:
            args += ["-v", f"{path}:{path}"]
        return [*args, "-w", str(cwd), spec.image]

    def prepare(self, command: str, spec: SandboxSpec, env: dict[str, str]) -> Prepared:
        name = f"teotl-sbx-{uuid.uuid4().hex[:12]}"
        argv = [*self.arguments(spec, name), "sh", "-c", command]
        return Prepared(
            argv=argv,
            env=scrub_env(env),  # for the docker client itself
            cwd=spec.cwd,
            kill_argv=["docker", "kill", name],
        )


def native_backend() -> Backend | None:
    """The OS sandbox for this machine, if there is one."""
    for backend in (MacSandbox, Bubblewrap):
        if backend.available():
            return backend()
    return None


def backend_for(mode: str) -> Backend | None:
    """The backend for a mode; None for `off`, or when none is available."""
    if mode == "off":
        return None
    if mode == "docker":
        return DockerSandbox() if DockerSandbox.available() else None
    return native_backend()


INSTALL_HINT = (
    "On Linux install bubblewrap (apt install bubblewrap / dnf install bubblewrap), "
    "or use sandbox='docker'."
)


# Set by Agent.run(): True when no one is watching (no ui= given). Calls made outside
# a run (a developer calling the tool directly) count as watched.
RUN_UNATTENDED: ContextVar[bool] = ContextVar("teotl_run_unattended", default=False)


class SandboxSettings:
    """An agent's sandbox settings; picks the backend for each command."""

    def __init__(
        self,
        mode: str = "auto",
        zones: list[Path] | None = None,
        network: bool = False,
        image: str = DEFAULT_IMAGE,
        session: str | None = None,
        idle_minutes: int = 240,
        docker_root: bool = False,
    ) -> None:
        from teotl.core.tools.sandbox_session import validate_session

        self.mode = validate_mode(mode)
        self.zones = list(zones or [])
        self.network = network
        self.image = image
        self.session_scope = validate_session(session, self.mode)
        self.idle_minutes = idle_minutes
        self.docker_root = docker_root
        self._session: Any = None
        self._backend: Backend | None = None
        self._resolved = False
        self._warned = False

    def backend(self) -> Backend | None:
        if not self._resolved:
            self._backend = backend_for(self.mode)
            self._resolved = True
        return self._backend

    def choose(self, unattended: bool) -> tuple[Backend | None, str | None]:
        """(backend to use or None, refusal message if the command must not run)."""
        if self.mode == "off" or (self.mode == "auto" and not unattended):
            return (None, None)
        backend = self.backend()
        if backend is not None:
            return (backend, None)
        if self.mode == "auto":
            if not self._warned:
                logger.warning(
                    "No OS sandbox on this machine: unattended shell commands are checked by "
                    f"the guardrails only. {INSTALL_HINT}"
                )
                self._warned = True
            return (None, None)
        what = "Docker isn't running" if self.mode == "docker" else "no OS sandbox was found"
        return (
            None,
            f"Refused: sandbox={self.mode!r} is set but {what}, so commands can't run safely. "
            + ("Start Docker." if self.mode == "docker" else INSTALL_HINT),
        )

    def spec(self, cwd: Path) -> SandboxSpec:
        return SandboxSpec(writable=self.zones, cwd=cwd, network=self.network, image=self.image)

    def session(self, backend: Backend, cwd: Path, env: dict[str, str]) -> Any:
        """The long-lived shell session (created on first use), or None without one."""
        if self.session_scope is None:
            return None
        if self._session is None:
            from teotl.core.tools.sandbox_session import open_session

            self._session = open_session(
                self.session_scope,
                backend,
                self.spec(cwd),
                env,
                idle_minutes=self.idle_minutes,
                docker_root=self.docker_root,
            )
        return self._session

    async def close(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            await session.close()

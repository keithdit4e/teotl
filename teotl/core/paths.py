"""Where Teotl keeps its data (memory, missions, tasks, credentials, agent workspaces).

The data directory is `~/.teotl`, or `$TEOTL_HOME` if set. Teotl was previously
called Forge and used `~/.forge`; if that directory exists and `~/.teotl` does
not, it keeps being used so existing memory, missions, and credentials still
work. Move it with `mv ~/.forge ~/.teotl` to switch to the new location.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

LEGACY_DIRNAME = ".forge"
DIRNAME = ".teotl"

_warned_legacy = False


def teotl_home() -> Path:
    """Return the Teotl data directory (not created)."""
    global _warned_legacy

    override = os.environ.get("TEOTL_HOME")
    if override:
        return Path(override).expanduser()

    home = Path.home()
    current, legacy = home / DIRNAME, home / LEGACY_DIRNAME
    if not current.exists() and legacy.exists():
        if not _warned_legacy:
            logger.info(
                f"Using legacy data directory {legacy}. "
                f"Run `mv {legacy} {current}` to move to the new location."
            )
            _warned_legacy = True
        return legacy
    return current


def teotl_home_display() -> str:
    """The data directory for messages and config defaults, using `~` when possible."""
    path = teotl_home()
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def getenv(name: str, default: str | None = None) -> str | None:
    """Read `TEOTL_<name>`, falling back to the legacy `FORGE_<name>`."""
    value = os.environ.get(f"TEOTL_{name}")
    if value is None:
        value = os.environ.get(f"FORGE_{name}")
    return default if value is None else value

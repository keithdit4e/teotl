"""
Forge Cloud: paid services that enhance but never gate the core experience.

Free tier: everything works locally.
Paid: sync, analytics, teams, compliance.

This package contains client stubs. The free tier implementations are no-ops.
"""


class ForgeCloud:
    """Cloud service client. No-op in free tier."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self.enabled = api_key is not None

    @property
    def is_connected(self) -> bool:
        return self.enabled

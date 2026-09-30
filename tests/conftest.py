"""Shared test fixtures and configuration."""

import pytest


@pytest.fixture(autouse=True)
def _isolated_teotl_home(tmp_path_factory, monkeypatch):
    """Keep tests out of the real ~/.teotl (or legacy ~/.forge) data directory."""
    monkeypatch.setenv("TEOTL_HOME", str(tmp_path_factory.mktemp("teotl_home")))

"""Tests for mission interruption and multi-agent features."""

import tempfile
from pathlib import Path

import pytest

from teotl.primitives.missions import Mission, MissionStore
from teotl.primitives.tasks import Priority


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_missions.db"


@pytest.fixture
async def store(temp_db):
    """Create a mission store for testing."""
    store = MissionStore(temp_db)
    yield store
    store.close()


@pytest.mark.asyncio
async def test_mission_interruption_defaults(store):
    """Test default interruption settings."""
    mission = Mission(description="Test mission")

    # Defaults
    assert mission.can_be_interrupted is True
    assert mission.interrupt_threshold == Priority.URGENT

    await store.create(mission)
    retrieved = await store.get(mission.id)

    assert retrieved.can_be_interrupted is True
    assert retrieved.interrupt_threshold == Priority.URGENT


@pytest.mark.asyncio
async def test_mission_cannot_be_interrupted(store):
    """Test mission that cannot be interrupted."""
    mission = Mission(
        description="Critical mission",
        can_be_interrupted=False,
        interrupt_threshold=Priority.CRITICAL,
    )

    await store.create(mission)
    retrieved = await store.get(mission.id)

    assert retrieved.can_be_interrupted is False
    assert retrieved.interrupt_threshold == Priority.CRITICAL


@pytest.mark.asyncio
async def test_mission_various_interrupt_thresholds(store):
    """Test different interrupt threshold levels."""
    thresholds = [
        Priority.CRITICAL,
        Priority.URGENT,
        Priority.HIGH,
        Priority.NORMAL,
        Priority.LOW,
    ]

    for threshold in thresholds:
        mission = Mission(
            description=f"Mission with {threshold.name} threshold", interrupt_threshold=threshold
        )

        await store.create(mission)
        retrieved = await store.get(mission.id)

        assert retrieved.interrupt_threshold == threshold


@pytest.mark.asyncio
async def test_multi_agent_originator(store):
    """Test mission originator tracking."""
    mission = Mission(
        description="User task",
        originator_agent_id="personal-assistant",
        current_agent_id="personal-assistant",
    )

    await store.create(mission)
    retrieved = await store.get(mission.id)

    assert retrieved.originator_agent_id == "personal-assistant"
    assert retrieved.current_agent_id == "personal-assistant"


@pytest.mark.asyncio
async def test_multi_agent_delegation(store):
    """Test mission delegation tracking."""
    # Parent mission created by PA
    parent = Mission(
        description="Parent mission",
        originator_agent_id="personal-assistant",
        current_agent_id="personal-assistant",
    )
    await store.create(parent)

    # Delegated to email agent
    delegated = Mission(
        description="Send email",
        originator_agent_id="personal-assistant",  # PA is still originator
        current_agent_id="email-agent",  # Email agent executes
        parent_mission_id=parent.id,
        delegation_chain=["personal-assistant", "email-agent"],
    )
    await store.create(delegated)

    retrieved = await store.get(delegated.id)

    assert retrieved.originator_agent_id == "personal-assistant"
    assert retrieved.current_agent_id == "email-agent"
    assert retrieved.parent_mission_id == parent.id
    assert retrieved.delegation_chain == ["personal-assistant", "email-agent"]


@pytest.mark.asyncio
async def test_multi_level_delegation_chain(store):
    """Test multi-level delegation chain."""
    mission = Mission(
        description="Deep delegation",
        originator_agent_id="personal-assistant",
        current_agent_id="specialized-agent",
        delegation_chain=["personal-assistant", "coordinator", "email-agent", "specialized-agent"],
    )

    await store.create(mission)
    retrieved = await store.get(mission.id)

    assert len(retrieved.delegation_chain) == 4
    assert retrieved.delegation_chain[0] == "personal-assistant"
    assert retrieved.delegation_chain[-1] == "specialized-agent"


@pytest.mark.asyncio
async def test_update_interruption_settings(store):
    """Test updating interruption settings."""
    mission = Mission(description="Test mission")
    await store.create(mission)

    # Update interruption settings
    mission.can_be_interrupted = False
    mission.interrupt_threshold = Priority.CRITICAL
    await store.update(mission)

    retrieved = await store.get(mission.id)
    assert retrieved.can_be_interrupted is False
    assert retrieved.interrupt_threshold == Priority.CRITICAL


@pytest.mark.asyncio
async def test_update_agent_delegation(store):
    """Test updating agent delegation."""
    mission = Mission(
        description="Test mission", originator_agent_id="agent-1", current_agent_id="agent-1"
    )
    await store.create(mission)

    # Delegate to agent-2
    mission.current_agent_id = "agent-2"
    mission.delegation_chain = ["agent-1", "agent-2"]
    await store.update(mission)

    retrieved = await store.get(mission.id)
    assert retrieved.originator_agent_id == "agent-1"  # Unchanged
    assert retrieved.current_agent_id == "agent-2"
    assert retrieved.delegation_chain == ["agent-1", "agent-2"]


@pytest.mark.asyncio
async def test_interruption_logic_checks(store):
    """Test interruption decision logic."""
    # Mission that only allows CRITICAL to interrupt
    critical_only = Mission(
        description="Critical only", can_be_interrupted=True, interrupt_threshold=Priority.CRITICAL
    )

    # CRITICAL task should interrupt
    assert critical_only.interrupt_threshold <= Priority.CRITICAL

    # URGENT task should NOT interrupt
    assert critical_only.interrupt_threshold > Priority.URGENT

    # Mission that allows URGENT and above
    urgent_allowed = Mission(description="Urgent allowed", interrupt_threshold=Priority.URGENT)

    assert urgent_allowed.interrupt_threshold <= Priority.CRITICAL
    assert urgent_allowed.interrupt_threshold <= Priority.URGENT
    assert urgent_allowed.interrupt_threshold > Priority.HIGH


@pytest.mark.asyncio
async def test_cannot_interrupt_flag_overrides(store):
    """Test that can_be_interrupted=False prevents all interruption."""
    mission = Mission(
        description="Never interrupt",
        can_be_interrupted=False,
        interrupt_threshold=Priority.LOW,  # Even low threshold doesn't matter
    )

    # Regardless of task priority, if can_be_interrupted is False, don't interrupt
    assert mission.can_be_interrupted is False

    # This would be the daemon's logic:
    # if not mission.can_be_interrupted:
    #     # Never interrupt, regardless of task priority
    #     continue_mission()

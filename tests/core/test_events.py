"""Tests for the event bus."""

import pytest

from teotl.core.events import EventBus
from teotl.core.types import EventResult


@pytest.fixture
def bus():
    return EventBus()


async def test_emit_no_handlers(bus):
    result = await bus.emit("test", {"foo": "bar"})
    assert not result.blocked
    assert result.data == {"foo": "bar"}


async def test_handler_receives_data(bus):
    received = []

    async def handler(event, **kwargs):
        received.append(event.data)
        return event

    bus.on("test", handler)
    await bus.emit("test", "hello")
    assert received == ["hello"]


async def test_handler_can_block(bus):
    async def blocker(event, **kwargs):
        return EventResult(data=event.data, blocked=True, reason="nope")

    async def should_not_run(event, **kwargs):
        raise AssertionError("Should not have been called")

    bus.on("test", blocker, priority=0)
    bus.on("test", should_not_run, priority=1)

    result = await bus.emit("test", "data")
    assert result.blocked
    assert result.reason == "nope"


async def test_priority_ordering(bus):
    order = []

    async def first(event, **kwargs):
        order.append("first")
        return event

    async def second(event, **kwargs):
        order.append("second")
        return event

    bus.on("test", second, priority=10)
    bus.on("test", first, priority=1)

    await bus.emit("test", None)
    assert order == ["first", "second"]


async def test_handler_can_modify_data(bus):
    async def modifier(event, **kwargs):
        event.data = event.data + " modified"
        event.modified = True
        return event

    bus.on("test", modifier)
    result = await bus.emit("test", "original")
    assert result.data == "original modified"
    assert result.modified


async def test_off_removes_handler(bus):
    call_count = 0

    async def handler(event, **kwargs):
        nonlocal call_count
        call_count += 1
        return event

    bus.on("test", handler)
    await bus.emit("test", None)
    assert call_count == 1

    bus.off("test", handler)
    await bus.emit("test", None)
    assert call_count == 1


async def test_broken_handler_doesnt_crash(bus):
    async def broken(event, **kwargs):
        raise ValueError("boom")

    async def after(event, **kwargs):
        event.data = "survived"
        return event

    bus.on("test", broken, priority=0)
    bus.on("test", after, priority=1)

    result = await bus.emit("test", "data")
    assert result.data == "survived"


async def test_has_handlers(bus):
    assert not bus.has_handlers("test")

    async def handler(event, **kwargs):
        return event

    bus.on("test", handler)
    assert bus.has_handlers("test")

    bus.clear("test")
    assert not bus.has_handlers("test")

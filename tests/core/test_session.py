"""Tests for session management."""

import pytest

from teotl.core.session import Session
from teotl.core.types import Role


@pytest.fixture
def session():
    return Session()


@pytest.fixture
def persistent_session(tmp_path):
    return Session(path=tmp_path / "test_session.jsonl")


def test_empty_session(session):
    assert session.message_count == 0
    assert session.get_messages() == []


def test_add_user_message(session):
    msg = session.add_user("Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"
    assert session.message_count == 1


def test_add_assistant_message(session):
    msg = session.add_assistant("Hi there!")
    assert msg.role == Role.ASSISTANT
    assert msg.content == "Hi there!"


def test_message_ordering(session):
    session.add_user("First")
    session.add_assistant("Second")
    session.add_user("Third")

    messages = session.get_messages()
    assert len(messages) == 3
    assert messages[0].content == "First"
    assert messages[1].content == "Second"
    assert messages[2].content == "Third"


def test_parent_id_chain(session):
    m1 = session.add_user("First")
    m2 = session.add_assistant("Second")
    m3 = session.add_user("Third")

    assert m1.parent_id is None
    assert m2.parent_id == m1.id
    assert m3.parent_id == m2.id


def test_token_budget(session):
    # Add messages with known approximate sizes
    for i in range(20):
        session.add_user(f"Message {i} " * 50)  # ~200 chars each

    # With a small budget, should get fewer messages
    limited = session.get_messages(token_budget=100)
    all_msgs = session.get_messages()
    assert len(limited) < len(all_msgs)


def test_context_messages_exclude_system(session):
    session.add_system("System prompt")
    session.add_user("Hello")
    session.add_assistant("Hi")

    context = session.get_context_messages()
    assert len(context) == 2
    assert context[0]["role"] == "user"
    assert context[1]["role"] == "assistant"


def test_system_prompt_combination(session):
    session.add_system("Part 1")
    session.add_system("Part 2")

    prompt = session.get_system_prompt()
    assert "Part 1" in prompt
    assert "Part 2" in prompt


def test_persistence(persistent_session):
    persistent_session.add_user("Hello")
    persistent_session.add_assistant("Hi")

    # Load from disk
    loaded = Session(path=persistent_session.path)
    assert loaded.message_count == 2
    assert loaded.get_messages()[0].content == "Hello"
    assert loaded.get_messages()[1].content == "Hi"


def test_format_for_extraction(session):
    session.add_system("You are helpful")
    session.add_user("What is Python?")
    session.add_assistant("Python is a programming language.")

    formatted = session.format_for_extraction()
    assert "User: What is Python?" in formatted
    assert "Assistant: Python is a programming language." in formatted
    assert "You are helpful" not in formatted  # System messages excluded


def test_file_permissions(persistent_session):
    """Test that session files are created with restrictive permissions (0600)."""
    import os
    import stat

    # Add a message to create the file
    persistent_session.add_user("Test message")

    # Check that file exists
    assert persistent_session.path.exists()

    # Check file permissions
    file_stat = os.stat(persistent_session.path)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Should be 0o600 (owner read/write only)
    assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

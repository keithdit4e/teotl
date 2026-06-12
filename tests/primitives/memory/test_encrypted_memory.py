"""Tests for encrypted memory storage."""

import sqlite3

import pytest
from cryptography.fernet import Fernet

from teotl.core.types import MemoryMeta
from teotl.primitives.memory.encrypted import EncryptedMemory


class TestEncryptedMemory:
    """Test encrypted memory storage and retrieval."""

    @pytest.mark.asyncio
    async def test_remember_encrypts_content(self, tmp_path):
        """Test that content is encrypted in database."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Store a memory
        memory_id = await memory.remember("My API key is secret123", MemoryMeta(tags=["test"]))

        # Check database directly
        db = sqlite3.connect(str(db_path))
        row = db.execute(
            "SELECT content, encrypted_content FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        sanitized_content = row[0]
        encrypted_content = row[1]

        # Content should be sanitized (no actual secret)
        assert "secret123" not in sanitized_content
        assert "[API_KEY]" in sanitized_content

        # Encrypted content should not be readable
        assert "secret123" not in encrypted_content
        assert encrypted_content != "My API key is secret123"

        db.close()
        memory.close()

    @pytest.mark.asyncio
    async def test_recall_decrypts_content(self, tmp_path):
        """Test that recall returns decrypted content."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Store a memory with some non-PII searchable content
        original_content = "Remember to update the database password for production"
        await memory.remember(original_content, MemoryMeta(tags=["test"]))

        # Recall using a non-PII term that remains in sanitized content
        results = await memory.recall("database", limit=10)

        assert len(results) > 0
        # Should get back the original decrypted content
        assert results[0].content == original_content

        memory.close()

    @pytest.mark.asyncio
    async def test_search_works_on_sanitized_content(self, tmp_path):
        """Test that FTS search works on sanitized content."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Store memories with sensitive data
        await memory.remember(
            "Remember to update the API key in production", MemoryMeta(tags=["todo"])
        )
        await memory.remember(
            "User email: john@example.com needs verification", MemoryMeta(tags=["user"])
        )

        # Search should work on non-PII terms
        results = await memory.recall("production", limit=10)
        assert len(results) == 1
        assert "API key" in results[0].content

        results = await memory.recall("verification", limit=10)
        assert len(results) == 1
        assert "john@example.com" in results[0].content

        memory.close()

    @pytest.mark.asyncio
    async def test_list_all_decrypts(self, tmp_path):
        """Test that list_all returns decrypted content."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Store multiple memories
        content1 = "Secret message one"
        content2 = "Secret message two"

        await memory.remember(content1)
        await memory.remember(content2)

        # List all
        memories = await memory.list_all()

        assert len(memories) == 2
        contents = [m.content for m in memories]
        assert content1 in contents
        assert content2 in contents

        memory.close()

    def test_pii_sanitization(self, tmp_path):
        """Test that PII patterns are sanitized."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Test various PII patterns
        test_cases = [
            ("Email: user@example.com", "[EMAIL]", "user@example.com"),
            ("API key: abc123xyz", "[API_KEY]", "abc123xyz"),
            ("Token: ghp_1234567890abcdef", "[GITHUB_TOKEN]", "ghp_1234567890abcdef"),
            ("Bearer xyz123abc456", "[BEARER_TOKEN]", "xyz123abc456"),
            ("Card: 4111 1111 1111 1111", "[CREDIT_CARD]", "4111 1111 1111 1111"),
            ("Phone: 555-123-4567", "[PHONE]", "555-123-4567"),
            ("SSN: 123-45-6789", "[SSN]", "123-45-6789"),
            (
                "URL: https://api.com?token=secret",
                "[URL_WITH_PARAMS]",
                "https://api.com?token=secret",
            ),
        ]

        for original, expected_pattern, sensitive_part in test_cases:
            sanitized = memory._sanitize_for_search(original)
            assert expected_pattern in sanitized, f"Expected {expected_pattern} in {sanitized}"
            assert sensitive_part not in sanitized, (
                f"Sensitive part {sensitive_part} should not be in {sanitized}"
            )

        memory.close()

    @pytest.mark.asyncio
    async def test_encryption_key_from_credential_store(self, tmp_path, monkeypatch):
        """Test that encryption key is retrieved from credential store."""
        db_path = tmp_path / "test.db"
        cred_path = tmp_path / "creds"

        # Set up credential store to use file backend with our tmp_path
        monkeypatch.delenv("FORGE_ALLOW_ENV_AUTH", raising=False)
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

        # Patch the FileBackend initialization to use our tmp_path
        from unittest.mock import patch

        from teotl.primitives.integrations.credential_store import FileBackend

        original_init = FileBackend.__init__

        def patched_init(self, storage_path=None):
            original_init(self, storage_path=cred_path)

        with patch.object(FileBackend, "__init__", patched_init):
            memory = EncryptedMemory(path=db_path)

            # Store and retrieve
            content = "Test content"
            await memory.remember(content)

            results = await memory.recall("Test", limit=10)
            assert len(results) == 1
            assert results[0].content == content

            memory.close()

    @pytest.mark.asyncio
    async def test_migration_from_plaintext(self, tmp_path):
        """Test migration of existing plaintext memories."""
        db_path = tmp_path / "test.db"

        # Create plaintext memories using LocalMemory
        from teotl.primitives.memory.local import LocalMemory

        plain_memory = LocalMemory(path=db_path)
        await plain_memory.remember("Plaintext secret one")
        await plain_memory.remember("Plaintext secret two")
        plain_memory.close()

        # Now open with EncryptedMemory and migrate
        key = Fernet.generate_key()
        encrypted_memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Check dry run first
        stats = encrypted_memory.migrate_from_plaintext(dry_run=True)
        assert stats["total"] == 2
        assert stats["dry_run"] is True

        # Actual migration
        stats = encrypted_memory.migrate_from_plaintext(dry_run=False)
        assert stats["total"] == 2
        assert stats["migrated"] == 2
        assert stats["failed"] == 0

        # Verify encrypted content is stored
        db = sqlite3.connect(str(db_path))
        rows = db.execute("SELECT encrypted_content FROM memories").fetchall()

        assert len(rows) == 2
        for row in rows:
            assert row[0] is not None
            assert "Plaintext" not in row[0]  # Encrypted

        db.close()

        # Verify we can still recall
        results = await encrypted_memory.list_all()
        assert len(results) == 2
        assert "Plaintext secret one" in [m.content for m in results]

        encrypted_memory.close()

    @pytest.mark.asyncio
    async def test_decryption_failure_handling(self, tmp_path):
        """Test that decryption failures are handled gracefully."""
        db_path = tmp_path / "test.db"
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        # Store with one key
        memory1 = EncryptedMemory(path=db_path, encryption_key=key1)
        await memory1.remember("Important information about the project")
        memory1.close()

        # Try to read with different key
        memory2 = EncryptedMemory(path=db_path, encryption_key=key2)
        results = await memory2.recall("project", limit=10)

        # Should return result but with decryption error
        assert len(results) > 0
        assert results[0].content == "[DECRYPTION_ERROR]"

        memory2.close()

    @pytest.mark.asyncio
    async def test_metadata_remains_searchable(self, tmp_path):
        """Test that metadata (tags, importance) remain searchable."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Store with tags
        await memory.remember(
            "Secret project details", MemoryMeta(tags=["project", "important"], importance=9)
        )
        await memory.remember("Regular note", MemoryMeta(tags=["note"], importance=5))

        # Can still search by content
        results = await memory.recall("project", limit=10)
        assert len(results) == 1
        assert results[0].metadata.importance == 9

        memory.close()

    @pytest.mark.asyncio
    async def test_forget_removes_encrypted_content(self, tmp_path):
        """Test that forget() removes encrypted content."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        memory = EncryptedMemory(path=db_path, encryption_key=key)

        # Store and then forget
        memory_id = await memory.remember("Secret to delete")
        deleted = await memory.teotlt(memory_id)

        assert deleted is True

        # Verify it's gone from database
        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()

        assert row is None

        db.close()
        memory.close()

    def test_backward_compatibility_with_local_memory(self, tmp_path):
        """Test that EncryptedMemory can read from LocalMemory databases."""
        db_path = tmp_path / "test.db"

        # Create with LocalMemory
        import asyncio

        from teotl.primitives.memory.local import LocalMemory

        plain = LocalMemory(path=db_path)
        asyncio.run(plain.remember("Legacy content"))
        plain.close()

        # Read with EncryptedMemory
        key = Fernet.generate_key()
        encrypted = EncryptedMemory(path=db_path, encryption_key=key)

        memories = asyncio.run(encrypted.list_all())
        assert len(memories) == 1

        # Content should be available (not encrypted, but readable)
        assert "Legacy content" in memories[0].content

        encrypted.close()


class TestEncryptedMemoryKeyManagement:
    """Test encryption key management."""

    def test_key_stored_in_credential_store(self, tmp_path, monkeypatch):
        """Test that encryption key is persisted in credential store."""
        db_path = tmp_path / "test.db"
        cred_path = tmp_path / "creds"

        monkeypatch.delenv("FORGE_ALLOW_ENV_AUTH", raising=False)

        # Create memory (generates key)
        from unittest.mock import patch

        from teotl.primitives.integrations.credential_store import CredentialStore, FileBackend

        # Create real backend and store at test path
        backend = FileBackend(storage_path=cred_path)
        mock_store = CredentialStore(backend)

        # Patch CredentialStore.create at the definition site (where it's defined)
        # This will affect the import inside _get_or_create_key()
        with patch(
            "teotl.primitives.integrations.credential_store.CredentialStore.create",
            return_value=mock_store,
        ):
            memory1 = EncryptedMemory(path=db_path)
            memory1.close()

            # Create another instance (should reuse key)
            memory2 = EncryptedMemory(path=db_path)
            memory2.close()

            # Both should have accessed the same key
            # Verify key exists in credential store
            key_data = mock_store.load_credential("_teotl_memory_encryption")
            assert "key" in key_data
            assert key_data["purpose"] == "memory content encryption"

    def test_explicit_key_bypasses_credential_store(self, tmp_path):
        """Test that providing explicit key doesn't use credential store."""
        db_path = tmp_path / "test.db"
        key = Fernet.generate_key()

        # Should not try to access credential store
        memory = EncryptedMemory(path=db_path, encryption_key=key)

        import asyncio

        asyncio.run(memory.remember("Test"))

        memory.close()
        # If we got here without errors, explicit key worked


class TestSanitizationPatterns:
    """Test various PII sanitization patterns."""

    def test_email_sanitization(self, tmp_path):
        """Test email address sanitization."""
        key = Fernet.generate_key()
        memory = EncryptedMemory(path=tmp_path / "test.db", encryption_key=key)

        tests = [
            "user@example.com",
            "first.last@company.co.uk",
            "test+tag@gmail.com",
        ]

        for email in tests:
            sanitized = memory._sanitize_for_search(f"Contact: {email}")
            assert email not in sanitized
            assert "[EMAIL]" in sanitized

        memory.close()

    def test_api_key_sanitization(self, tmp_path):
        """Test API key pattern sanitization."""
        key = Fernet.generate_key()
        memory = EncryptedMemory(path=tmp_path / "test.db", encryption_key=key)

        tests = [
            "api_key: abc123",
            "API-KEY=xyz789",
            "token: secret123",
            "password: p@ssw0rd",
        ]

        for pattern in tests:
            sanitized = memory._sanitize_for_search(pattern)
            assert "[API_KEY]" in sanitized

        memory.close()

    def test_github_token_sanitization(self, tmp_path):
        """Test GitHub token sanitization."""
        key = Fernet.generate_key()
        memory = EncryptedMemory(path=tmp_path / "test.db", encryption_key=key)

        tokens = [
            ("Found ghp_1234567890abcdefghij in repo", "ghp_1234567890abcdefghij"),
            ("Using gho_abcdefghijklmnopqrst for auth", "gho_abcdefghijklmnopqrst"),
            ("Token ghu_zyxwvutsrqponmlkjih is valid", "ghu_zyxwvutsrqponmlkjih"),
        ]

        for text, token in tokens:
            sanitized = memory._sanitize_for_search(text)
            assert token not in sanitized, f"Token {token} should not be in {sanitized}"
            assert "[GITHUB_TOKEN]" in sanitized, f"Expected [GITHUB_TOKEN] in {sanitized}"

        memory.close()

    def test_credit_card_sanitization(self, tmp_path):
        """Test credit card number sanitization."""
        key = Fernet.generate_key()
        memory = EncryptedMemory(path=tmp_path / "test.db", encryption_key=key)

        cards = [
            "4111 1111 1111 1111",
            "4111-1111-1111-1111",
            "4111111111111111",
        ]

        for card in cards:
            sanitized = memory._sanitize_for_search(f"Card: {card}")
            assert "[CREDIT_CARD]" in sanitized

        memory.close()

"""Encrypted memory storage with searchable metadata.

Provides transparent encryption of memory content while maintaining
full-text search capability on sanitized content.

Strategy:
- Content field: Encrypted at rest (Fernet)
- Search index: Sanitized content (PII removed) for FTS
- Metadata: Plain (tags, importance, etc.) for filtering
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from teotl.core.types import Memory, MemoryMeta
from teotl.primitives.memory.local import LocalMemory

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class EncryptedMemory(LocalMemory):
    """
    Memory storage with content encryption.

    Features:
    - Transparent encryption/decryption of memory content
    - Full-text search on sanitized content (PII patterns removed)
    - Uses credential store for encryption key management
    - Backward compatible with LocalMemory API
    """

    def __init__(
        self,
        path: Path | str | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        """
        Initialize encrypted memory store.

        Args:
            path: Database file path (default: ~/.forge/memory.db)
            encryption_key: Optional explicit key (for testing/custom backends)
                          If None, retrieves from credential store
        """
        super().__init__(path)

        # Import here to avoid circular dependency
        from cryptography.fernet import Fernet

        self._fernet = Fernet

        # Get or create encryption key
        if encryption_key:
            self.cipher = Fernet(encryption_key)
        else:
            key = self._get_or_create_key()
            self.cipher = Fernet(key)

        # Modify schema to add encrypted_content column
        self._ensure_encrypted_schema()

        logger.info("EncryptedMemory initialized with content encryption")

    def _get_or_create_key(self) -> bytes:
        """
        Get encryption key from credential store or create new one.

        Uses the same backend as credential storage for consistency.
        """
        from teotl.primitives.integrations.credential_store import CredentialStore

        try:
            store = CredentialStore.create()

            # Try to load existing key
            try:
                key_data = store.load_credential("_forge_memory_encryption")
                return key_data["key"].encode()
            except ValueError:
                # Key doesn't exist, create new one
                key = self._fernet.generate_key()
                store.save_credential(
                    "_forge_memory_encryption",
                    {
                        "auth_type": "encryption_key",
                        "key": key.decode(),
                        "purpose": "memory content encryption",
                    },
                )
                logger.info("Generated new memory encryption key")
                return key

        except Exception as e:
            logger.error(f"Failed to retrieve encryption key: {e}")
            raise RuntimeError(
                "Could not initialize memory encryption. "
                "Ensure credential store is properly configured."
            ) from e

    def _ensure_encrypted_schema(self) -> None:
        """Add encrypted_content column if it doesn't exist."""
        # Check if column exists
        cursor = self.db.execute("PRAGMA table_info(memories)")
        columns = [row[1] for row in cursor.fetchall()]

        if "encrypted_content" not in columns:
            # Add encrypted_content column
            self.db.execute("ALTER TABLE memories ADD COLUMN encrypted_content TEXT")
            self.db.commit()
            logger.info("Added encrypted_content column to memories table")

    def _sanitize_for_search(self, content: str) -> str:
        """
        Remove PII patterns from content for search indexing.

        Removes:
        - Email addresses
        - API keys/tokens (common patterns)
        - URLs with sensitive data
        - Credit card numbers
        - Phone numbers
        - SSN patterns

        Returns sanitized content safe for FTS indexing.

        Note: Order matters! More specific patterns first.
        """
        sanitized = content

        # Email addresses
        sanitized = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL]",
            sanitized,
        )

        # GitHub tokens (before generic API key pattern)
        sanitized = re.sub(
            r"\bgh[prou]_\w+",
            "[GITHUB_TOKEN]",
            sanitized,
        )

        # Bearer tokens (before generic pattern)
        sanitized = re.sub(
            r"\bBearer\s+[\w\-\.]+",
            "[BEARER_TOKEN]",
            sanitized,
        )

        # Generic hex tokens (32+ chars) - before API key pattern
        sanitized = re.sub(
            r"\b[a-fA-F0-9]{32,}\b",
            "[TOKEN]",
            sanitized,
        )

        # API keys and tokens (common patterns)
        # Match patterns like:
        # - "API key is secret123" / "password is abc"
        # - "api_key: value" / "password = value" / "token: value"
        # Note: "is" pattern must come first in alternation
        sanitized = re.sub(
            r"\b(?:api[_-]?\s*key|token|secret|password)(?:\s+is\s+|[:\s=]+)['\"]?[\w\-\.@#$%^&*()!]+['\"]?",
            "[API_KEY]",
            sanitized,
            flags=re.IGNORECASE,
        )

        # Credit card numbers
        sanitized = re.sub(
            r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
            "[CREDIT_CARD]",
            sanitized,
        )

        # Phone numbers (US format)
        sanitized = re.sub(
            r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "[PHONE]",
            sanitized,
        )

        # SSN patterns
        sanitized = re.sub(
            r"\b\d{3}-\d{2}-\d{4}\b",
            "[SSN]",
            sanitized,
        )

        # URLs with query parameters (may contain sensitive data)
        sanitized = re.sub(
            r"https?://[^\s]+\?[^\s]+",
            "[URL_WITH_PARAMS]",
            sanitized,
        )

        return sanitized

    async def remember(self, content: str, metadata: MemoryMeta | None = None) -> str:
        """
        Store a memory with encrypted content.

        Content is encrypted before storage. A sanitized version (PII removed)
        is stored for full-text search.
        """
        # Encrypt the content
        encrypted_content = self.cipher.encrypt(content.encode()).decode()

        # Sanitize for search
        sanitized_content = self._sanitize_for_search(content)

        # Store both encrypted (in new column) and sanitized (in content for FTS)
        meta = metadata or MemoryMeta()

        from datetime import datetime

        import ulid

        memory_id = ulid.new().str

        self.db.execute(
            """INSERT INTO memories
               (id, content, encrypted_content, source, tags, importance, session_id, created)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory_id,
                sanitized_content,  # For FTS search
                encrypted_content,  # Encrypted original
                meta.source,
                self._serialize_tags(meta.tags),
                meta.importance,
                meta.session_id,
                datetime.now().isoformat(),
            ),
        )
        self.db.commit()

        logger.debug(f"Stored encrypted memory {memory_id}")
        return memory_id

    async def recall(self, query: str, *, limit: int = 10) -> list[Memory]:
        """
        Retrieve memories with automatic decryption.

        Searches using sanitized content (FTS), returns decrypted content.
        """
        # Use parent's search logic (searches sanitized content)
        memories = await super().recall(query, limit=limit)

        # Decrypt content for each memory
        for memory in memories:
            # Get encrypted content from database
            row = self.db.execute(
                "SELECT encrypted_content FROM memories WHERE id = ?",
                (memory.id,),
            ).fetchone()

            if row and row[0]:
                # Decrypt and replace content
                try:
                    encrypted = row[0].encode()
                    decrypted = self.cipher.decrypt(encrypted).decode()
                    memory.content = decrypted
                except Exception as e:
                    logger.error(f"Failed to decrypt memory {memory.id}: {e}")
                    memory.content = "[DECRYPTION_ERROR]"
            else:
                # No encrypted content (legacy memory or migration in progress)
                # Keep the sanitized content
                pass

        return memories

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[Memory]:
        """List all memories with decrypted content."""
        # Get memories from parent
        memories = await super().list_all(limit=limit, offset=offset)

        # Decrypt each one
        for memory in memories:
            row = self.db.execute(
                "SELECT encrypted_content FROM memories WHERE id = ?",
                (memory.id,),
            ).fetchone()

            if row and row[0]:
                try:
                    encrypted = row[0].encode()
                    decrypted = self.cipher.decrypt(encrypted).decode()
                    memory.content = decrypted
                except Exception as e:
                    logger.error(f"Failed to decrypt memory {memory.id}: {e}")
                    memory.content = "[DECRYPTION_ERROR]"

        return memories

    def _serialize_tags(self, tags: list[str]) -> str:
        """Serialize tags for storage."""
        import json

        return json.dumps(tags)

    def migrate_from_plaintext(self, dry_run: bool = False) -> dict:
        """
        Migrate existing plaintext memories to encrypted format.

        Args:
            dry_run: If True, only report what would be migrated

        Returns:
            Dict with migration statistics
        """
        # Find memories without encrypted_content
        cursor = self.db.execute("SELECT id, content FROM memories WHERE encrypted_content IS NULL")
        rows = cursor.fetchall()

        stats = {
            "total": len(rows),
            "migrated": 0,
            "failed": 0,
            "dry_run": dry_run,
        }

        if dry_run:
            logger.info(f"DRY RUN: Would migrate {stats['total']} memories")
            return stats

        for row in rows:
            memory_id = row[0]
            plaintext_content = row[1]

            try:
                # Encrypt the content
                encrypted = self.cipher.encrypt(plaintext_content.encode()).decode()

                # Sanitize for search
                sanitized = self._sanitize_for_search(plaintext_content)

                # Update the record
                self.db.execute(
                    """UPDATE memories
                       SET encrypted_content = ?, content = ?
                       WHERE id = ?""",
                    (encrypted, sanitized, memory_id),
                )

                stats["migrated"] += 1

            except Exception as e:
                logger.error(f"Failed to migrate memory {memory_id}: {e}")
                stats["failed"] += 1

        self.db.commit()

        logger.info(f"Migration complete: {stats['migrated']} migrated, {stats['failed']} failed")

        return stats

# Security Quick Start Guide

**Fast-track guide for implementing critical security fixes**

---

## Priority 1: Encrypted Credentials (C-1)

### Install Dependencies
```bash
pip install keyring cryptography
```

### Create Secure Credential Store

**File:** `teotl/primitives/integrations/secure_store.py`

```python
"""Secure credential storage using OS keyring + encryption."""

import json
import logging
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Try to import keyring, fall back to file-based
try:
    from keyring import get_password, set_password
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning("keyring not available - using fallback encryption")


class SecureCredentialStore:
    """
    Secure credential storage with encryption.

    Uses OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
    for master key storage, with Fernet encryption for credential data.
    """

    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
        self.key_file = Path.home() / ".teotl" / ".keyfile"

    def _get_or_create_key(self) -> bytes:
        """Get or create master encryption key."""
        if KEYRING_AVAILABLE:
            # Preferred: Use OS keyring
            key = get_password("teotl", "master_key")
            if not key:
                key = Fernet.generate_key().decode()
                set_password("teotl", "master_key", key)
                logger.info("Created new master key in OS keyring")
            return key.encode()
        else:
            # Fallback: File-based key (with strict permissions)
            if self.key_file.exists():
                return self.key_file.read_bytes()
            else:
                key = Fernet.generate_key()
                self.key_file.parent.mkdir(parents=True, exist_ok=True)
                self.key_file.write_bytes(key)
                self.key_file.chmod(0o600)
                logger.warning("Created key file - OS keyring preferred for production")
                return key

    def save_credential(self, service: str, data: dict[str, Any]) -> None:
        """Encrypt and store credential."""
        encrypted = self.cipher.encrypt(json.dumps(data).encode())

        if KEYRING_AVAILABLE:
            set_password("teotl", f"cred_{service}", encrypted.decode())
        else:
            # Fallback: encrypted file
            cred_file = Path.home() / ".teotl" / "auth" / f"{service}.enc"
            cred_file.parent.mkdir(parents=True, exist_ok=True)
            cred_file.write_bytes(encrypted)
            cred_file.chmod(0o600)

        logger.info(f"Saved encrypted credential for {service}")

    def load_credential(self, service: str) -> dict[str, Any]:
        """Load and decrypt credential."""
        if KEYRING_AVAILABLE:
            encrypted_str = get_password("teotl", f"cred_{service}")
            if not encrypted_str:
                raise ValueError(f"No credential found for {service}")
            encrypted = encrypted_str.encode()
        else:
            # Fallback: encrypted file
            cred_file = Path.home() / ".teotl" / "auth" / f"{service}.enc"
            if not cred_file.exists():
                raise ValueError(f"No credential found for {service}")
            encrypted = cred_file.read_bytes()

        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted)

    def delete_credential(self, service: str) -> bool:
        """Delete a credential."""
        if KEYRING_AVAILABLE:
            try:
                # keyring doesn't have a standard delete, try setting to empty
                set_password("teotl", f"cred_{service}", "")
                return True
            except Exception as e:
                logger.error(f"Failed to delete credential: {e}")
                return False
        else:
            cred_file = Path.home() / ".teotl" / "auth" / f"{service}.enc"
            if cred_file.exists():
                cred_file.unlink()
                return True
            return False

    def list_services(self) -> list[str]:
        """List all stored services."""
        if KEYRING_AVAILABLE:
            # This is tricky with keyring - would need to maintain a service index
            # For now, return empty (implement service registry separately)
            return []
        else:
            auth_dir = Path.home() / ".teotl" / "auth"
            if not auth_dir.exists():
                return []
            return [f.stem for f in auth_dir.glob("*.enc")]
```

### Update Integration Registry

**File:** `teotl/primitives/integrations/registry.py`

Replace the file-based storage with:

```python
from teotl.primitives.integrations.secure_store import SecureCredentialStore

class IntegrationRegistry:
    def __init__(self, auth_path: Path | None = None):
        # Use secure store instead of plaintext JSON
        self.store = SecureCredentialStore()
        self.connected: dict[str, AuthCredential] = {}
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load saved credentials from secure store."""
        # Note: With keyring, we need to maintain a service registry
        # For now, attempt to load known services
        known_services = ["github", "slack", "gmail"]  # Add as needed

        for service in known_services:
            try:
                data = self.store.load_credential(service)
                self.connected[service] = AuthCredential(
                    service=service,
                    auth_type=data.get("auth_type", "api_key"),
                    data=data.get("data", {}),
                )
            except (ValueError, Exception):
                pass  # Service not configured

    def _save_credentials(self) -> None:
        """Save credentials to secure store."""
        for service, cred in self.connected.items():
            data = {
                "auth_type": cred.auth_type,
                "data": cred.data,
            }
            self.store.save_credential(service, data)
```

### Migration Script

**File:** `scripts/migrate_credentials.py`

```python
"""Migrate plaintext credentials to encrypted storage."""

import json
from pathlib import Path
from teotl.primitives.integrations.secure_store import SecureCredentialStore

def migrate():
    old_file = Path.home() / ".teotl" / "auth" / "credentials.json"

    if not old_file.exists():
        print("No credentials to migrate")
        return

    # Load old credentials
    with open(old_file) as f:
        old_creds = json.load(f)

    # Save to secure store
    store = SecureCredentialStore()
    for service, data in old_creds.items():
        store.save_credential(service, data)
        print(f"✓ Migrated {service}")

    # Backup and remove old file
    backup = old_file.with_suffix(".json.backup")
    old_file.rename(backup)
    print(f"\n✓ Migration complete")
    print(f"  Old file backed up to: {backup}")
    print(f"  You can delete the backup after verifying everything works")

if __name__ == "__main__":
    migrate()
```

---

## Priority 2: Rate Limiting (C-3)

### Create Rate Limiter

**File:** `teotl/primitives/guardrails/rate_limiter.py`

```python
"""Rate limiting and cost tracking for LLM calls."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class RateLimiter:
    """
    Rate limiter for LLM API calls with cost tracking.

    Tracks:
    - Requests per minute (RPM)
    - Cost per hour
    - Cost per day
    """

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_cost_per_hour: float = 5.0,
        max_cost_per_day: float = 25.0,
    ):
        self.max_rpm = max_requests_per_minute
        self.max_cost_hour = max_cost_per_hour
        self.max_cost_day = max_cost_per_day

        self.requests: List[datetime] = []
        self.costs: List[Tuple[datetime, float]] = []

    def check_and_record(self, estimated_cost: float = 0.0) -> None:
        """
        Check rate limits and record request.

        Raises:
            RateLimitExceeded: If any limit is exceeded
        """
        now = datetime.now()

        # RPM check
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [r for r in self.requests if r > minute_ago]
        if len(recent_requests) >= self.max_rpm:
            raise RateLimitExceeded(
                f"Rate limit exceeded: {self.max_rpm} requests/minute"
            )

        # Hourly cost check
        hour_ago = now - timedelta(hours=1)
        hourly_cost = sum(cost for ts, cost in self.costs if ts > hour_ago)
        if hourly_cost + estimated_cost >= self.max_cost_hour:
            raise RateLimitExceeded(
                f"Hourly cost limit exceeded: ${hourly_cost:.2f} + ${estimated_cost:.2f} >= ${self.max_cost_hour}"
            )

        # Daily cost check
        day_ago = now - timedelta(days=1)
        daily_cost = sum(cost for ts, cost in self.costs if ts > day_ago)
        if daily_cost + estimated_cost >= self.max_cost_day:
            raise RateLimitExceeded(
                f"Daily cost limit exceeded: ${daily_cost:.2f} + ${estimated_cost:.2f} >= ${self.max_cost_day}"
            )

        # Record request
        self.requests.append(now)
        if estimated_cost > 0:
            self.costs.append((now, estimated_cost))

        # Cleanup old entries (keep last 24 hours)
        cutoff = now - timedelta(days=1)
        self.requests = [r for r in self.requests if r > cutoff]
        self.costs = [(ts, c) for ts, c in self.costs if ts > cutoff]

    def get_stats(self) -> Dict[str, float]:
        """Get current usage statistics."""
        now = datetime.now()

        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        return {
            "requests_last_minute": len([r for r in self.requests if r > minute_ago]),
            "cost_last_hour": sum(c for ts, c in self.costs if ts > hour_ago),
            "cost_last_day": sum(c for ts, c in self.costs if ts > day_ago),
        }
```

### Wrap Providers

**File:** `teotl/core/provider.py` (add to end)

```python
class RateLimitedProvider(Provider):
    """Provider wrapper with rate limiting."""

    # Pricing per 1M tokens (update as needed)
    PRICING = {
        "claude-opus-4": {"input": 3.0, "output": 15.0},
        "claude-sonnet-4": {"input": 1.0, "output": 5.0},
        "gpt-4": {"input": 10.0, "output": 30.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }

    def __init__(
        self,
        base_provider: Provider,
        rate_limiter: RateLimiter | None = None,
    ):
        self.provider = base_provider
        self.limiter = rate_limiter or RateLimiter()

    async def complete(self, **kwargs) -> CompletionResult:
        # Estimate cost (rough, based on context size)
        system = kwargs.get("system", "")
        messages = kwargs.get("messages", [])
        estimated_input = len(system) + sum(len(str(m)) for m in messages)
        estimated_cost = self._estimate_cost_from_chars(estimated_input)

        # Check rate limit
        try:
            self.limiter.check_and_record(estimated_cost)
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise

        # Execute
        result = await self.provider.complete(**kwargs)

        # Update with actual cost
        actual_cost = self._calculate_cost(result.usage)
        # Adjust: remove estimate, add actual
        self.limiter.costs[-1] = (self.limiter.costs[-1][0], actual_cost)

        logger.debug(f"LLM call cost: ${actual_cost:.4f}")
        return result

    def _estimate_cost_from_chars(self, chars: int) -> float:
        """Rough cost estimate from character count."""
        tokens = chars // 4
        model = self.provider.model_name
        pricing = self._get_pricing(model)
        # Assume 50/50 input/output split for estimate
        return (tokens * pricing["input"] / 1_000_000) * 1.5

    def _calculate_cost(self, usage: dict) -> float:
        """Calculate actual cost from token usage."""
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        model = self.provider.model_name
        pricing = self._get_pricing(model)

        cost = (
            (input_tokens * pricing["input"] / 1_000_000) +
            (output_tokens * pricing["output"] / 1_000_000)
        )
        return cost

    def _get_pricing(self, model: str) -> dict:
        """Get pricing for model."""
        for key, pricing in self.PRICING.items():
            if key in model:
                return pricing
        # Default to mid-range pricing
        return {"input": 1.0, "output": 5.0}

    @property
    def context_window(self) -> int:
        return self.provider.context_window

    @property
    def model_name(self) -> str:
        return self.provider.model_name
```

### Usage

```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider, RateLimitedProvider
from teotl.primitives.guardrails.rate_limiter import RateLimiter

# Create rate-limited provider
base_provider = AnthropicProvider()
limiter = RateLimiter(
    max_requests_per_minute=60,
    max_cost_per_hour=5.0,
    max_cost_per_day=25.0,
)
provider = RateLimitedProvider(base_provider, limiter)

# Use in agent
agent = Agent(provider=provider, ...)
```

---

## Testing Security Fixes

### Test Encrypted Credentials

```python
# test_secure_store.py
def test_credential_encryption():
    from teotl.primitives.integrations.secure_store import SecureCredentialStore

    store = SecureCredentialStore()

    # Save credential
    store.save_credential("test_service", {
        "auth_type": "api_key",
        "api_key": "secret_key_123",
    })

    # Load credential
    cred = store.load_credential("test_service")
    assert cred["api_key"] == "secret_key_123"

    # Verify not stored as plaintext
    auth_dir = Path.home() / ".teotl" / "auth"
    if auth_dir.exists():
        for file in auth_dir.glob("*.enc"):
            content = file.read_text()
            assert "secret_key_123" not in content
```

### Test Rate Limiting

```python
# test_rate_limiter.py
def test_rate_limiting():
    from teotl.primitives.guardrails.rate_limiter import RateLimiter, RateLimitExceeded

    limiter = RateLimiter(max_requests_per_minute=2)

    # Should allow first 2
    limiter.check_and_record()
    limiter.check_and_record()

    # Should block 3rd
    with pytest.raises(RateLimitExceeded):
        limiter.check_and_record()
```

---

## Deployment Checklist

- [ ] Install security dependencies: `pip install keyring cryptography`
- [ ] Run migration script: `python scripts/migrate_credentials.py`
- [ ] Update agent initialization to use `RateLimitedProvider`
- [ ] Set rate limits in policy files
- [ ] Test credential loading
- [ ] Test rate limiting
- [ ] Update documentation
- [ ] Deploy to staging
- [ ] Run security tests
- [ ] Deploy to production

---

## Environment Variables for CI/CD

For automated environments where keyring isn't available:

```bash
# Allow environment variable auth (NOT recommended for production)
export TEOTL_ALLOW_ENV_AUTH=true
export TEOTL_GITHUB_API_KEY=ghp_...
export TEOTL_ANTHROPIC_API_KEY=sk-ant-...
```

---

## Support

Questions? security@teotl.dev

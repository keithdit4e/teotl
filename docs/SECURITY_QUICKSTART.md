# Security Quick Start Guide

**Fast-track guide to Teotl's credential storage and rate limiting**

Both features ship with Teotl — this guide shows how to use them.

---

## 1. Encrypted Credentials

### Install Dependencies
```bash
pip install "teotl[security]"   # or: pip install keyring cryptography
```

### Store and Load Credentials

`CredentialStore` (in `teotl/primitives/integrations/credential_store.py`) picks the best
available backend automatically, or you can choose one explicitly:

| Backend name | Storage |
|--------------|---------|
| `"keyring"` | OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service) |
| `"file"` | Fernet-encrypted files in `~/.forge/auth/` (fallback when no keyring) |
| `"environment"` | Read-only, from environment variables (CI/CD; requires `FORGE_ALLOW_ENV_AUTH=true`) |
| `"aws_secrets"` | AWS Secrets Manager (requires `teotl[aws]`) |

Auto-detection order: environment (if `FORGE_ALLOW_ENV_AUTH=true`) → AWS Secrets Manager
(if `AWS_REGION`/`AWS_DEFAULT_REGION` is set) → OS keyring → encrypted file.

```python
from teotl.primitives.integrations.credential_store import CredentialStore

# Auto-detect the best backend
store = CredentialStore.create()
print(store.backend_name)

# Or pick one explicitly
store = CredentialStore.create(backend="file")

# The API is synchronous and stores a dict per service
store.save_credential("github", {"auth_type": "token", "token": "ghp_..."})
cred = store.load_credential("github")      # -> {"auth_type": "token", "token": "ghp_..."}
print(store.list_services())                # -> ["github", ...]
store.delete_credential("github")
```

---

## 2. Rate Limiting

`RateLimiter` enforces requests-per-minute, hourly/daily cost budgets, and a per-request
token limit. `RateLimitedProvider` wraps any provider and applies the limiter to every LLM call.

### Usage

```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider
from teotl.core.rate_limited_provider import RateLimitedProvider
from teotl.primitives.guardrails.rate_limiter import RateLimiter

# Create rate-limited provider
base_provider = AnthropicProvider()
limiter = RateLimiter(
    max_requests_per_minute=60,
    max_cost_per_hour=5.0,
    max_cost_per_day=25.0,
    max_tokens_per_request=200000,
)
provider = RateLimitedProvider(base_provider, limiter)

# Use in agent
agent = Agent(provider=provider)

# Later: inspect usage
print(limiter.get_stats())
```

When a limit is hit, the provider raises `RateLimitExceeded`
(from `teotl.primitives.guardrails.rate_limiter`).

### Using the limiter directly

```python
from teotl.primitives.guardrails.rate_limiter import RateLimiter, estimate_cost

limiter = RateLimiter(max_requests_per_minute=60)

allowed, reason = limiter.check_rate_limit()
if not allowed:
    print(f"Blocked: {reason}")
else:
    # ... make the call, then record it
    cost = estimate_cost("anthropic", "claude-sonnet-5-5", input_tokens=1000, output_tokens=500)
    limiter.record_request(cost=cost, tokens=1500)
```

---

## Testing

### Test Encrypted Credentials

```python
# test_credentials.py
from teotl.primitives.integrations.credential_store import CredentialStore, FileBackend


def test_credential_encryption(tmp_path):
    store = CredentialStore(FileBackend(storage_path=tmp_path))

    store.save_credential("test_service", {"auth_type": "api_key", "api_key": "secret_key_123"})

    cred = store.load_credential("test_service")
    assert cred["api_key"] == "secret_key_123"

    # Verify not stored as plaintext
    for file in tmp_path.iterdir():
        if file.is_file():
            assert b"secret_key_123" not in file.read_bytes()
```

### Test Rate Limiting

```python
# test_rate_limits.py
from teotl.primitives.guardrails.rate_limiter import RateLimiter


def test_rate_limiting():
    limiter = RateLimiter(max_requests_per_minute=2)

    # First 2 are allowed
    for _ in range(2):
        allowed, _ = limiter.check_rate_limit()
        assert allowed
        limiter.record_request()

    # 3rd is blocked
    allowed, reason = limiter.check_rate_limit()
    assert not allowed
```

The project's own tests live in `tests/primitives/integrations/test_credential_store.py` and
`tests/primitives/guardrails/test_rate_limiter.py`.

---

## Deployment Checklist

- [ ] Install security dependencies: `pip install "teotl[security]"`
- [ ] Store API credentials with `CredentialStore` (not in plaintext files)
- [ ] Wrap providers with `RateLimitedProvider` and set budgets
- [ ] Test credential loading
- [ ] Test rate limiting
- [ ] Review audit logs: `teotl security logs`

---

## Environment Variables for CI/CD

For automated environments where keyring isn't available, the `environment` backend reads
credentials from environment variables. It is read-only and must be enabled explicitly:

```bash
# Allow environment variable auth (NOT recommended for local development)
export FORGE_ALLOW_ENV_AUTH=true
export FORGE_GITHUB_TOKEN=ghp_...          # -> load_credential("github")
export FORGE_SLACK_API_KEY=xoxb-...        # -> load_credential("slack")
```

Each service is read from `FORGE_<SERVICE>_API_KEY`, `FORGE_<SERVICE>_TOKEN`, or
`FORGE_<SERVICE>_ACCESS_TOKEN`. (LLM provider keys such as `ANTHROPIC_API_KEY` are read
by the providers themselves — see [SECURITY_API_KEYS.md](SECURITY_API_KEYS.md).)

---

## Support

Report security issues privately via GitHub's
[private vulnerability reporting](https://github.com/keithdit4e/teotl/security/advisories/new)
(see [SECURITY.md](../SECURITY.md)).

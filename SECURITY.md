# Security Policy

## Supported versions

Teotl is in alpha. Security fixes are made on the latest release only.

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2   | No        |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report them privately through GitHub's [private vulnerability reporting](https://github.com/keithdit4e/teotl/security/advisories/new). Include:

- what the issue is and what an attacker could do with it
- steps to reproduce, or a proof of concept
- the Teotl version, Python version, and provider you were using

You should get an acknowledgement within a few days. Once a fix is ready, it will be released and credited in the changelog unless you'd prefer to stay anonymous.

## Scope

In scope: guardrail or policy bypasses, prompt-injection paths that lead to unapproved tool execution, credential exposure, and audit-log tampering.

Out of scope: an LLM giving wrong or unsafe *text* without executing anything, and problems in third-party providers or dependencies (report those upstream).

For how the guardrails work, see [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) and [docs/GUARDRAILS.md](docs/GUARDRAILS.md).

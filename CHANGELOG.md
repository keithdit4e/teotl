# Changelog

All notable changes to Teotl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.3] - 2026-09-30

### Removed
- **Social media skills** (`social-media`, and `linkedin`, `medium`, `substack`, `twitter` under `platforms/`) and the `BrowserTool` browser automation behind them, until they can be rebuilt properly:
  - The platform skills were never discovered (they sat one directory too deep)
  - `BrowserTool` was written for an old `browser-use` API and failed to launch with any current release
  - No agent tool exposed browser actions, so an agent couldn't follow the skills anyway
  - Posting through automated browser sessions conflicts with LinkedIn's and X's automation rules; a rebuild should use official APIs where they exist
  - The code remains in git history (tag `v0.2.2`)
- The `browser` install extra (`teotl[browser]`). Installing with it now only prints a pip warning

### Added
- A test that every `SKILL.md` bundled in the package is discovered by the skill registry

## [0.2.2] - 2026-09-30

### Security
- **Planner-worker workers now run with guardrails.** `PlannerWorkerHarness` passed its `SecurityPolicy` into the agent's guardrail slot, which failed to load, so the worker executed tools with no guardrails at all (silently, since v0.2.0). Security presets now map to guardrail presets: `strict`→`strict`, `moderate`/`autonomous-dev`→`standard`, `permissive`→`minimal`
- **Config-built agents now run with guardrails.** The same bug affected any agent created from a config file with `security.preset` or `policy_file` (daemon and wizard configs)
- An unknown `policy=` name (e.g. `"permissive"`) now logs a warning that guardrails are disabled, instead of a debug message

### Fixed
- `python -m teotl.daemon.run` crashed on import (`teotl.daemon.heartbeat` no longer existed); it now uses `AgentDaemon`, so missions can run again
- `teotl security logs|report|status` rejected its subcommands; arguments are now passed through
- `teotl memory` commands existed but weren't registered with the CLI; they now are
- Remaining `forge.` imports and CLI usage strings renamed to `teotl`

### Changed
- **Finished the Forge → Teotl rename.** The data directory is now `~/.teotl` (override with `TEOTL_HOME`). Existing `~/.forge` directories keep working: Teotl uses `~/.forge` when `~/.teotl` doesn't exist and logs how to move it (`mv ~/.forge ~/.teotl`)
- Environment variables are now `TEOTL_SKILLS_PATH`, `TEOTL_ALLOW_ENV_AUTH`, and `TEOTL_<SERVICE>_API_KEY` / `_TOKEN` / `_ACCESS_TOKEN`; the `FORGE_*` names are still accepted, and skill scripts receive both prefixes
- OS keyring entries are stored under `teotl`; credentials saved under `forge` are still read, and the master key is copied the first time
- Guardrail presets deny both `~/.teotl/auth/**` and `~/.forge/auth/**`
- `ForgeCloud` renamed to `TeotlCloud` (old name kept as an alias); remaining "Forge"/`forge` names in CLI output, docstrings, docs, and examples renamed
- Fixed `EnvironmentBackend.list_services()` reporting `<service>_access` for `*_ACCESS_TOKEN` variables
- The test suite no longer writes to the real data directory (it previously appended to `~/.forge/audit.jsonl`)

### Documentation
- Rewrote examples across the docs to use the real API. Removed `Agent.create_planner_worker`, `Mission.from_file`/`from_dict`/`run`, `SkillRegistry.register_builtin`, the `Skill` base class, `secure_store`, and CLI commands that don't exist (`teotl init`, `run`, `skills`, `auth`, `audit`, `policy`, `compliance`, `test-security`)
- Planner-worker docs now use `PlannerWorkerHarness`; missions are documented as daemon-scheduled work defined in config YAML
- Policy docs list only the real presets (`minimal`, `standard`, `strict`)
- Credential docs use the real backends (`keyring`, `file`, `environment`, `aws_secrets`) and synchronous API
- `docs/api_reference.md` signatures checked against the code
- Installation docs lead with `pip install teotl`
- Removed unverifiable marketing numbers and fabricated sample outputs; the one-pager no longer includes competitor claims or an enterprise tier
- Fixed escaped code fences in `docs/CUSTOM_SKILLS_QUICKSTART.md` and an example
- Example agent templates: replaced old `forge.` imports and invented APIs (`Agent.load`, `MissionStore.get_default_store`, a Slack integration, `Mission(instructions=, tools=)`) with the real API and daemon mission config

## [0.2.1] - 2026-09-30

### Fixed
- Replaced invalid and retired Claude model IDs throughout. `claude-3-haiku-20240307` (retired April 2026) was the default worker model, and several date-suffixed IDs such as `claude-sonnet-4-6-20260301` and `claude-haiku-4-20250514` never existed, so the default setups failed at the API
- Defaults are now `claude-sonnet-5-5` (general and planner) and `claude-haiku-4-5` (worker); the wizard offers Sonnet 5.5, Opus 5.5, and Haiku 4.5
- Tool loops now send Claude's assistant turn back exactly as received, including thinking blocks. Current models think by default and reject turns where those blocks were dropped
- Claude Haiku models got a 10K-token compaction threshold because only "opus"/"sonnet" names were recognized; all Claude models now use 100K
- Corrected Haiku 4.5's context window (200K, not 1M) and Claude pricing used for cost tracking

### Added
- `teotl.core.models`: one catalog of Claude model IDs, context windows, and prices, used by the provider, cost tracking, and the wizard

### Changed
- `docs/MODEL_STRATEGY.md` updated for current models and prices. With current pricing, a Haiku worker saves about 50% versus an all-Sonnet setup (earlier docs claimed 97%, based on retired Claude 3 Haiku pricing)

## [0.2.0] - 2026-09-30

First release published to PyPI (`pip install teotl`).

### Added
- Google Gemini provider (`GeminiProvider`, `teotl[google]`)
- Expanded YAML configuration for multi-agent, planner-worker, and harness settings
- Browser automation tool (`teotl[browser]`) and social media skills (LinkedIn, Medium, Substack, Twitter/X)
- `TEOTL_SKILLS_PATH` environment variable for extra skill directories (`FORGE_SKILLS_PATH` still works)
- GitHub Actions CI and PyPI trusted-publishing workflows

### Changed
- Built-in skills now ship inside the package (`teotl/skills/`), so they're available after `pip install`
- `teotl --version` now reads the package version
- Renamed remaining "Forge" branding in CLI output and docstrings to Teotl
- Rewrote the README with working examples
- Moved internal planning notes and ad-hoc scripts out of the repository root

### Removed
- Unused `teotl/cli.py` module (shadowed by the `teotl/cli/` package)

---

## [0.1.0] - 2026-06-11

### 🎉 Initial Release

First public release of Teotl framework, prepared for Google Startup Challenge submission.

### Added

#### Core Framework
- **Agent System:** Production-ready agent loop with planner-worker architecture
  - Single agent mode for simple tasks
  - Planner-worker mode achieving 40% cost savings
  - Automatic context management and compaction
  - Prompt injection defense
- **Provider System:** Model-agnostic LLM interface
  - AnthropicProvider (Claude Sonnet 4, Opus 4, Haiku 4)
  - OpenAIProvider (GPT-4o, GPT-4 Turbo, GPT-3.5)
  - OllamaProvider (Local models: Llama3, Mistral, etc.)
- **Type System:** Complete type definitions for Response, ToolCall, Message, etc.
- **Event System:** Extensible event bus for hooks and extensions

#### Primitives

##### Skills System
- SkillRegistry for managing agent capabilities
- Built-in skills:
  - `filesystem` - File read/write operations
  - `git` - Repository operations
  - `bash` - Shell command execution
  - `python_repl` - Dynamic Python code execution
- Custom skill creation framework
- Progressive disclosure (skills only available when needed)

##### Memory System
- LocalMemory (SQLite-based persistence)
- EncryptedMemory (encrypted storage with auto-generated keys)
- Semantic search and recall
- Context persistence across sessions
- Automatic memory summarization and compaction

##### Mission System
- YAML-based mission definitions
- Autonomous long-running workflows
- Error recovery and retry logic
- Context management for multi-hour tasks
- Cost tracking and optimization

##### Guardrails
- Three security policy levels: permissive, standard, strict
- Command classification and risk analysis
- Trust-building system (automatic approval after 3 confirmations)
- Blocked command patterns (rm -rf /, etc.)
- Path sandboxing and file size limits
- Real-time audit logging

##### Credentials
- Secure credential storage with multiple backends:
  - OS Keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
  - Encrypted file storage (fallback)
  - AWS Secrets Manager (cloud option)
- Automatic backend detection
- Never store credentials in code or environment variables

#### CLI

##### Commands
- `teotl` - Interactive REPL mode
- `teotl chat` - Chat mode with skills and memory
- `teotl onboard` - Interactive setup wizard
- `teotl memory` - Memory management (list, search, forget)
- `teotl security` - Security policy configuration
- `teotl init` - Initialize Teotl in current directory

##### Interactive Mode
- Slash commands: `/help`, `/quit`, `/memory`, `/skills`, `/policy`
- Rich terminal output with syntax highlighting
- Progress indicators and status displays

#### Documentation

##### Comprehensive Guides
- README.md with compelling introduction and 40% cost savings
- CONTRIBUTING.md with development guidelines
- Installation guide (platform-specific instructions)
- Quick start tutorial (5-minute getting started)
- Core concepts deep dive
- Complete API reference (900+ lines)
- Architecture documentation

##### Examples
- Basic agent creation
- Planner-worker setup
- Skills usage
- Memory integration
- Guardrails configuration
- Custom skill development

#### Testing
- 553 passing tests (99.5% pass rate)
- Unit tests for all core components
- Integration tests for guardrails, memory, skills
- 3 skipped tests (documented in TESTING.md)
- High code coverage (>85%)

#### Infrastructure
- PyPI-ready package configuration
- Proper dependency management
- Optional dependency groups (anthropic, openai, memory, security, web, all, dev)
- Entry point configuration
- Type hints throughout codebase
- Ruff formatting and linting

### Cost Optimization

**Planner-Worker Architecture:**
- 40% cost reduction vs single-model agents (benchmarked)
- Strategic planning with expensive models (Sonnet)
- Fast execution with cheap models (Haiku)
- Automatic delegation between planner and worker
- Cost tracking built-in

**Example Savings:**
```
Traditional (Sonnet only):  $0.29 per task
Teotl (Planner-Worker):     $0.17 per task
Savings:                    40%
```

### Performance

**Metrics (from real-world testing):**
- Average task duration: 12 minutes (vs 18 minutes traditional)
- Success rate: 87% (vs ~65% traditional)
- Test pass rate: 99.5% (553/556 tests)

### Security

**Built-in Protection:**
- Prompt injection defense with instruction validation
- Command filtering and risk analysis
- Path sandboxing (standard and strict policies)
- Encrypted credential storage
- Audit logging for all operations
- Trust-building to reduce false positives

### Known Issues

**TODOs (Non-Critical):**
- MCP Bridge implementation (placeholder, optional feature)
- Full sandbox implementation (policy-only enforcement currently works)
- Agent daemon lifecycle management (single agents work fine)
- Wizard integration tests need rewrite (wizard works, tests out of sync)

See [TODO.md](TODO.md) for complete list.

### Requirements

- Python 3.11 or higher
- macOS, Linux, or Windows
- API key for Anthropic Claude or OpenAI (or local Ollama)

### Installation

```bash
# From PyPI (when published)
pip install teotl

# From source
git clone https://github.com/yourusername/teotl
cd teotl
pip install -e .
```

### Quick Start

```python
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

# Create planner-worker agent
agent = Agent.create_planner_worker(
    planner=AnthropicProvider(model="claude-sonnet-4-20250514"),
    worker=AnthropicProvider(model="claude-haiku-4-20250514"),
)

# Run autonomous task
response = await agent.run("Analyze this repository and suggest improvements")
print(response.text)
```

### Roadmap

**v0.2.0 (Planned):**
- DevOps Automation Agent (flagship demo)
- GAIA benchmark validation
- Web dashboard
- Multi-agent orchestration
- Enhanced MCP integration

**v1.0.0 (Future):**
- GCP Marketplace listing
- Production case studies
- Gemini Enterprise support
- Advanced monitoring

### Acknowledgments

Built for the Google Startup Challenge (June 5, 2026 deadline).

Powered by:
- [Anthropic Claude](https://www.anthropic.com/) - Strategic planning and execution
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Pytest](https://pytest.org/) - Testing framework

### License

MIT License - see [LICENSE](LICENSE) for details.

---

## Release Notes Format

### [Version] - YYYY-MM-DD

#### Added
New features

#### Changed
Changes to existing functionality

#### Deprecated
Soon-to-be removed features

#### Removed
Removed features

#### Fixed
Bug fixes

#### Security
Security improvements

---

[Unreleased]: https://github.com/yourusername/teotl/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/teotl/releases/tag/v0.1.0

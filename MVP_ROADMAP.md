# Forge Framework MVP Roadmap

**Project:** Forge - A Python framework for building safe, memory-aware AI agents
**MVP Goal:** Production-ready framework + reference personal assistant implementation
**Timeline:** 6-8 weeks
**Target:** Demonstrate framework capabilities through real-world usage on macOS

---

## Vision Statement

**"A framework for building ANY agent type - from personal assistants to code reviewers to customer support bots - with built-in guardrails, memory, and skills."**

### The Framework Enables

- Developers can build custom agents for specific use cases
- Agents can compose other agents (meta-agents)
- Safety and memory are built-in, not bolt-on
- Skills are reusable across agent types
- Zero-context-cost integrations via progressive disclosure

---

## MVP Scope: Framework + Reference Implementation

### What We're Building

```
┌─────────────────────────────────────────────────────────────┐
│                  FORGE FRAMEWORK (Core)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Core Loop, Events, Session, Provider, Types         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Four Primitives:                                     │  │
│  │  • Guardrails (tool-layer enforcement)               │  │
│  │  • Memory (cross-session persistence)                │  │
│  │  • Skills (progressive disclosure)                   │  │
│  │  • Integrations (auth + CLI scripts)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Extension System (audit, undo, custom hooks)        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Uses Framework
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         REFERENCE IMPLEMENTATION: Personal Assistant         │
│  (Demonstrates framework capabilities in real-world use)     │
│                                                              │
│  • Filesystem operations (skill example)                    │
│  • Email management (integration example)                   │
│  • Task tracking (custom extension example)                 │
│  • Memory across sessions (primitive example)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Framework MVP Features

### Phase 1: Core Framework (Week 1-2)
**Goal:** Solid, secure foundation

#### Core Components (Mostly Done ✅)
- [x] Agent loop
- [x] Event bus
- [x] Session management
- [x] Provider abstraction
- [x] Type system
- [ ] **Security Hardening (CRITICAL)**
  - [ ] C-1: Encrypted credential storage
  - [ ] C-2: Memory encryption
  - [ ] C-3: Rate limiting
  - [ ] H-2: Session file permissions
  - [ ] H-4: Prompt injection defenses

#### Framework Essentials
- [ ] **Agent API Cleanup**
  - [ ] Simplify Agent initialization
  - [ ] Clean provider configuration
  - [ ] Better error messages
- [ ] **Documentation**
  - [ ] Framework architecture guide
  - [ ] API reference
  - [ ] Agent building tutorial

---

### Phase 2: Guardrails System (Week 3)
**Goal:** Production-ready safety layer

#### Already Built ✅
- [x] Policy engine
- [x] Bash analyzer
- [x] Action classifier
- [x] Trust tracker

#### Needs Work
- [ ] **Completion**
  - [ ] Wire guardrails fully into agent loop
  - [ ] Test all risk levels
  - [ ] Verify blocking/confirmation flows
- [ ] **Policy Management**
  - [ ] Policy loading from custom files
  - [ ] Policy validation
  - [ ] Runtime policy updates
- [ ] **Examples**
  - [ ] Example custom policies
  - [ ] Policy testing utilities

---

### Phase 3: Skills System (Week 3-4)
**Goal:** Extensible skill framework

#### Already Built ✅
- [x] Skill loader (SKILL.md parsing)
- [x] Registry (discovery & activation)
- [x] Router (skill routing logic)

#### Needs Work
- [ ] **Core Integration**
  - [ ] Wire skills into agent loop
  - [ ] Skill activation on-demand
  - [ ] Skill deactivation after use
- [ ] **Reference Skills** (Examples for framework users)
  - [ ] Filesystem skill (read, search, list)
  - [ ] Web skill (fetch, search)
  - [ ] Git skill (status, diff, commit)
- [ ] **Skill Development Kit**
  - [ ] Skill template generator
  - [ ] Skill testing utilities
  - [ ] Best practices guide

---

### Phase 4: Memory System (Week 4-5)
**Goal:** Cross-session intelligence

#### Already Built ✅
- [x] LocalMemory (SQLite + embeddings)
- [x] Memory store interface
- [x] Context formatting

#### Needs Work
- [ ] **Agent Integration**
  - [ ] Wire memory into agent loop
  - [ ] Auto-extraction from sessions
  - [ ] Context injection with budget
- [ ] **Security**
  - [ ] Implement memory encryption (C-2)
  - [ ] PII detection
  - [ ] Data retention policies
- [ ] **API**
  - [ ] Memory management commands
  - [ ] Export/import memories
  - [ ] Clear utilities

---

### Phase 5: Integration System (Week 5)
**Goal:** OAuth + external service framework

#### Already Built ✅
- [x] Integration registry (credential storage)
- [x] MCP bridge (meta-tool pattern)

#### Needs Work
- [ ] **Security**
  - [ ] Implement C-1: Encrypted credentials
  - [ ] OAuth2 flow helpers
  - [ ] Token refresh logic
- [ ] **Reference Integrations**
  - [ ] Gmail (OAuth2, send/read/search)
  - [ ] GitHub (webhook support)
- [ ] **Integration SDK**
  - [ ] Integration template
  - [ ] Auth flow helpers
  - [ ] Testing utilities

---

### Phase 6: Extension System (Week 6)
**Goal:** Extensible plugin architecture

#### Already Built ✅
- [x] Extension base class
- [x] Extension manager
- [x] Built-in extensions (audit, undo)

#### Needs Work
- [ ] **Security**
  - [ ] Extension permissions model (M-4)
  - [ ] Extension audit logging (M-5)
  - [ ] Sandboxed agent interface
- [ ] **Developer Experience**
  - [ ] Extension generator CLI
  - [ ] Extension testing framework
  - [ ] Extension marketplace concept

---

### Phase 7: CLI & Developer UX (Week 7)
**Goal:** Delightful developer experience

#### Needs Work
- [ ] **Forge CLI**
  - [ ] `teotl init` - Project scaffolding
  - [ ] `teotl new agent` - Agent template
  - [ ] `teotl new skill` - Skill template
  - [ ] `teotl new extension` - Extension template
  - [ ] `teotl auth <service>` - OAuth flows
  - [ ] `teotl run` - Launch agent
- [ ] **Interactive Mode**
  - [ ] Rich terminal UI
  - [ ] Streaming responses
  - [ ] Progress indicators
- [ ] **Developer Tools**
  - [ ] Agent debugger
  - [ ] Event inspector
  - [ ] Memory browser

---

### Phase 8: Reference Implementation (Week 8)
**Goal:** Personal assistant as framework showcase

This demonstrates what developers can build with Forge:

#### Personal Assistant Features
- [ ] **Filesystem Operations**
  - Uses: Filesystem skill
  - Shows: Skill system, guardrails
- [ ] **Email Management**
  - Uses: Gmail integration
  - Shows: Integration system, OAuth
- [ ] **Task Tracking**
  - Uses: Custom extension
  - Shows: Extension system
- [ ] **Memory & Context**
  - Uses: Memory primitive
  - Shows: Cross-session intelligence

**Purpose:** Dogfooding the framework, proving it works end-to-end

---

## Milestones

### M1: Secure Foundation (End of Week 2)
- [ ] All critical security fixes (C-1, C-2, C-3)
- [ ] Tests passing (80%+ coverage)
- [ ] Basic agent creation works
- [ ] Provider integration solid

**Deliverable:** Can create and run a basic agent securely

---

### M2: Core Primitives Complete (End of Week 5)
- [ ] Guardrails fully wired
- [ ] Skills system functional
- [ ] Memory integration working
- [ ] Integrations with OAuth

**Deliverable:** Framework primitives are usable by developers

---

### M3: Developer Experience (End of Week 7)
- [ ] CLI tools complete (`teotl init`, `teotl new`, etc.)
- [ ] Documentation comprehensive
- [ ] Templates available
- [ ] Testing utilities ready

**Deliverable:** Developers can build agents easily

---

### M4: Reference Implementation (End of Week 8)
- [ ] Personal assistant working on macOS
- [ ] Demonstrates all framework features
- [ ] Daily usage validated
- [ ] Ready for beta testers

**Deliverable:** Proof that framework works for real use cases

---

## Success Criteria

### Framework Success
- [ ] Developers can build custom agents in <1 hour
- [ ] All four primitives work independently and together
- [ ] Security model is sound (audit passed)
- [ ] Extension system allows unlimited customization
- [ ] Documentation is clear and complete

### Reference Implementation Success
- [ ] Personal assistant works for daily use
- [ ] Demonstrates all framework capabilities
- [ ] Zero security incidents during dogfooding
- [ ] Positive user feedback

### Technical Success
- [ ] 80%+ test coverage
- [ ] Zero critical vulnerabilities
- [ ] <2s average response time
- [ ] <$5/day API costs

---

## Getting Started

### Day 1 Checklist
1. [ ] Review this roadmap
2. [ ] Set up project tracker (see PROJECT_TRACKER.md)
3. [ ] Start Phase 1: Security fixes
4. [ ] Write first framework documentation

### Week 1 Focus
- **Security:** C-1, C-2, C-3
- **Testing:** Verify all existing code
- **Docs:** Architecture overview

---

This is a **framework** that happens to ship with a great personal assistant example. Developers can use Forge to build agents for any purpose, including meta-agents that build other agents. 🚀

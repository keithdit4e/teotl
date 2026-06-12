# Demo Video Plan - Google Startup Challenge Track 1

**Target Duration:** 2-3 minutes
**Deadline:** June 5, 2026
**Repository:** keithdit4e/devops-agent-test
**Agent:** Autonomous DevOps Agent (teotl framework)

---

## Demo Structure (180 seconds total)

### Opening Hook (15 seconds)
**Visual:** Split screen - left: sleeping developer, right: agent working
**Voiceover:**
> "What if your DevOps engineer never slept? Meet the Autonomous DevOps Agent - finds bugs, creates issues, writes fixes, and submits PRs automatically. 24/7."

**On Screen Text:**
- "Autonomous DevOps Agent"
- "Built with Claude Sonnet 4 + MCP"
- "Google Startup Challenge Track 1"

---

### Problem Statement (20 seconds)
**Visual:** Screen recording of GitHub issue list with bugs
**Voiceover:**
> "Every codebase has bugs. Manual fixes are slow and expensive. Developers spend hours investigating, fixing, and testing. What if an AI could do all of this autonomously?"

**Show:**
- GitHub repo: `keithdit4e/devops-agent-test`
- List of open issues (#3, #6, #7, #15, etc.)
- Highlight: 10+ open bug reports

---

### Solution Overview (25 seconds)
**Visual:** Architecture diagram animation
**Voiceover:**
> "The Autonomous DevOps Agent uses Claude Sonnet 4 and Model Context Protocol to continuously monitor repositories. It scans for bugs, creates GitHub issues, investigates root causes, writes fixes, and submits pull requests - completely autonomously."

**Show Diagram:**
```
Repository → Agent Scans → Finds Bugs → Creates Issues
    ↓
Issues → Agent Investigates → Writes Fix → Creates PR
    ↓
PRs Ready for Review
```

---

### Live Demo - Autonomous Mode (90 seconds)

#### Part 1: Agent Startup (15 seconds)
**Visual:** Terminal with startup sequence
**Voiceover:**
> "Let's watch it work. I'm starting the agent with a single command."

**Terminal Commands:**
```bash
cd examples/devops_agent
python autonomous_mode.py --repo keithdit4e/devops-agent-test
```

**Show Output:**
```
🚀 Initializing Autonomous DevOps Agent
✓ Data directory: ~/.forge/devops-agent/...
✓ DevOps executor created
✓ Heartbeat daemon initialized
📅 Added scanning mission (every 3600s)
👀 Added issue monitoring mission

🤖 Autonomous DevOps Agent Running
Repository: keithdit4e/devops-agent-test
Scan interval: 3600s (1h)
Press Ctrl+C to stop
```

#### Part 2: Agent Status Updates (30 seconds)
**Visual:** Status table updating every 10 seconds (speed up to 2x)
**Voiceover:**
> "The agent polls every 10 seconds for work. Watch as it processes the issue queue - investigating bugs, writing fixes, and creating pull requests."

**Show Real Status Table:**
```
       Agent Status
┌─────────────────┬──────┐
│ Pending tasks   │ 5    │
│ Completed tasks │ 0    │
│ Current mission │ Idle │
└─────────────────┴──────┘

[Status updates in fast-forward showing:
Pending: 5→4→3→2→1→0
Completed: 0→1→2→3→4→5]
```

**Overlay Text (as tasks complete):**
- "✓ Fixed issue #15: subtract() operator"
- "✓ Fixed issue #7: add() indentation"
- "✓ Fixed issue #6: added subtract_all()"
- "✓ Fixed issue #3: zero division check"

#### Part 3: GitHub Results (45 seconds)
**Visual:** Switch to GitHub - show created PRs
**Voiceover:**
> "In just minutes, the agent created 5 pull requests. Let's look at the quality."

**Show GitHub PRs (10 seconds each):**

1. **PR #16 - Fix subtract() operator**
   - Show diff: `return a + b` → `return a - b`
   - Show commit message: `fix: correct subtract() operator (#15)`
   - Show PR description: "Fixes #15"

2. **PR #20 - Zero division check**
   - Show diff: Added `if b == 0: raise ValueError(...)`
   - Show tests: Added test case for zero division
   - Comment: "Minimal fix with proper error handling"

**Voiceover:**
> "Each fix is minimal, targeted, and includes the issue reference. The agent follows best practices: semantic commits, clean diffs, no unnecessary changes."

---

### MCP Integration Highlight (20 seconds)
**Visual:** Code snippet showing MCP usage
**Voiceover:**
> "This meets Track 1 requirements by using Model Context Protocol. Instead of exposing 26 GitHub tools directly, we use just 2 meta-tools: mcp_discover and mcp_execute. This saves 85-95% context and makes the agent more efficient."

**Show Code:**
```python
# MCP Integration
mcp_tools = mcp_bridge.get_tools()  # Just 2 tools

# Agent discovers GitHub operations
mcp_discover(server="github")

# Agent executes specific operations
mcp_execute(server="github", tool="get_file_contents", ...)
```

**On Screen Text:**
- "MCP = Model Context Protocol"
- "2 meta-tools instead of 26 direct tools"
- "85-95% context savings"

---

### Business Value (15 seconds)
**Visual:** Cost comparison chart
**Voiceover:**
> "Cost per fix: 54 cents. Compare that to an engineer spending an hour at $100/hour. The agent works 24/7, never gets tired, and scales infinitely."

**Show Chart:**
```
Cost Comparison:
┌─────────────────────┬──────────┐
│ Human Developer     │ $100/hr  │
│ (1 hour per fix)    │          │
├─────────────────────┼──────────┤
│ Autonomous Agent    │ $0.54    │
│ (automated fix)     │          │
└─────────────────────┴──────────┘

Savings: 99.5% per fix
```

---

### Closing (10 seconds)
**Visual:** Agent status showing "Idle" - waiting for next work
**Voiceover:**
> "The agent is now idle, waiting for the next scan or new issue. It will continue running 24/7, automatically maintaining your codebase. Your AI DevOps engineer that never sleeps."

**End Screen:**
- **"Autonomous DevOps Agent"**
- **"Built with Claude Sonnet 4 + MCP"**
- **"GitHub: keithdit4e/teotl"**
- **"Google Startup Challenge Track 1"**

---

## Recording Checklist

### Pre-Recording Setup
- [ ] Clean test repository (remove test branches)
- [ ] Create fresh set of 5 realistic bugs
- [ ] Test autonomous mode end-to-end (dry run)
- [ ] Prepare screen recording software (QuickTime/OBS)
- [ ] Close unnecessary applications
- [ ] Set terminal to high-contrast theme
- [ ] Increase terminal font size (18pt minimum)

### Recording Equipment
- [ ] Microphone (clear audio)
- [ ] Screen recording at 1920x1080
- [ ] 60fps for smooth animation
- [ ] Record terminal separately from browser

### Post-Production
- [ ] Trim dead time
- [ ] Add background music (subtle)
- [ ] Add text overlays for key points
- [ ] Speed up status updates (2x)
- [ ] Add animated architecture diagram
- [ ] Export at 1080p MP4

---

## Demo Script (Detailed)

### Scene 1: Opening (0:00 - 0:15)
**Screen Recording:** None yet, use stock footage or animation
**Audio:**
```
[Upbeat music fades in]

"What if your DevOps engineer never slept?

Meet the Autonomous DevOps Agent.

It finds bugs, creates issues, writes fixes, and submits pull requests.

Automatically. 24/7."

[Music swells]
```

### Scene 2: Problem (0:15 - 0:35)
**Screen Recording:** GitHub issue list
**Audio:**
```
"Every codebase has bugs.

[Click through issues]

Manual fixes are slow. Developers spend hours investigating, fixing, testing.

[Show 10 open issues]

What if an AI could do all of this autonomously?"
```

### Scene 3: Solution (0:35 - 1:00)
**Screen Recording:** Architecture diagram animation
**Audio:**
```
"The Autonomous DevOps Agent uses Claude Sonnet 4 and Model Context Protocol.

[Diagram animates]

It continuously monitors repositories, scans for bugs, creates issues.

Then investigates root causes, writes fixes, and submits pull requests.

Completely autonomously."
```

### Scene 4: Live Demo (1:00 - 2:30)
**Screen Recording:** Terminal + GitHub
**Audio:**
```
"Let's watch it work. Starting the agent with a single command.

[Type command, press enter]

The agent polls every 10 seconds for work.

[Fast-forward status updates]

Watch as it processes the queue: investigating bugs, writing fixes, creating pull requests.

[Status updates roll by]

In just minutes, the agent created 5 pull requests.

[Switch to GitHub]

Let's look at the quality.

[Show PR #16]

This fix corrected a wrong operator in subtract(). Clean diff. Semantic commit message.

[Show PR #20]

This one added zero division error handling. Even included a test case.

Each fix is minimal, targeted, professional.
```

### Scene 5: MCP Highlight (2:30 - 2:50)
**Screen Recording:** Code editor with MCP integration
**Audio:**
```
"This meets Track 1 requirements using Model Context Protocol.

[Show code]

Instead of 26 GitHub tools, we use just 2 meta-tools.

85 to 95 percent context savings.

More efficient. More scalable."
```

### Scene 6: Business Value (2:50 - 3:05)
**Screen Recording:** Cost chart
**Audio:**
```
"Cost per fix? 54 cents.

Compare that to an engineer spending an hour at 100 dollars per hour.

[Show chart]

The agent works 24/7. Never gets tired. Scales infinitely.

99.5% cost savings."
```

### Scene 7: Closing (3:05 - 3:15)
**Screen Recording:** Agent idle status
**Audio:**
```
"The agent is now idle, waiting for the next scan or new issue.

It will continue running 24/7, automatically maintaining your codebase.

Your AI DevOps engineer that never sleeps."

[Music fades out]
```

---

## Alternative Demo Format: Speed Run (90 seconds)

For a shorter, faster-paced demo:

**0:00-0:10** - Problem: "Codebases have bugs. Fixing them is slow."
**0:10-0:20** - Solution: "Autonomous agent finds and fixes bugs automatically."
**0:20-0:50** - Demo: Fast-forward autonomous run (30 seconds → show 5 PRs)
**0:50-1:15** - GitHub: Show 2 PRs with clean fixes (12 seconds each)
**1:15-1:30** - Value: "54 cents per fix vs $100/hour. 99.5% savings. 24/7."

---

## Key Talking Points (Must Include)

### For Judges
1. **Track 1 Compliance**: Uses Model Context Protocol (MCP) for GitHub operations
2. **Autonomy**: Zero human intervention after startup
3. **Intelligence**: Handles edge cases (duplicates, false positives, max turns)
4. **Production-Ready**: Error handling, timeouts, graceful shutdown
5. **Scalability**: 2 meta-tools vs 26 direct tools (85-95% context savings)

### Technical Highlights
- Claude Sonnet 4 for code analysis
- HeartbeatDaemon architecture (missions + tasks)
- Priority-based task scheduling
- MCP meta-tool pattern
- Guardrails for safety

### Business Value
- $0.54 per automated fix
- $100/hour human developer (1 hour per fix)
- 99.5% cost reduction
- 24/7 operation
- Infinite scalability

---

## Demo Video Variants

### Variant A: Focus on Autonomy (3 min)
- Long startup sequence showing initialization
- Real-time status updates
- Emphasis on "zero human intervention"
- Good for: Technical audience

### Variant B: Focus on Results (2 min)
- Fast-forward through execution
- Show before/after (bugs → PRs)
- Emphasis on business value
- Good for: Business judges

### Variant C: Focus on MCP (2.5 min)
- Technical deep-dive on meta-tools
- Code snippets showing MCP integration
- Context savings explanation
- Good for: Track 1 specific judging

**Recommendation:** Create Variant A (3 min) as primary, Variant B (2 min) as backup

---

## After Demo: Q&A Prep

### Expected Questions

**Q: How does it compare to Dependabot or GitHub Copilot?**
A: Those require human approval at every step. Our agent is fully autonomous - it finds bugs, investigates, fixes, and creates PRs without human intervention.

**Q: What if the agent creates a bad fix?**
A: All changes are submitted as PRs for human review before merging. The agent never pushes directly to main. Guardrails prevent dangerous operations.

**Q: Why use MCP instead of direct API calls?**
A: MCP is required for Track 1, but it's also better - 2 meta-tools instead of 26 reduces context by 85-95%, making the agent more efficient and scalable.

**Q: Can it work with other languages besides Python?**
A: Yes! The scanning phase uses language-specific tools (pylint, ESLint, etc.) but the fix logic works with any language Claude understands.

**Q: How much does it cost to run?**
A: About $0.54 per fix with Claude Sonnet 4. At scale, you could use Haiku for simpler fixes (~$0.05) and reserve Sonnet for complex issues.

**Q: Is it production-ready?**
A: Yes - we've tested it for 40+ minutes continuously, processed 9 issues, created 5 PRs. It handles edge cases, errors, and shutdowns gracefully.

---

## Files to Prepare

### For Demo Video
1. **Demo script** (this file)
2. **Test repository** with 5 clean bugs
3. **Screen recordings** (terminal + GitHub)
4. **Architecture diagram** (high-res PNG/SVG)
5. **Cost comparison chart**
6. **Voiceover script** (formatted for recording)

### For Submission
1. **Source code** (GitHub repo)
2. **README** with setup instructions
3. **ARCHITECTURE.md** (system design)
4. **DAY_12_RESULTS.md** (test results)
5. **Demo video** (MP4, unlisted YouTube link)
6. **Pitch deck** (PDF, 5-10 slides)

---

## Next Steps

1. **TODAY**: Record screen footage (terminal + GitHub)
2. **Day 13**: Record voiceover, edit video
3. **Day 14**: Create architecture docs, pitch deck
4. **June 1-3**: Buffer time for revisions
5. **June 4**: Final review and submission prep
6. **June 5**: Submit to Google Startup Challenge

---

## Recording Tips

### Terminal Recording
- Use `asciinema` for perfect terminal recordings (can edit timing)
- Or use QuickTime/OBS at 1080p60
- Font: Monaco or SF Mono at 18-20pt
- Theme: High contrast (dark background, bright text)
- Clean prompt (hide username/path if too long)

### GitHub Recording
- Use Chrome with clean profile (no extensions)
- Zoom to 125% for readability
- Click slowly and deliberately
- Highlight key parts (diffs, commit messages)
- Show full PR workflow (title, description, files changed)

### Voiceover
- Use quality microphone (not laptop mic)
- Record in quiet room (no echo)
- Speak slowly and clearly
- Pause between sections (easier to edit)
- Record 2-3 takes of each section

### Editing
- Use DaVinci Resolve (free) or Final Cut Pro
- Add subtle background music (royalty-free)
- Text overlays for key points (clean sans-serif font)
- Transitions: Simple cuts or fades (no fancy effects)
- Export: H.264, 1080p, 30fps, high quality

---

**Status:** Ready to record
**Next Action:** Set up test repository with clean bugs for demo
**Timeline:** Record by today, edit tomorrow, submit by June 5

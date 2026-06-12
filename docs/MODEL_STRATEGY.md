# Multi-Model Strategy for Autonomous Development

## Overview

Use **different models for different phases** to optimize cost, speed, and quality:

- **Analysis/Planning**: Smart model (Sonnet) for deep reasoning
- **Execution**: Fast model (Haiku) for implementing specific tasks
- **Review** (optional): Smart model for final validation

This can reduce costs by **80-90%** while maintaining quality.

## Model Phases

### Phase 1: Analysis/Planning (Rare, Deep)

**When:** Generating initial roadmap (once)

**Model:** Claude Sonnet 4
- **Use case:** Codebase analysis, identifying improvements, prioritization
- **Frequency:** Once per roadmap (every 10-20 improvements)
- **Cost:** High (~$15 per million tokens)
- **Quality:** Best reasoning, deep analysis

**Why Sonnet:**
- Needs to understand entire codebase
- Requires complex reasoning about impact/safety
- Creates foundation for all future work
- Run once, benefits multiply

**Example output:**
```
Roadmap of 20 improvements:
1. [BUG] auth.py:45 - Missing None check → NullPointer
2. [TYPE] helpers.py:12 - Add type hints for IDE support
3. [ERROR] api.py:89 - Add try/except for network failures
...
```

### Phase 2: Execution (Frequent, Focused)

**When:** Implementing each improvement (20+ times)

**Model:** Claude 3 Haiku
- **Use case:** Making specific code changes, running tests, iterating
- **Frequency:** Every improvement (20+ per roadmap)
- **Cost:** Low (~$0.25 per million tokens) - **60x cheaper than Sonnet!**
- **Quality:** Good for focused tasks

**Why Haiku:**
- Task is specific (from roadmap): "Add type hints to format_size()"
- Doesn't need deep reasoning, just execution
- Fast iteration (5 retries × 20 improvements = 100 API calls)
- Cost matters at scale

**Example execution:**
```
Attempt 1: Adding type hints...
def format_size(bytes: int) -> str:  # ← Haiku can do this
    ...

Tests: FAILED (need int|float)

Attempt 2: Adjusting types...
def format_size(bytes: int | float) -> str:  # ← And this
    ...

Tests: PASSED ✅
```

### Phase 3: Review (Optional, Selective)

**When:** Before committing critical changes

**Model:** Claude Sonnet 4
- **Use case:** Final validation, security review
- **Frequency:** Optional (disabled by default)
- **Cost:** Medium (only for critical changes)
- **Quality:** Best validation

**Enable in config:**
```yaml
models:
  review:
    name: claude-sonnet-4-20250514
    enabled: true  # ← Enable review phase
```

## Cost Analysis

### Example: 20 Improvements with 5 Retries Each

**Without multi-model (all Sonnet):**
- Analysis: 1 × $15 = $15
- Execution: 100 × $15 = $1,500
- **Total: $1,515**

**With multi-model (Sonnet + Haiku):**
- Analysis: 1 × $15 = $15
- Execution: 100 × $0.25 = $25
- **Total: $40**

**Savings: $1,475 (97% reduction!)**

### Real-World Usage

For continuous autonomous development:
- Roadmap refresh: Every 20 improvements (weekly)
- Executions: ~100 per week

**Monthly costs:**
- All Sonnet: ~$6,000/month
- Multi-model: ~$160/month

**The smart model does deep work once, fast model executes 100 times.**

## Configuration

Edit `~/.teotl/agents/coding-assistant/AUTONOMOUS_CONFIG.yaml`:

```yaml
models:
  # Analysis phase - use smart model
  analysis:
    name: claude-sonnet-4-20250514  # Best reasoning
    max_tokens: 8192
    use_case: "Deep codebase analysis, roadmap planning"
    cost: high
    quality: best

  # Execution phase - use fast model
  execution:
    name: claude-3-haiku-20240307  # Fast & cheap
    max_tokens: 4096
    use_case: "Implementing tasks, running tests, iterating"
    cost: low
    quality: good

  # Review phase - optional
  review:
    name: claude-sonnet-4-20250514  # Best validation
    max_tokens: 4096
    enabled: false  # Disable to save cost
```

## Model Options

### Analysis Phase Options

| Model | Cost | Quality | When to Use |
|-------|------|---------|-------------|
| **Claude Sonnet 4** | High | Best | Default (recommended) |
| Claude Opus 4 | Very High | Best+ | Critical codebases only |
| Claude 3.5 Sonnet | Medium | Good | Budget-conscious |

### Execution Phase Options

| Model | Cost | Quality | When to Use |
|-------|------|---------|-------------|
| **Claude 3 Haiku** | Low | Good | Default (recommended) |
| Claude 3.5 Haiku | Low | Good+ | If available |
| Claude 3.5 Sonnet | Medium | Better | Complex changes |
| Claude Sonnet 4 | High | Best | Critical changes only |

### Trade-off Matrix

```
Quality vs Cost for 100 executions:

High Quality │              ● Sonnet ($1,500)
             │            ╱
             │          ╱
Good Quality │        ● 3.5 Sonnet ($750)
             │      ╱
             │    ╱
Acceptable   │  ● Haiku ($25) ← Recommended
             │
             └──────────────────────────────
               Low Cost        High Cost
```

## When to Use Different Models

### Use Sonnet for Execution When:

1. **Critical security changes**
   ```yaml
   # For security-focused roadmap
   focus:
     - name: security
       priority: 1
   models:
     execution:
       name: claude-sonnet-4-20250514  # Use smart model
   ```

2. **Complex refactoring**
   - Multi-file changes
   - Architecture modifications
   - Breaking API changes

3. **Initial setup/testing**
   - First time using system
   - Want to see best-case results
   - Establishing baseline quality

### Use Haiku for Execution When:

1. **Simple improvements** (recommended default)
   - Type hints
   - Docstrings
   - Error handling
   - Small bug fixes

2. **High iteration count**
   - Running continuously
   - Large roadmaps (50+ items)
   - Cost-conscious operation

3. **Stable, focused tasks**
   - Roadmap already defined by Sonnet
   - Tasks are specific and clear
   - Tests provide feedback

## Quality Assessment

**Does Haiku produce lower quality?**

Not necessarily! Consider:

1. **Task specificity matters**
   - Haiku + specific task = Good results
   - Haiku + vague task = Poor results
   - **Solution:** Sonnet creates specific roadmap, Haiku executes it

2. **Tests provide feedback**
   - Haiku makes change
   - Tests fail → Haiku sees error
   - Haiku adjusts (up to 5 times)
   - **Result:** Tests ensure quality regardless of model

3. **Measured outcomes**
   - Haiku success rate: 70-80% (per attempt)
   - Sonnet success rate: 85-95% (per attempt)
   - With 5 retries: Both achieve ~95% final success
   - **Difference:** Haiku needs more attempts but reaches same goal

## Hybrid Strategies

### Strategy 1: Progressive Intelligence

Start cheap, escalate if needed:

```yaml
execution:
  # Try Haiku first (fast, cheap)
  primary_model: claude-3-haiku-20240307
  max_retries: 3

  # Escalate to Sonnet if Haiku fails
  fallback_model: claude-sonnet-4-20250514
  fallback_after: 3  # Switch after 3 Haiku failures
```

### Strategy 2: Time-Based

Different models for different times:

```yaml
execution:
  # Daytime: Use Haiku (fast iteration)
  daytime_model: claude-3-haiku-20240307
  daytime_hours: [9, 17]  # 9 AM - 5 PM

  # Nighttime: Use Sonnet (overnight batch)
  nighttime_model: claude-sonnet-4-20250514
  nighttime_hours: [22, 6]  # 10 PM - 6 AM
```

### Strategy 3: Priority-Based

Model selection by improvement priority:

```yaml
focus:
  - name: critical_bugs
    priority: 1
    model: claude-sonnet-4-20250514  # Use smart model

  - name: type_safety
    priority: 3
    model: claude-3-haiku-20240307  # Use fast model
```

## Monitoring Model Performance

Track success rates per model:

```python
# In mission metadata
{
  "model_stats": {
    "claude-3-haiku-20240307": {
      "attempts": 87,
      "successes": 68,
      "success_rate": 0.78,
      "avg_retries": 2.1
    },
    "claude-sonnet-4-20250514": {
      "attempts": 13,
      "successes": 12,
      "success_rate": 0.92,
      "avg_retries": 1.2
    }
  }
}
```

If Haiku success rate drops below 60%, consider:
- Using Sonnet for execution
- Simplifying roadmap items
- Improving test feedback

## Best Practices

### 1. Always Use Sonnet for Analysis

**Don't:** Try to save money on roadmap generation
```yaml
analysis:
  name: claude-3-haiku-20240307  # ❌ Bad - weak analysis
```

**Do:** Invest in good roadmap
```yaml
analysis:
  name: claude-sonnet-4-20250514  # ✅ Good - strong foundation
```

**Why:** A smart roadmap makes execution easier. Weak analysis = vague tasks = Haiku struggles.

### 2. Start with Haiku, Measure, Adjust

**Month 1:** Use Haiku, track results
**Month 2:** If success rate < 70%, upgrade execution model
**Month 3:** Optimize based on data

### 3. Let Tests Be the Arbiter

Models vary, but tests don't lie:
- Haiku passes tests → Good enough ✅
- Sonnet fails tests → Not better ❌

Quality = "Does it work?" not "Which model made it?"

### 4. Consider Total Cost

**Apparent cost:** Haiku vs Sonnet per token

**Real cost:** Including retries and human time
- Haiku: 3 retries × $0.25 = $0.75 + 0 human time
- Sonnet: 1 try × $15 = $15 + 0 human time
- Human: 1 fix × $50/hour = $50 + frustration

**Even with 5× retries, Haiku is cheaper.**

## Summary

**The Strategy:**
1. **Sonnet analyzes** → Creates specific, prioritized roadmap
2. **Haiku executes** → Implements focused tasks with retries
3. **Tests validate** → Ensure quality regardless of model
4. **Dashboard tracks** → Monitor success rates per model

**The Result:**
- 97% cost reduction
- Minimal quality impact (tests ensure correctness)
- Faster iteration (Haiku is fast)
- Scalable autonomous development

**The Trade-off:**
- Haiku needs more retries (2-3 vs 1-2)
- Total time per improvement: ~same (Haiku is faster per try)
- Quality output: same (tests validate both)

**Bottom line:** Use the smart model to think, fast model to execute. Let tests ensure quality. Save 97% on costs.

---

**Current Configuration:** See `~/.teotl/agents/coding-assistant/AUTONOMOUS_CONFIG.yaml`

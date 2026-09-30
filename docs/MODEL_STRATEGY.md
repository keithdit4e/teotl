# Multi-Model Strategy for Autonomous Development

## Overview

Use **different models for different phases** to optimize cost, speed, and quality:

- **Analysis/Planning**: Smart model (Sonnet) for deep reasoning
- **Execution**: Fast model (Haiku) for implementing specific tasks
- **Review** (optional): Smart model for final validation

With current pricing this cuts execution cost roughly in half (see [Cost Analysis](#cost-analysis)), and the fast model also makes each retry quicker.

## Model Phases

### Phase 1: Analysis/Planning (Rare, Deep)

**When:** Generating initial roadmap (once)

**Model:** Claude Sonnet 5.5 (`claude-sonnet-5-5`)
- **Use case:** Codebase analysis, identifying improvements, prioritization
- **Frequency:** Once per roadmap (every 10-20 improvements)
- **Cost:** $2 input / $10 output per million tokens
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

**Model:** Claude Haiku 4.5 (`claude-haiku-4-5`)
- **Use case:** Making specific code changes, running tests, iterating
- **Frequency:** Every improvement (20+ per roadmap)
- **Cost:** $1 input / $5 output per million tokens (half of Sonnet 5.5)
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

**Model:** Claude Sonnet 5.5 (`claude-sonnet-5-5`)
- **Use case:** Final validation, security review
- **Frequency:** Optional (disabled by default)
- **Cost:** Medium (only for critical changes)
- **Quality:** Best validation

**Enable in config:**
```yaml
models:
  review:
    name: claude-sonnet-5-5
    enabled: true  # ← Enable review phase
```

## Cost Analysis

### Example: 20 Improvements with 5 Retries Each

Assume each call uses about 20K input tokens and 2K output tokens:

| Model | Cost per call |
|-------|---------------|
| Claude Sonnet 5.5 | 20K × $2/M + 2K × $10/M = **$0.06** |
| Claude Haiku 4.5 | 20K × $1/M + 2K × $5/M = **$0.03** |

**Without multi-model (all Sonnet):**
- Analysis: 1 × $0.06 = $0.06
- Execution: 100 × $0.06 = $6.00
- **Total: $6.06**

**With multi-model (Sonnet + Haiku):**
- Analysis: 1 × $0.06 = $0.06
- Execution: 100 × $0.03 = $3.00
- **Total: $3.06**

**Savings: about 50%**, as long as Haiku doesn't need many more attempts than Sonnet (see [Consider Total Cost](#4-consider-total-cost)). Your token counts will differ; the ratio is what matters.

### Real-World Usage

For continuous autonomous development:
- Roadmap refresh: Every 20 improvements (weekly)
- Executions: ~100 per week

**Monthly costs** (same per-call assumptions, ~430 executions and 4 roadmaps a month):
- All Sonnet: ~$26/month
- Multi-model: ~$13/month

**The smart model does deep work once, fast model executes 100 times.**

## Configuration

Edit `~/.teotl/agents/coding-assistant/AUTONOMOUS_CONFIG.yaml`:

```yaml
models:
  # Analysis phase - use smart model
  analysis:
    name: claude-sonnet-5-5  # Best reasoning
    max_tokens: 8192
    use_case: "Deep codebase analysis, roadmap planning"
    cost: high
    quality: best

  # Execution phase - use fast model
  execution:
    name: claude-haiku-4-5  # Fast & cheap
    max_tokens: 4096
    use_case: "Implementing tasks, running tests, iterating"
    cost: low
    quality: good

  # Review phase - optional
  review:
    name: claude-sonnet-5-5  # Best validation
    max_tokens: 4096
    enabled: false  # Disable to save cost
```

## Model Options

### Analysis Phase Options

| Model | Cost | Quality | When to Use |
|-------|------|---------|-------------|
| **Claude Sonnet 5.5** (`claude-sonnet-5-5`) | $2 / $10 | Excellent | Default (recommended) |
| Claude Opus 5.5 (`claude-opus-5-5`) | $4 / $20 | Best | Large or critical codebases |
| Claude Fable 5.1 (`claude-fable-5-1`) | $10 / $50 | Most capable | Hardest long-horizon work |

### Execution Phase Options

| Model | Cost | Quality | When to Use |
|-------|------|---------|-------------|
| **Claude Haiku 4.5** (`claude-haiku-4-5`) | $1 / $5 | Good | Default (recommended) |
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | $2 / $10 | Excellent | Complex changes |
| Claude Opus 5.5 (`claude-opus-5-5`) | $4 / $20 | Best | Critical changes only |

Costs are input / output USD per million tokens (Anthropic API list prices, September 2026). Model IDs and prices used for cost tracking live in `teotl/core/models.py`.

### Trade-off Matrix

```
Quality vs Cost for 100 executions:

Best Quality │              ● Opus 5.5 ($12)
             │            ╱
             │          ╱
Excellent    │        ● Sonnet 5.5 ($6)
             │      ╱
             │    ╱
Good         │  ● Haiku 4.5 ($3) ← Recommended
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
       name: claude-sonnet-5-5  # Use smart model
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
  primary_model: claude-haiku-4-5
  max_retries: 3

  # Escalate to Sonnet if Haiku fails
  fallback_model: claude-sonnet-5-5
  fallback_after: 3  # Switch after 3 Haiku failures
```

### Strategy 2: Time-Based

Different models for different times:

```yaml
execution:
  # Daytime: Use Haiku (fast iteration)
  daytime_model: claude-haiku-4-5
  daytime_hours: [9, 17]  # 9 AM - 5 PM

  # Nighttime: Use Sonnet (overnight batch)
  nighttime_model: claude-sonnet-5-5
  nighttime_hours: [22, 6]  # 10 PM - 6 AM
```

### Strategy 3: Priority-Based

Model selection by improvement priority:

```yaml
focus:
  - name: critical_bugs
    priority: 1
    model: claude-sonnet-5-5  # Use smart model

  - name: type_safety
    priority: 3
    model: claude-haiku-4-5  # Use fast model
```

## Monitoring Model Performance

Track success rates per model:

```python
# In mission metadata
{
  "model_stats": {
    "claude-haiku-4-5": {
      "attempts": 87,
      "successes": 68,
      "success_rate": 0.78,
      "avg_retries": 2.1
    },
    "claude-sonnet-5-5": {
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
  name: claude-haiku-4-5  # ❌ Bad - weak analysis
```

**Do:** Invest in good roadmap
```yaml
analysis:
  name: claude-sonnet-5-5  # ✅ Good - strong foundation
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
- Haiku: 2 tries × $0.03 = $0.06
- Sonnet: 1 try × $0.06 = $0.06
- Human: 1 fix × $50/hour = $50 + frustration

**Haiku is cheaper only while it needs fewer than about 2 attempts for every 1 Sonnet attempt.** Track success rates per model; if Haiku keeps retrying, Sonnet is the cheaper worker. Either way, both are far cheaper than a human fix.

## Summary

**The Strategy:**
1. **Sonnet analyzes** → Creates specific, prioritized roadmap
2. **Haiku executes** → Implements focused tasks with retries
3. **Tests validate** → Ensure quality regardless of model
4. **Dashboard tracks** → Monitor success rates per model

**The Result:**
- About 50% lower execution cost
- Minimal quality impact (tests ensure correctness)
- Faster iteration (Haiku is fast)
- Scalable autonomous development

**The Trade-off:**
- Haiku needs more retries (2-3 vs 1-2)
- Total time per improvement: ~same (Haiku is faster per try)
- Quality output: same (tests validate both)

**Bottom line:** Use the smart model to think, fast model to execute. Let tests ensure quality, and measure retries to confirm the savings.

---

**Current Configuration:** See `~/.teotl/agents/coding-assistant/AUTONOMOUS_CONFIG.yaml`

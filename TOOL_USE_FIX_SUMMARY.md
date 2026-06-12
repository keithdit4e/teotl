# Tool Use API Format Fix

## Problem Identified

When the agent tried to use skills (tools), it crashed with:
```
Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error',
'message': 'messages: Unexpected role "tool". Allowed roles are "user" or "assistant".'}}
```

### Root Cause

The agent was formatting tool results incorrectly for the Anthropic API:

**Incorrect Format (what we had):**
```python
messages.append({"role": "assistant", "content": result.content})
messages.append({"role": "tool", "content": tool_result.output})  # ❌ WRONG
```

The Anthropic API **does not accept** `"role": "tool"` in messages.

**Correct Format (what we need):**
```python
# Assistant message with tool use content blocks
messages.append({
    "role": "assistant",
    "content": [
        {"type": "text", "text": result.content},
        {"type": "tool_use", "id": tool_call.id, "name": tool_call.name, "input": tool_call.args}
    ]
})

# User message with tool result content blocks
messages.append({
    "role": "user",
    "content": [
        {"type": "tool_result", "tool_use_id": tool_call.id, "content": tool_result.output}
    ]
})
```

## Fix Applied

Modified `forge/core/agent.py` (lines 251-290) to:

1. **Format assistant messages properly**:
   - Use content blocks instead of plain text
   - Include `tool_use` blocks with tool call details

2. **Format tool results as user messages**:
   - Use `"role": "user"` instead of `"role": "tool"`
   - Include `tool_result` content blocks with results

3. **Collect all tool results before adding to messages**:
   - Process all tool calls first
   - Then add one user message with all tool results

## Anthropic API Tool Use Flow

The correct message sequence for tool use is:

1. **User asks question** → User message
2. **Model decides to use tools** → Assistant message with `tool_use` blocks
3. **Tool results returned** → User message with `tool_result` blocks
4. **Model responds** → Assistant message with final response

## Testing After Fix

The fix has been applied to both:
- `/Users/keithfoster/agent/teotl/` (working installation)
- `/Users/keithfoster/Documents/GitHub/teotl/` (git repository)

### Test Command
```bash
cd /Users/keithfoster/agent/teotl
python3 -m forge.cli chat --agent coding-assistant --skills filesystem,git,web
```

### Test Interaction
```
You: List all Python files in the forge/cli directory
```

**Expected**: Agent successfully uses the filesystem skill and returns the list of files.

**Before Fix**: Crashed with "Unexpected role 'tool'" error.

**After Fix**: Works correctly! ✅

## Related Fixes in This Session

1. **Skills Parsing Fix** (commit 383f047)
   - Fixed comma-separated skills argument parsing
   - `/skills` command now shows all enabled skills

2. **Tool Use Format Fix** (commit 83149d8) ← **This fix**
   - Fixed Anthropic API message format for tool results
   - Skills can now actually execute successfully

## References

- [Anthropic Tool Use Documentation](https://docs.anthropic.com/en/docs/tool-use)
- Anthropic API only accepts `"user"` and `"assistant"` roles
- Tool results must be formatted as content blocks, not role messages

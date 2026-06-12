# Demo Checklist

Quick reference for running the internal demo.

## Setup (5 min, one-time)

- [ ] Get API key from provider (Anthropic/OpenAI) or install Ollama
- [ ] Set environment variable: `export ANTHROPIC_API_KEY="your-key"`
- [ ] Install dependencies: `pip install anthropic pyyaml`
- [ ] Verify setup: `echo $ANTHROPIC_API_KEY`

## Run Demo (5 min)

```bash
cd demos/internal
python demo_with_config.py
```

Watch for:
- ✅ URGENT task executes first
- ✅ HIGH task executes next
- ✅ Mission runs on schedule
- ✅ LOW task runs last
- ✅ Clean shutdown (Ctrl+C)

## Expected Cost

- Anthropic Sonnet 4: ~$0.60-1.50
- OpenAI GPT-4o: ~$0.40-1.20
- Ollama: $0.00 (free, local)

## Files

- `README.md` - Start here
- `config.yaml` - Configuration
- `demo_with_config.py` - Main script
- `REAL_SETUP.md` - Detailed setup
- `DEMO_SUMMARY.md` - What we built

## Success

Demo succeeded if:
- ✅ 3 tasks completed
- ✅ Missions executed
- ✅ Priority order visible
- ✅ No errors

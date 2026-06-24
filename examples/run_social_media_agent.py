#!/usr/bin/env python3
"""Run the Teotl Social Media Content Creator agent."""

import asyncio
import os
import sys
from pathlib import Path

# Ensure HOME is set (fixes guardrails issue)
if "HOME" not in os.environ:
    os.environ["HOME"] = str(Path.home())

from teotl.config import create_agent_from_yaml


async def main():
    # Load the agent from YAML config
    config_path = Path(__file__).parent / "social_media_agent.yaml"
    agent = create_agent_from_yaml(config_path)

    print("=" * 60)
    print("Teotl Social Media Content Creator")
    print("=" * 60)
    print("\nExample prompts:")
    print("  - Create a Twitter thread about Teotl's Memory feature")
    print("  - Write LinkedIn posts about SMB automation use cases")
    print("  - Create a week of content covering all core features")
    print("  - Generate Instagram captions for Teotl productivity tips")
    print("\nType 'quit' to exit.\n")

    while True:
        try:
            prompt = input("You: ").strip()

            if not prompt:
                continue

            if prompt.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            print("\nAgent is working (this may take 30-60 seconds)...\n")
            try:
                response = await agent.run(prompt)
                print(f"\nAgent:\n{response}\n")
            except Exception as e:
                print(f"\nError: {e}\n")
            print("-" * 60)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())

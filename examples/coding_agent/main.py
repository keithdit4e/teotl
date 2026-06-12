"""
Example: Coding Agent

A simple coding assistant that can read/write files and run commands.
"""

import asyncio

from forge import Agent

from teotl.core.provider import AnthropicProvider
from teotl.extensions.builtin import AuditExtension, UndoExtension


async def main():
    agent = Agent(
        provider=AnthropicProvider(model="claude-sonnet-4-20250514"),
        instructions="""You are a coding assistant. You help users write, debug,
        and refactor code. You can read and write files, run tests, and use git.
        Always explain what you're doing before making changes.""",
        skills=["filesystem", "git"],
        policy="standard",
        extensions=[
            AuditExtension(),
            UndoExtension(),
        ],
    )

    # One-shot mode
    response = await agent.run("Show me the project structure")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())

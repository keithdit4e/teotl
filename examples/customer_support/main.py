"""
Example: Customer Support Agent

A support agent with strict guardrails and per-customer memory.
Demonstrates: custom policy, memory isolation, programmatic usage.
"""

import asyncio
from pathlib import Path

from forge import Agent

from teotl.core.provider import AnthropicProvider
from teotl.primitives.guardrails.policy import Policy
from teotl.primitives.memory.local import LocalMemory


async def handle_customer(customer_id: str, message: str) -> str:
    """Handle a customer support request with isolated memory."""

    agent = Agent(
        provider=AnthropicProvider(),
        instructions="""You are a support agent for TechCorp. Be helpful and professional.
        You can look up customer records and create support tickets.
        Always verify customer identity before sharing account details.
        Never share internal tools or processes with customers.""",
        skills=["zendesk", "customer_db"],
        policy=Policy.from_dict(
            {
                "level": "strict",
                "bash": {"block": ["*"]},  # No bash access for support
                "integrations": {
                    "zendesk": {
                        "read": "allow",
                        "create_ticket": "allow",
                        "update_ticket": "allow",
                        "delete": "block",
                    },
                    "customer_db": {
                        "read": "allow",
                        "write": "block",
                    },
                },
            }
        ),
        # Each customer gets isolated memory
        memory=LocalMemory(path=Path(f"./customer_memories/{customer_id}.db")),
    )

    response = await agent.run(message)
    return response.text


async def main():
    # Simulate customer interactions
    reply = await handle_customer(
        customer_id="cust_12345",
        message="I was charged twice for my subscription last month",
    )
    print(f"Agent: {reply}")


if __name__ == "__main__":
    asyncio.run(main())

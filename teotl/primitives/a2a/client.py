"""HTTP client for agent-to-agent communication."""

import aiohttp

from teotl.primitives.a2a.protocol import A2ARequest, A2AResponse


class A2AClient:
    """HTTP client for sending tasks to other agents.

    Example:
        client = A2AClient(endpoint="http://localhost:8001/a2a")

        request = A2ARequest(
            requester_agent_id="personal-agent",
            task_description="Send email to john@example.com",
            context={"recipient": "john@example.com"},
        )

        response = await client.send_task(request)
        if response.status == A2AStatus.COMPLETED:
            print("Task completed:", response.result)
    """

    def __init__(self, endpoint: str, timeout: int = 30):
        """Initialize A2A client.

        Args:
            endpoint: Agent's A2A endpoint (e.g., "http://localhost:8001/a2a")
            timeout: Request timeout in seconds (default: 30)
        """
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    async def send_task(self, request: A2ARequest) -> A2AResponse:
        """Send a task to another agent.

        Args:
            request: A2A request with task details

        Returns:
            A2AResponse with result or error

        Raises:
            aiohttp.ClientError: If HTTP request fails
            TimeoutError: If request times out
        """
        timeout = aiohttp.ClientTimeout(total=request.timeout_seconds or self.timeout)

        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(
                f"{self.endpoint}/task",
                json=request.model_dump(),
            ) as resp,
        ):
            resp.raise_for_status()
            data = await resp.json()
            return A2AResponse(**data)

    async def get_task_status(self, task_id: str) -> A2AResponse:
        """Get status of an async task.

        Args:
            task_id: Task ID returned from send_task

        Returns:
            A2AResponse with current status

        Raises:
            aiohttp.ClientError: If HTTP request fails
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(
                f"{self.endpoint}/task/{task_id}",
            ) as resp,
        ):
            resp.raise_for_status()
            data = await resp.json()
            return A2AResponse(**data)

    async def health_check(self) -> bool:
        """Check if agent endpoint is reachable.

        Returns:
            True if agent responds to health check
        """
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.endpoint}/health") as resp:
                    return resp.status == 200
        except Exception:
            return False

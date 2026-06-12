"""HTTP server for receiving agent-to-agent tasks."""

import logging
from collections.abc import Callable

from aiohttp import web

from teotl.primitives.a2a.protocol import A2ARequest, A2AResponse, A2AStatus
from teotl.primitives.tasks import Priority, Task, TaskStore

logger = logging.getLogger(__name__)


class A2AServer:
    """HTTP server for receiving A2A tasks from other agents.

    Example:
        async def task_handler(request: A2ARequest) -> A2AResponse:
            # Process the task
            return A2AResponse(
                status=A2AStatus.COMPLETED,
                result={"status": "done"},
            )

        server = A2AServer(
            agent_id="email-agent",
            task_handler=task_handler,
            port=8001,
        )

        await server.start()
    """

    def __init__(
        self,
        agent_id: str,
        task_handler: Callable[[A2ARequest], A2AResponse] | None = None,
        task_store: TaskStore | None = None,
        host: str = "localhost",
        port: int = 8000,
    ):
        """Initialize A2A server.

        Args:
            agent_id: This agent's ID
            task_handler: Callback to handle incoming tasks (optional)
            task_store: TaskStore to queue tasks (alternative to task_handler)
            host: Server host (default: localhost)
            port: Server port (default: 8000)
        """
        self.agent_id = agent_id
        self.task_handler = task_handler
        self.task_store = task_store
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        # Setup routes
        self.app.router.add_post("/a2a/task", self.handle_task)
        self.app.router.add_get("/a2a/health", self.handle_health)
        self.app.router.add_get("/a2a/task/{task_id}", self.handle_task_status)

    async def handle_task(self, request: web.Request) -> web.Response:
        """Handle incoming A2A task request."""
        try:
            data = await request.json()
            a2a_request = A2ARequest(**data)

            logger.info(
                f"Received A2A task from {a2a_request.requester_agent_id}: "
                f"{a2a_request.task_description}"
            )

            # Option 1: Use task handler (synchronous processing)
            if self.task_handler:
                response = await self.task_handler(a2a_request)
                return web.json_response(response.model_dump())

            # Option 2: Add to task store (async processing)
            elif self.task_store:
                # Convert A2A priority to Task priority
                priority_map = {
                    "CRITICAL": Priority.CRITICAL,
                    "URGENT": Priority.URGENT,
                    "HIGH": Priority.HIGH,
                    "NORMAL": Priority.NORMAL,
                    "LOW": Priority.LOW,
                }

                task = Task(
                    description=a2a_request.task_description,
                    priority=priority_map.get(a2a_request.priority.value, Priority.NORMAL),
                    context={
                        **a2a_request.context,
                        "requester_agent_id": a2a_request.requester_agent_id,
                        "a2a_request": True,
                    },
                )

                task_id = await self.task_store.create(task)

                response = A2AResponse(
                    status=A2AStatus.PENDING,
                    task_id=task_id,
                    message=f"Task queued with ID: {task_id}",
                )

                return web.json_response(response.model_dump())

            else:
                # No handler configured
                response = A2AResponse(
                    status=A2AStatus.REJECTED,
                    error="No task handler configured",
                )
                return web.json_response(response.model_dump(), status=503)

        except Exception as e:
            logger.error(f"Error handling A2A task: {e}", exc_info=True)
            response = A2AResponse(
                status=A2AStatus.FAILED,
                error=str(e),
            )
            return web.json_response(response.model_dump(), status=500)

    async def handle_health(self, request: web.Request) -> web.Response:
        """Handle health check."""
        return web.json_response(
            {
                "status": "healthy",
                "agent_id": self.agent_id,
            }
        )

    async def handle_task_status(self, request: web.Request) -> web.Response:
        """Handle task status request."""
        task_id = request.match_info["task_id"]

        if not self.task_store:
            return web.json_response(
                {
                    "error": "Task store not configured",
                },
                status=503,
            )

        try:
            task = await self.task_store.get(task_id)

            if not task:
                return web.json_response(
                    {
                        "error": f"Task not found: {task_id}",
                    },
                    status=404,
                )

            # Convert task state to A2A status
            status_map = {
                "pending": A2AStatus.PENDING,
                "in_progress": A2AStatus.IN_PROGRESS,
                "completed": A2AStatus.COMPLETED,
                "failed": A2AStatus.FAILED,
                "cancelled": A2AStatus.REJECTED,
            }

            response = A2AResponse(
                status=status_map.get(task.state.value, A2AStatus.PENDING),
                task_id=task_id,
                result=task.result,
                error=task.error,
            )

            return web.json_response(response.model_dump())

        except Exception as e:
            logger.error(f"Error getting task status: {e}", exc_info=True)
            return web.json_response(
                {
                    "error": str(e),
                },
                status=500,
            )

    async def start(self) -> None:
        """Start the A2A server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info(f"A2A server started on http://{self.host}:{self.port}/a2a")

    async def stop(self) -> None:
        """Stop the A2A server."""
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("A2A server stopped")

    @property
    def endpoint(self) -> str:
        """Get the server's A2A endpoint URL."""
        return f"http://{self.host}:{self.port}/a2a"

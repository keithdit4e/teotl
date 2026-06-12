"""Dashboard web server for Forge agents.

Provides a unified web interface to monitor multiple agents simultaneously.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web

from teotl.primitives.missions import MissionStore
from teotl.primitives.tasks import TaskStore

logger = logging.getLogger(__name__)


class AgentMonitor:
    """Monitor for a single agent."""

    def __init__(self, agent_id: str, data_dir: Path):
        """Initialize agent monitor.

        Args:
            agent_id: Agent identifier
            data_dir: Path to agent data directory
        """
        self.agent_id = agent_id
        self.data_dir = data_dir
        self.task_store = TaskStore(data_dir / "tasks.db")
        self.mission_store = MissionStore(data_dir / "missions.db")

    def close(self):
        """Close database connections."""
        self.task_store.close()
        self.mission_store.close()


class DashboardServer:
    """Unified web dashboard server for multi-agent monitoring.

    Features:
    - Monitor multiple agents simultaneously
    - Aggregate stats across all agents
    - Filter by specific agents
    - Real-time updates via WebSocket
    - Unified activity feed
    """

    def __init__(
        self,
        agents: dict[str, Path],
        host: str = "localhost",
        port: int = 8080,
    ):
        """Initialize dashboard server.

        Args:
            agents: Dict mapping agent_id -> data_dir path
            host: Host to bind to
            port: Port to listen on
        """
        self.agents = {
            agent_id: AgentMonitor(agent_id, data_dir) for agent_id, data_dir in agents.items()
        }
        self.host = host
        self.port = port

        # WebSocket connections for real-time updates
        self.websockets: set[web.WebSocketResponse] = set()

        # Web app
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self._handle_index)
        self.app.router.add_get("/api/agents", self._handle_get_agents)
        self.app.router.add_get("/api/tasks", self._handle_get_tasks)
        self.app.router.add_get("/api/missions", self._handle_get_missions)
        self.app.router.add_get("/api/status", self._handle_get_status)
        self.app.router.add_get("/ws", self._handle_websocket)

        # Static files
        static_dir = Path(__file__).parent / "static"
        self.app.router.add_static("/static", static_dir, name="static")

    async def _handle_index(self, request: web.Request) -> web.Response:
        """Serve dashboard HTML."""
        static_dir = Path(__file__).parent / "static"
        index_path = static_dir / "index.html"

        if not index_path.exists():
            return web.Response(text="Dashboard UI not found", status=404)

        with open(index_path) as f:
            html = f.read()

        return web.Response(text=html, content_type="text/html")

    async def _handle_get_agents(self, request: web.Request) -> web.Response:
        """Get list of monitored agents."""
        agents_info = []

        for agent_id, monitor in self.agents.items():
            from teotl.primitives.tasks import TaskState

            pending = await monitor.task_store.count(TaskState.PENDING)
            completed = await monitor.task_store.count(TaskState.COMPLETED)
            failed = await monitor.task_store.count(TaskState.FAILED)

            missions = await monitor.mission_store.list_all()
            total_executions = sum(m.execution_count for m in missions)

            agents_info.append(
                {
                    "agent_id": agent_id,
                    "data_dir": str(monitor.data_dir),
                    "tasks": {
                        "pending": pending,
                        "completed": completed,
                        "failed": failed,
                    },
                    "missions": {
                        "total": len(missions),
                        "executions": total_executions,
                    },
                }
            )

        return web.json_response(agents_info)

    async def _handle_get_tasks(self, request: web.Request) -> web.Response:
        """Get tasks from all or specific agents."""
        limit = int(request.query.get("limit", "50"))
        state = request.query.get("state")  # Optional filter
        agent_filter = request.query.get("agents")  # Comma-separated agent IDs

        # Determine which agents to query
        if agent_filter:
            agent_ids = [a.strip() for a in agent_filter.split(",")]
            monitors = {aid: self.agents[aid] for aid in agent_ids if aid in self.agents}
        else:
            monitors = self.agents

        # Collect tasks from all selected agents
        all_tasks = []

        from teotl.primitives.tasks import TaskState

        for agent_id, monitor in monitors.items():
            if state:
                tasks = await monitor.task_store.list_all(state=TaskState(state), limit=limit)
            else:
                tasks = await monitor.task_store.list_all(limit=limit)

            # Add agent_id to each task
            for task in tasks:
                all_tasks.append(
                    {
                        "agent_id": agent_id,
                        "id": task.id,
                        "description": task.description,
                        "priority": task.priority.name,
                        "state": task.state.value,
                        "created_at": task.created_at.isoformat(),
                        "completed_at": task.completed_at.isoformat()
                        if task.completed_at
                        else None,
                        "result": task.result,
                        "error": task.error,
                    }
                )

        # Sort by creation time (most recent first)
        all_tasks.sort(key=lambda t: t["created_at"], reverse=True)

        # Limit total results
        return web.json_response(all_tasks[:limit])

    async def _handle_get_missions(self, request: web.Request) -> web.Response:
        """Get missions from all or specific agents."""
        agent_filter = request.query.get("agents")

        # Determine which agents to query
        if agent_filter:
            agent_ids = [a.strip() for a in agent_filter.split(",")]
            monitors = {aid: self.agents[aid] for aid in agent_ids if aid in self.agents}
        else:
            monitors = self.agents

        # Collect missions from all selected agents
        all_missions = []

        for agent_id, monitor in monitors.items():
            missions = await monitor.mission_store.list_all()

            for mission in missions:
                # Extract key data from context
                context = mission.context or {}
                execution_history = context.get("execution_history", [])
                completed_items = context.get("completed_items", [])
                skipped_items = context.get("skipped_items", [])
                full_roadmap = context.get("full_roadmap", "")

                # Calculate success rate
                if execution_history:
                    successful = sum(1 for ex in execution_history if ex.get("success"))
                    success_rate = (successful / len(execution_history)) * 100
                else:
                    success_rate = 0

                all_missions.append(
                    {
                        "agent_id": agent_id,
                        "id": mission.id,
                        "description": mission.description,
                        "state": mission.state.value,
                        "interval": mission.interval.value,
                        "execution_count": mission.execution_count,
                        "success_count": mission.success_count,
                        "failure_count": mission.failure_count,
                        "last_execution_at": mission.last_executed_at.isoformat()
                        if mission.last_executed_at
                        else None,
                        "next_execution_at": mission.next_execution_at.isoformat()
                        if mission.next_execution_at
                        else None,
                        "created_at": mission.created_at.isoformat(),
                        "tags": mission.tags,
                        # Context data for detailed view
                        "execution_history": execution_history,
                        "completed_items": completed_items,
                        "skipped_items": skipped_items,
                        "roadmap_preview": full_roadmap[:200] + "..."
                        if len(full_roadmap) > 200
                        else full_roadmap,
                        "success_rate": round(success_rate, 1),
                    }
                )

        # Sort by next execution (soonest first)
        all_missions.sort(key=lambda m: m["next_execution_at"] or "9999-12-31", reverse=False)

        return web.json_response(all_missions)

    async def _handle_get_status(self, request: web.Request) -> web.Response:
        """Get aggregate status across all agents."""
        from teotl.primitives.tasks import TaskState

        total_pending = 0
        total_completed = 0
        total_failed = 0
        total_missions = 0
        total_executions = 0

        for monitor in self.agents.values():
            total_pending += await monitor.task_store.count(TaskState.PENDING)
            total_completed += await monitor.task_store.count(TaskState.COMPLETED)
            total_failed += await monitor.task_store.count(TaskState.FAILED)

            missions = await monitor.mission_store.list_all()
            total_missions += len(missions)
            total_executions += sum(m.execution_count for m in missions)

        status = {
            "agent_count": len(self.agents),
            "agents": list(self.agents.keys()),
            "tasks": {
                "pending": total_pending,
                "completed": total_completed,
                "failed": total_failed,
            },
            "missions": {
                "total": total_missions,
                "total_executions": total_executions,
            },
            "timestamp": datetime.now().isoformat(),
        }

        return web.json_response(status)

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for real-time updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websockets.add(ws)
        logger.info(f"WebSocket client connected (total: {len(self.websockets)})")

        try:
            # Send initial status
            status = await self._get_status_dict()
            await ws.send_json({"type": "status", "data": status})

            # Keep connection alive
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Echo back for heartbeat
                    await ws.send_json({"type": "pong"})
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"WebSocket client disconnected (remaining: {len(self.websockets)})")

        return ws

    async def _get_status_dict(self) -> dict[str, Any]:
        """Get current status as dict."""
        from teotl.primitives.tasks import TaskState

        total_pending = 0
        total_completed = 0
        total_failed = 0
        total_missions = 0
        total_executions = 0

        for monitor in self.agents.values():
            total_pending += await monitor.task_store.count(TaskState.PENDING)
            total_completed += await monitor.task_store.count(TaskState.COMPLETED)
            total_failed += await monitor.task_store.count(TaskState.FAILED)

            missions = await monitor.mission_store.list_all()
            total_missions += len(missions)
            total_executions += sum(m.execution_count for m in missions)

        return {
            "agent_count": len(self.agents),
            "agents": list(self.agents.keys()),
            "tasks": {
                "pending": total_pending,
                "completed": total_completed,
                "failed": total_failed,
            },
            "missions": {
                "total": total_missions,
                "total_executions": total_executions,
            },
            "timestamp": datetime.now().isoformat(),
        }

    async def broadcast_update(self, update_type: str, data: Any):
        """Broadcast update to all WebSocket clients.

        Args:
            update_type: Type of update (task_completed, mission_executed, etc.)
            data: Update data
        """
        if not self.websockets:
            return

        message = {"type": update_type, "data": data, "timestamp": datetime.now().isoformat()}

        # Send to all connected clients
        disconnected = set()
        for ws in self.websockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.add(ws)

        # Remove disconnected clients
        self.websockets -= disconnected

    async def start(self):
        """Start the dashboard server."""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"🌐 Dashboard server started: http://{self.host}:{self.port}")
        logger.info(f"📊 Monitoring {len(self.agents)} agent(s): {', '.join(self.agents.keys())}")

        # Keep running
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()

    def close(self):
        """Close all database connections."""
        for monitor in self.agents.values():
            monitor.close()

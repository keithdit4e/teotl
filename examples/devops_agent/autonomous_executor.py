"""Custom executor for autonomous DevOps agent.

This bridges the HeartbeatDaemon to the actual issue-fixing logic.
"""

import logging
import subprocess
from pathlib import Path

from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.guardrails.policy import Policy
from teotl.primitives.guardrails.presets import PRESETS
from teotl.primitives.tasks import Task

from mcp_config import create_mcp_bridge

logger = logging.getLogger(__name__)


class DevOpsExecutor:
    """Executor that fixes GitHub issues and creates PRs."""

    def __init__(self, anthropic_key: str):
        """Initialize executor.

        Args:
            anthropic_key: Anthropic API key
        """
        self.anthropic_key = anthropic_key
        self.provider = AnthropicProvider(
            model="claude-sonnet-4-20250514",
            api_key=anthropic_key
        )
        self.mcp_bridge = create_mcp_bridge()

        # Create custom policy for DevOps agent (allows gh CLI)
        devops_policy_config = PRESETS["standard"].copy()
        devops_policy_config["bash"]["allow"].extend(["gh", "gh pr", "gh pr create"])
        self.policy = Policy(devops_policy_config)

    async def execute_task(self, task: Task) -> dict:
        """Execute a task to fix an issue.

        Args:
            task: Task with context containing repo and issue_number

        Returns:
            Dict with success status and details
        """
        repo = task.context.get("repo")
        issue_number = task.context.get("issue_number")

        if not repo or not issue_number:
            return {
                "success": False,
                "error": "Missing repo or issue_number in task context"
            }

        logger.info(f"🔧 Executing task: Fix {repo}#{issue_number}")

        try:
            # Fetch issue details
            result = subprocess.run(
                ["gh", "issue", "view", str(issue_number), "--repo", repo,
                 "--json", "number,title,body,state,labels,url"],
                capture_output=True,
                text=True,
                check=True
            )

            import json
            issue_data = json.loads(result.stdout)
            issue_data['labels'] = [label['name'] for label in issue_data.get('labels', [])]

            logger.info(f"   Issue: {issue_data['title']}")

            # Get MCP tools
            mcp_tools = self.mcp_bridge.get_tools()

            # Create agent with issue-specific instructions
            # Pass skill names (not registry object) - Agent creates its own SkillRegistry
            agent = Agent(
                provider=self.provider,
                tools=mcp_tools,
                instructions=f"""You are a DevOps automation agent fixing issue #{issue_number}.

=== ISSUE DETAILS ===
Repository: {repo}
Issue #{issue_number}: {issue_data['title']}

Description:
{issue_data['body']}

Labels: {', '.join(issue_data['labels']) if issue_data['labels'] else 'None'}
URL: {issue_data['url']}

=== YOUR OBJECTIVE ===
Fix this issue and create a pull request.

=== WORKFLOW ===

PHASE 1: SETUP
1. Create working directory: /tmp/devops-agent-{issue_number}
2. Clone repository: git clone https://github.com/{repo}.git
3. Examine repository structure

PHASE 2: INVESTIGATION
4. Identify files related to the issue
5. Read those files
6. Identify the root cause

PHASE 3: FIX
7. Create branch: git checkout -b fix/issue-{issue_number}
8. Make minimal changes to fix the issue
9. Test if possible

PHASE 4: PULL REQUEST
10. Stage changes: git add <modified-files>
11. Commit: git commit -m "fix: <description> (#{issue_number})"
12. Push: git push origin fix/issue-{issue_number}
13. Create PR:
    gh pr create --repo {repo} --base main --head fix/issue-{issue_number} --title "Fix: <description> (#{issue_number})" --body "Fixes #{issue_number}"

IMPORTANT:
- Make minimal changes only
- Always create the PR (step 13 is required)
- The gh CLI is authenticated and ready to use

Begin now!
""",
                skills=["git", "filesystem"],
                policy=self.policy,
            )

            # Run agent
            response = await agent.run(
                f"Fix issue #{issue_number} in {repo}: {issue_data['title']}"
            )

            # Check if PR was created
            pr_url = None
            if "github.com" in response.text and "/pull/" in response.text:
                import re
                match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/\d+', response.text)
                if match:
                    pr_url = match.group(0)

            return {
                "success": True,
                "issue_number": issue_number,
                "response": response.text[:500],
                "pr_url": pr_url
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch issue: {e.stderr}")
            return {
                "success": False,
                "error": f"Failed to fetch issue: {e.stderr}"
            }

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def close(self):
        """Clean up resources."""
        await self.mcp_bridge.close()

"""Read-only exploration mode for codebase understanding.

Allows agents to explore and understand a codebase before planning changes,
reducing errors and improving plan quality.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from teotl.core.agent import Agent
from teotl.core.provider import Provider

logger = logging.getLogger(__name__)


@dataclass
class ExplorationResult:
    """Result of exploration phase."""

    success: bool
    findings: list[str] = field(default_factory=list)
    questions_answered: list[str] = field(default_factory=list)
    codebase_summary: str = ""
    relevant_files: list[str] = field(default_factory=list)
    patterns_found: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    exploration_depth: str = "quick"  # quick, thorough, deep


class ExplorationMode:
    """Read-only exploration mode for understanding codebases.

    Usage:
        explorer = ExplorationMode(
            workspace_dir=Path("~/my-project"),
            provider=claude_haiku,
            exploration_depth="thorough",
        )

        # Explore before planning
        result = await explorer.explore(
            goal="Understand how authentication works",
            questions=[
                "Where is user authentication handled?",
                "What authentication method is used?",
                "Are there any security vulnerabilities?",
            ]
        )

        # Use findings to inform planning
        print(f"Found {len(result.relevant_files)} relevant files")
        print(f"Summary: {result.codebase_summary}")

    Benefits:
    - Reduces hallucinations by gathering context first
    - Identifies relevant files before planning changes
    - Answers questions about existing implementation
    - Detects patterns and anti-patterns
    - No risk of accidental modifications
    """

    def __init__(
        self,
        workspace_dir: Path,
        provider: Provider,
        exploration_depth: str = "thorough",
        max_files_to_read: int = 50,
        max_turns: int = 10,
    ):
        """Initialize exploration mode.

        Args:
            workspace_dir: Project directory to explore
            provider: LLM provider (recommend fast model like Haiku)
            exploration_depth: quick, thorough, or deep
            max_files_to_read: Maximum files to read during exploration
            max_turns: Maximum conversation turns
        """
        self.workspace_dir = Path(workspace_dir).expanduser().resolve()
        self.provider = provider
        self.exploration_depth = exploration_depth
        self.max_files_to_read = max_files_to_read
        self.max_turns = max_turns

        # Validate workspace exists
        if not self.workspace_dir.exists():
            raise ValueError(f"Workspace directory not found: {self.workspace_dir}")

        logger.info(f"Explorer initialized: {self.workspace_dir} ({exploration_depth} depth)")

    def _create_exploration_agent(self) -> Agent:
        """Create agent with read-only tools.

        Returns:
            Agent configured for exploration only
        """
        # Import read-only tools
        from teotl.core.skills import (
            list_directory,
            read_file,
            search_code,
            search_files,
        )

        # Create agent with only read operations
        agent = Agent(
            provider=self.provider,
            skills=[
                read_file,
                list_directory,
                search_files,
                search_code,
            ],
            system_prompt=self._get_explorer_system_prompt(),
        )

        return agent

    def _get_explorer_system_prompt(self) -> str:
        """Get system prompt for exploration agent.

        Returns:
            System prompt emphasizing exploration and understanding
        """
        return f"""You are a codebase explorer in READ-ONLY mode.

Your goal is to explore and understand this codebase WITHOUT making any changes.

Working Directory: {self.workspace_dir}
Exploration Depth: {self.exploration_depth}

Your capabilities:
- read_file: Read file contents
- list_directory: List directory contents
- search_files: Find files by name/pattern
- search_code: Search for code patterns

Your constraints:
- NO file modifications allowed
- NO file creation allowed
- NO file deletion allowed
- NO command execution allowed
- ONLY read and search operations

Your approach:
1. Start broad - understand project structure
2. Narrow focus - identify relevant files
3. Deep dive - read and analyze key files
4. Synthesize - answer questions with evidence

Exploration strategies by depth:
- quick: Read 5-10 key files, focus on high-level structure
- thorough: Read 20-30 files, understand implementation details
- deep: Read 40-50 files, analyze patterns and dependencies

Always cite specific files and line numbers when answering questions.
"""

    async def explore(
        self,
        goal: str,
        questions: list[str] | None = None,
        focus_areas: list[str] | None = None,
    ) -> ExplorationResult:
        """Explore codebase to understand structure and answer questions.

        Args:
            goal: High-level exploration goal
            questions: Specific questions to answer
            focus_areas: Areas to focus on (e.g., ["auth", "database"])

        Returns:
            ExplorationResult with findings and analysis

        Example:
            result = await explorer.explore(
                goal="Understand authentication implementation",
                questions=[
                    "Where is login handled?",
                    "What session management is used?",
                ],
                focus_areas=["auth", "users", "sessions"],
            )
        """
        start_time = datetime.now()

        # Build exploration prompt
        prompt = self._build_exploration_prompt(goal, questions, focus_areas)

        # Create read-only agent
        agent = self._create_exploration_agent()

        # Run exploration
        findings = []
        questions_answered = []
        relevant_files = []
        patterns_found = []
        warnings = []

        try:
            logger.info(f"Starting exploration: {goal}")

            # Multi-turn exploration conversation
            conversation = []
            for turn in range(self.max_turns):
                if turn == 0:
                    message = prompt
                else:
                    # Follow-up prompts based on previous findings
                    message = self._generate_followup_prompt(turn, findings, questions or [])

                # Run agent turn
                response = await agent.run(message, context=conversation)

                conversation.append({"role": "user", "content": message})
                conversation.append({"role": "assistant", "content": response})

                # Extract findings from response
                turn_findings = self._extract_findings(response)
                findings.extend(turn_findings)

                # Track file mentions
                file_mentions = self._extract_file_mentions(response)
                relevant_files.extend(file_mentions)

                # Check if exploration is complete
                if self._is_exploration_complete(response, questions or []):
                    logger.info(f"Exploration complete after {turn + 1} turns")
                    break

            # Generate summary
            summary = self._generate_summary(findings, relevant_files)

            # Identify patterns
            patterns_found = self._identify_patterns(findings)

            # Answer questions
            if questions:
                questions_answered = self._answer_questions(questions, findings, conversation)

            # Calculate metrics
            duration = (datetime.now() - start_time).total_seconds()

            return ExplorationResult(
                success=True,
                findings=findings,
                questions_answered=questions_answered,
                codebase_summary=summary,
                relevant_files=list(set(relevant_files)),
                patterns_found=patterns_found,
                warnings=warnings,
                duration_seconds=duration,
                exploration_depth=self.exploration_depth,
            )

        except Exception as e:
            logger.error(f"Exploration failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()

            return ExplorationResult(
                success=False,
                warnings=[f"Exploration error: {str(e)}"],
                duration_seconds=duration,
                exploration_depth=self.exploration_depth,
            )

    def _build_exploration_prompt(
        self,
        goal: str,
        questions: list[str] | None,
        focus_areas: list[str] | None,
    ) -> str:
        """Build initial exploration prompt.

        Args:
            goal: Exploration goal
            questions: Questions to answer
            focus_areas: Areas to focus on

        Returns:
            Formatted exploration prompt
        """
        prompt = f"""I need to explore this codebase to: {goal}

Working directory: {self.workspace_dir}
"""

        if questions:
            prompt += "\nQuestions to answer:\n"
            for i, q in enumerate(questions, 1):
                prompt += f"{i}. {q}\n"

        if focus_areas:
            prompt += f"\nFocus areas: {', '.join(focus_areas)}\n"

        prompt += f"""
Exploration approach ({self.exploration_depth} depth):
1. Start by listing the project structure to understand organization
2. Identify relevant files related to the goal
3. Read key files to understand implementation
4. Answer the questions with specific file and line number references
5. Provide a summary of findings

Begin exploration now.
"""

        return prompt

    def _generate_followup_prompt(
        self, turn: int, findings: list[str], questions: list[str]
    ) -> str:
        """Generate follow-up prompt for next exploration turn.

        Args:
            turn: Current turn number
            findings: Findings so far
            questions: Original questions

        Returns:
            Follow-up prompt
        """
        if turn == 1:
            return "Good start. Now dive deeper into the most relevant files you found. Read their contents and analyze implementation details."

        if turn == 2:
            return "Based on what you've learned, answer the specific questions with evidence (file paths and relevant code snippets)."

        if turn >= 3:
            unanswered = [q for q in questions if not self._is_question_answered(q, findings)]

            if unanswered:
                return f"Still need to answer: {unanswered[0]}. Find the relevant code and provide a detailed answer."

            return "Provide a final summary of your findings, including any patterns, potential issues, or recommendations."

        return "Continue exploring."

    def _extract_findings(self, response: str) -> list[str]:
        """Extract findings from agent response.

        Args:
            response: Agent response text

        Returns:
            List of findings
        """
        # Simple extraction - look for bullet points or numbered lists
        findings = []

        for line in response.split("\n"):
            line = line.strip()

            # Bullet points
            if line.startswith("- ") or line.startswith("* "):
                findings.append(line[2:].strip())

            # Numbered lists
            elif line and line[0].isdigit() and ". " in line:
                findings.append(line.split(". ", 1)[1].strip())

        return findings

    def _extract_file_mentions(self, response: str) -> list[str]:
        """Extract file path mentions from response.

        Args:
            response: Agent response text

        Returns:
            List of file paths mentioned
        """
        import re

        # Pattern for file paths
        pattern = r"(?:^|\s)([a-zA-Z0-9_\-/.]+\.(?:py|js|ts|tsx|jsx|go|rs|java|cpp|c|h|md|json|yaml|yml|toml))"

        files = re.findall(pattern, response, re.MULTILINE)
        return files

    def _is_exploration_complete(self, response: str, questions: list[str]) -> bool:
        """Check if exploration is complete.

        Args:
            response: Latest agent response
            questions: Original questions

        Returns:
            True if exploration is complete
        """
        # Check for completion indicators
        completion_indicators = [
            "exploration complete",
            "final summary",
            "in conclusion",
            "all questions answered",
        ]

        response_lower = response.lower()
        return any(indicator in response_lower for indicator in completion_indicators)

    def _is_question_answered(self, question: str, findings: list[str]) -> bool:
        """Check if a question has been answered.

        Args:
            question: Question text
            findings: Current findings

        Returns:
            True if question appears to be answered
        """
        # Simple heuristic - check if question keywords appear in findings
        question_keywords = question.lower().split()
        findings_text = " ".join(findings).lower()

        # Need at least 3 keywords from question to appear in findings
        matches = sum(1 for kw in question_keywords if kw in findings_text)
        return matches >= min(3, len(question_keywords))

    def _generate_summary(self, findings: list[str], files: list[str]) -> str:
        """Generate summary of exploration.

        Args:
            findings: All findings
            files: All relevant files

        Returns:
            Summary text
        """
        if not findings:
            return "Exploration did not yield significant findings."

        summary = f"Explored {len(files)} files and discovered:\n\n"

        # Top findings (first 5)
        for i, finding in enumerate(findings[:5], 1):
            summary += f"{i}. {finding}\n"

        if len(findings) > 5:
            summary += f"\n... and {len(findings) - 5} additional findings."

        return summary

    def _identify_patterns(self, findings: list[str]) -> list[dict]:
        """Identify patterns from findings.

        Args:
            findings: All findings

        Returns:
            List of pattern dictionaries
        """
        patterns = []

        # Simple pattern detection
        findings_text = " ".join(findings).lower()

        # Architecture patterns
        if "controller" in findings_text and "model" in findings_text:
            patterns.append({"type": "architecture", "name": "MVC", "confidence": "medium"})

        if "service" in findings_text and "repository" in findings_text:
            patterns.append(
                {
                    "type": "architecture",
                    "name": "Service/Repository",
                    "confidence": "medium",
                }
            )

        # Security patterns
        if "auth" in findings_text or "authentication" in findings_text:
            patterns.append({"type": "security", "name": "Authentication", "found": True})

        if "jwt" in findings_text or "token" in findings_text:
            patterns.append({"type": "security", "name": "Token-based auth", "found": True})

        return patterns

    def _answer_questions(
        self, questions: list[str], findings: list[str], conversation: list[dict]
    ) -> list[str]:
        """Extract answers to specific questions.

        Args:
            questions: Original questions
            findings: All findings
            conversation: Full conversation history

        Returns:
            List of answers (may be partial)
        """
        answers = []

        # Get last assistant response (should contain final answers)
        final_response = ""
        for msg in reversed(conversation):
            if msg["role"] == "assistant":
                final_response = msg["content"]
                break

        # Try to match questions to answers in final response
        for question in questions:
            # Look for question keywords in final response
            question_keywords = question.lower().split()[:3]  # First 3 words

            # Find paragraphs containing keywords
            paragraphs = final_response.split("\n\n")
            for para in paragraphs:
                para_lower = para.lower()
                if any(kw in para_lower for kw in question_keywords):
                    answers.append(f"Q: {question}\nA: {para.strip()}")
                    break
            else:
                # No direct answer found
                answers.append(f"Q: {question}\nA: [Not explicitly answered]")

        return answers

    def __repr__(self) -> str:
        """String representation."""
        return f"ExplorationMode(workspace={self.workspace_dir}, depth={self.exploration_depth})"

"""Conversation session lifecycle and short-term memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agent_lab.agent.loop import AgentLoop
from agent_lab.agent.messages import Message
from agent_lab.agent.state import AgentRunResult, utc_now_iso


@dataclass(frozen=True)
class SessionSummaryCandidate:
    session_id: str
    content: str
    source: str = "session_harness"
    summary_type: str = "session_summary_candidate"
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "content": self.content,
            "source": self.source,
            "summary_type": self.summary_type,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class SessionHarness:
    """Own one session's history while keeping AgentLoop turn-scoped."""

    def __init__(
        self,
        agent_loop: AgentLoop,
        session_id: str | None = None,
    ) -> None:
        if not isinstance(agent_loop, AgentLoop):
            raise TypeError("agent_loop must be an AgentLoop")
        self._agent_loop = agent_loop
        self._session_id = session_id or uuid4().hex
        if not isinstance(self._session_id, str) or not self._session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        self._history: list[Message] = []
        self._turn_results: list[AgentRunResult] = []
        self._summary_candidate: SessionSummaryCandidate | None = None
        self._ended = False

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def conversation_history(self) -> list[Message]:
        return list(self._history)

    def run_turn(self, user_goal: str) -> AgentRunResult:# 单次的对话
        if self._ended:
            raise RuntimeError("Session has already ended")
        result = self._agent_loop.run(
            user_goal,
            conversation_history=self._history,
            session_id=self._session_id,
        )
        self._history.extend(result.turn_messages)
        self._turn_results.append(result)
        return result

    def end_session(self) -> SessionSummaryCandidate:
        if self._summary_candidate is None:
            self._summary_candidate = self._build_summary_candidate()
        self._ended = True
        return self._summary_candidate

    def _build_summary_candidate(self) -> SessionSummaryCandidate:
        user_goals = [result.user_goal for result in self._turn_results]
        answers = [
            result.assistant_answer
            for result in self._turn_results
            if result.assistant_answer is not None
        ]
        content_lines = [
            f"Session completed with {len(self._turn_results)} turn(s).",
            "User goals:",
            *[f"- {goal}" for goal in user_goals],
            "Assistant outcomes:",
            *[f"- {answer}" for answer in answers],
        ]
        return SessionSummaryCandidate(
            session_id=self._session_id,
            content="\n".join(content_lines),
            metadata={
                "turn_count": len(self._turn_results),
                "tool_call_count": sum(
                    len(result.tool_events) for result in self._turn_results
                ),
                "persisted": False,
            },
        )

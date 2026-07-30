"""Run state and trace serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agent_lab.agent.messages import Message


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ToolEvent:
    name: str
    args: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: str = field(default_factory=utc_now_iso)
    ended_at: str | None = None

    def finish(self, result: dict[str, Any]) -> None:
        if not isinstance(result, dict):
            raise TypeError("Tool event result must be a dict")
        self.result = result
        self.ended_at = utc_now_iso()

    def fail(self, error: Exception) -> None:
        self.error = f"{type(error).__name__}: {error}"
        self.ended_at = utc_now_iso()

    def to_trace_record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "args": self.args,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


@dataclass
class AgentRunResult:
    run_id: str
    user_goal: str
    messages: list[Message]
    started_at: str
    ended_at: str | None = None
    assistant_answer: str | None = None
    error: str | None = None
    tool_events: list[ToolEvent] = field(default_factory=list) #工具调用
    reflection: str | None = None #模型回复

    @classmethod
    def start(cls, user_goal: str, messages: list[Message]) -> "AgentRunResult":
        if not isinstance(user_goal, str) or not user_goal.strip():
            raise ValueError("User goal must be a non-empty string")
        if not messages:
            raise ValueError("Run messages must not be empty")
        return cls(
            run_id=uuid4().hex,
            user_goal=user_goal,
            messages=messages,
            started_at=utc_now_iso(),
        )

    def finish(self, assistant_answer: str) -> None:
        if not isinstance(assistant_answer, str) or not assistant_answer.strip():
            raise ValueError("Assistant answer must be a non-empty string")
        self.assistant_answer = assistant_answer
        self.reflection = assistant_answer
        self.ended_at = utc_now_iso()

    def fail(self, error: Exception) -> None:
        self.error = f"{type(error).__name__}: {error}"
        self.reflection = self._build_failure_reflection()
        self.ended_at = utc_now_iso()

    def add_tool_event(self, event: ToolEvent) -> None:
        if not isinstance(event, ToolEvent):
            raise TypeError("event must be a ToolEvent")
        self.tool_events.append(event)

    def to_trace_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_goal": self.user_goal,
            "prompt_messages": [message.to_dict() for message in self.messages],
            "messages": [message.to_dict() for message in self.messages],
            "model_response": self.assistant_answer,
            "assistant_answer": self.assistant_answer,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "tool_events": [
                event.to_trace_record() for event in self.tool_events
            ],
            "reflection": self.reflection,
        }

    def _build_success_reflection(self) -> str:
        return (
            "本次运行完成了最小 agent loop：模型返回了非空回答，"
            "当前阶段尚未启用 tool、memory、evaluator。"
        )

    def _build_failure_reflection(self) -> str:
        return (
            "本次运行失败，失败原因已记录在 error 字段。"
            "下一步应优先检查模型配置、模型返回结构或输入契约。"
        )

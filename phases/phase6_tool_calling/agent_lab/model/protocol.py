"""Model client protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent_lab.agent.messages import Message


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.call_id, str) or not self.call_id.strip():
            raise ValueError("Tool call id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Tool call name must be a non-empty string")
        if not isinstance(self.arguments, dict):
            raise TypeError("Tool call arguments must be a dict")

    def to_openai_dict(self) -> dict[str, Any]:
        import json

        return {
            "id": self.call_id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, ensure_ascii=False),
            },
        }


@dataclass(frozen=True)
class ModelResponse:
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()

    def __post_init__(self) -> None:
        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("Model response content must be a string or None")
        if not self.tool_calls and (
            self.content is None or not self.content.strip()
        ):
            raise ValueError("Model response must contain content or tool calls")
        for tool_call in self.tool_calls:
            if not isinstance(tool_call, ToolCall):
                raise TypeError("Model response tool_calls must contain ToolCall objects")


class ChatModelClient(Protocol):
    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        """Return assistant content and/or requested tool calls."""

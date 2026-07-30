"""Message contracts for model interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: str = ""
    tool_calls: tuple[dict[str, Any], ...] = ()
    tool_call_id: str | None = None

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"Unsupported message role: {self.role}")
        if not isinstance(self.content, str):
            raise TypeError("Message content must be a string")
        if not self.content.strip() and not (
            self.role == "assistant" and self.tool_calls
        ):
            raise ValueError("Message content must be a non-empty string")
        if self.tool_calls and self.role != "assistant":
            raise ValueError("Only assistant messages can contain tool calls")
        if self.role == "tool":
            if not isinstance(self.tool_call_id, str) or not self.tool_call_id.strip():
                raise ValueError("Tool messages require a tool_call_id")
        elif self.tool_call_id is not None:
            raise ValueError("Only tool messages can set tool_call_id")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = list(self.tool_calls)
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        return data

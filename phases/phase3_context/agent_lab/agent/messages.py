"""Message contracts for model interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant"}:
            raise ValueError(f"Unsupported message role: {self.role}")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Message content must be a non-empty string")

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


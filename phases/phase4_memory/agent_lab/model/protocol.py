"""Model client protocol."""

from __future__ import annotations

from typing import Protocol

from agent_lab.agent.messages import Message


class ChatModelClient(Protocol):
    def complete(self, messages: list[Message]) -> str:
        """Return the assistant answer for the given messages."""


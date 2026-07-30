"""Context assembly for model prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from agent_lab.agent.messages import Message


DEFAULT_SYSTEM_INSTRUCTION = """You are a pragmatic agent.
Answer the user's goal directly and clearly.
If the task cannot be completed, explain the blocking reason."""

DEFAULT_RUNTIME_CONSTRAINTS = (
    "Do not claim to have used tools or memory unless they are present in the "
    "provided context sections."
)


@dataclass(frozen=True)
class ContextSection:
    name: str
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Context section name must be a non-empty string")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Context section content must be a non-empty string")

    def render(self) -> str:
        return f"## {self.name.strip()}\n{self.content.strip()}"


@dataclass
class ContextManager:
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION
    runtime_constraints: tuple[str, ...] = (DEFAULT_RUNTIME_CONSTRAINTS,)
    memory_sections: tuple[ContextSection, ...] = field(default_factory=tuple)
    tool_sections: tuple[ContextSection, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.system_instruction = self._validate_text(
            self.system_instruction,
            "System instruction",
        )
        self.runtime_constraints = tuple(
            self._validate_text(constraint, "Runtime constraint")
            for constraint in self.runtime_constraints
        )
        self.memory_sections = self._validate_sections(
            self.memory_sections,
            "memory_sections",
        )
        self.tool_sections = self._validate_sections(
            self.tool_sections,
            "tool_sections",
        )

    def build_messages(
        self,
        user_goal: str,
        conversation_history: Iterable[Message] | None = None,
    ) -> list[Message]:
        user_goal = self._validate_text(user_goal, "User goal")
        history = list(conversation_history or [])
        for message in history:
            if not isinstance(message, Message):
                raise TypeError("Conversation history must contain Message objects")

        return [
            Message(role="system", content=self.build_system_context()),
            *history,
            Message(role="user", content=user_goal),
        ]

    def build_system_context(self) -> str:
        sections = [
            ContextSection(
                name="system instruction",
                content=self.system_instruction,
            ),
        ]
        if self.runtime_constraints:
            sections.append(
                ContextSection(
                    name="runtime constraints",
                    content="\n".join(f"- {item}" for item in self.runtime_constraints),
                )
            )
        sections.extend(self.memory_sections)
        sections.extend(self.tool_sections)
        ##目前这里会在prompt中注入冗余，例如## memory
        return "\n\n".join(section.render() for section in sections)

    @staticmethod
    def _validate_text(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _validate_sections(
        sections: Iterable[ContextSection],
        label: str,
    ) -> tuple[ContextSection, ...]:
        validated = tuple(sections)
        for section in validated:
            if not isinstance(section, ContextSection):
                raise TypeError(f"{label} must contain ContextSection objects")
        return validated

"""Minimal agent loop."""

from __future__ import annotations

import json
from pathlib import Path

from agent_lab.agent.messages import Message
from agent_lab.agent.state import AgentRunResult
from agent_lab.context.manager import (
    ContextManager,
    ContextSection,
    DEFAULT_SYSTEM_INSTRUCTION,
)
from agent_lab.memory.jsonl_store import JsonlMemoryStore, MemoryRecord
from agent_lab.model.protocol import ChatModelClient


DEFAULT_SYSTEM_PROMPT = DEFAULT_SYSTEM_INSTRUCTION


class AgentLoop:
    def __init__(
        self,
        model_client: ChatModelClient,
        trace_file: Path | str = Path("runs") / "agent_runs.jsonl",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        context_manager: ContextManager | None = None,
        memory_store: JsonlMemoryStore | None = None,
        memory_recall_limit: int = 5,
    ) -> None:
        if context_manager is not None and not isinstance(
            context_manager,
            ContextManager,
        ):
            raise TypeError("context_manager must be a ContextManager")
        if memory_store is not None and not isinstance(memory_store, JsonlMemoryStore):
            raise TypeError("memory_store must be a JsonlMemoryStore")
        if not isinstance(memory_recall_limit, int) or memory_recall_limit <= 0:
            raise ValueError("memory_recall_limit must be a positive integer")
        self._model_client = model_client
        self._trace_file = Path(trace_file)
        self._context_manager = context_manager or ContextManager(
            system_instruction=system_prompt,
        )
        self._memory_store = memory_store
        self._memory_recall_limit = memory_recall_limit

    def run(
        self,
        user_goal: str,
        conversation_history: list[Message] | None = None,
    ) -> AgentRunResult:
        if not isinstance(user_goal, str) or not user_goal.strip():
            raise ValueError("User goal must be a non-empty string")

        context_manager = self._build_context_manager_for_run(user_goal)
        messages = context_manager.build_messages(
            user_goal=user_goal,
            conversation_history=conversation_history,
        )
        print(messages)
        result = AgentRunResult.start(user_goal=user_goal, messages=messages)
        try:
            assistant_answer = self._model_client.complete(messages)
            result.finish(assistant_answer)
        except Exception as exc:
            result.fail(exc)
            self._write_trace(result)
            raise

        self._write_trace(result)
        return result

    def _write_trace(self, result: AgentRunResult) -> None:
        self._trace_file.parent.mkdir(parents=True, exist_ok=True)
        with self._trace_file.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(result.to_trace_record(), ensure_ascii=False, sort_keys=True)
            )
            file.write("\n")

    def _build_context_manager_for_run(self, user_goal: str) -> ContextManager:
        recalled_records = self._recall_memory(user_goal)
        memory_sections = list(self._context_manager.memory_sections)
        if recalled_records:
            memory_sections.append(self._build_memory_section(recalled_records))

        return ContextManager(
            system_instruction=self._context_manager.system_instruction,
            runtime_constraints=self._context_manager.runtime_constraints,
            memory_sections=tuple(memory_sections),
            tool_sections=self._context_manager.tool_sections,
        )

    def _recall_memory(self, user_goal: str) -> list[MemoryRecord]:
        if self._memory_store is None:
            return []
        return self._memory_store.recall(
            query=user_goal,
            limit=self._memory_recall_limit,
        )

    @staticmethod
    def _build_memory_section(records: list[MemoryRecord]) -> ContextSection:
        content = "\n".join(
            f"- [{record.source}] {record.content}" for record in records
        )
        return ContextSection(name="memory", content=content)

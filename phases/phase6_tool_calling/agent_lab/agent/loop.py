"""Turn-scoped agent loop with native tool calling."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent_lab.agent.messages import Message
from agent_lab.agent.state import AgentRunResult, ToolEvent
from agent_lab.context.manager import (
    ContextManager,
    ContextSection,
    DEFAULT_SYSTEM_INSTRUCTION,
)
from agent_lab.memory.jsonl_store import JsonlMemoryStore, MemoryRecord
from agent_lab.model.protocol import ChatModelClient, ModelResponse
from agent_lab.tools import ToolRegistry


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
        tool_registry: ToolRegistry | None = None,
        max_tool_steps: int = 8,
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
        if tool_registry is not None and not isinstance(tool_registry, ToolRegistry):
            raise TypeError("tool_registry must be a ToolRegistry")
        if not isinstance(max_tool_steps, int) or max_tool_steps <= 0:
            raise ValueError("max_tool_steps must be a positive integer")
        self._model_client = model_client
        self._trace_file = Path(trace_file)
        self._context_manager = context_manager or ContextManager(
            system_instruction=system_prompt,
        )
        self._memory_store = memory_store
        self._memory_recall_limit = memory_recall_limit
        self._tool_registry = tool_registry
        self._max_tool_steps = max_tool_steps

    def run(
        self,
        user_goal: str,
        conversation_history: list[Message] | None = None,
        session_id: str | None = None,
    ) -> AgentRunResult:
        if not isinstance(user_goal, str) or not user_goal.strip():
            raise ValueError("User goal must be a non-empty string")

        context_manager = self._build_context_manager_for_run(user_goal)
        messages = context_manager.build_messages(
            user_goal=user_goal,
            conversation_history=conversation_history,
        )
        active_session_id = session_id or uuid4().hex
        result = AgentRunResult.start(
            user_goal=user_goal,
            messages=messages,
            session_id=active_session_id,
        )
        tools = (
            self._tool_registry.openai_tools()
            if self._tool_registry is not None
            else None
        )
        try:
            tool_steps = 0
            while True:
                response = self._complete(messages, tools)
                if not response.tool_calls:
                    if response.content is None:
                        raise ValueError("Final model response content is missing")
                    final_message = Message(
                        role="assistant",
                        content=response.content,
                    )
                    messages.append(final_message)
                    result.turn_messages.append(final_message)
                    result.finish(response.content)
                    break

                if tool_steps >= self._max_tool_steps:
                    raise RuntimeError(
                        f"Tool step limit exceeded: {self._max_tool_steps}"
                    )
                tool_steps += 1
                assistant_message = Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=tuple(
                        call.to_openai_dict() for call in response.tool_calls
                    ),
                )
                messages.append(assistant_message)
                result.turn_messages.append(assistant_message)

                for tool_call in response.tool_calls:
                    observation = self._execute_tool_call(
                        tool_call.call_id,
                        tool_call.name,
                        tool_call.arguments,
                        active_session_id,
                        result,
                    )
                    tool_message = Message(
                        role="tool",
                        content=json.dumps(
                            observation,
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        tool_call_id=tool_call.call_id,
                    )
                    messages.append(tool_message)
                    result.turn_messages.append(tool_message)
        except Exception as exc:
            result.fail(exc)
            self._write_trace(result)
            raise

        self._write_trace(result)
        return result

    def _complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
    ) -> ModelResponse:
        parameters = inspect.signature(self._model_client.complete).parameters.values()
        accepts_tools = any(
            parameter.name == "tools"
            or parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in parameters
        )
        if accepts_tools:
            response = self._model_client.complete(messages, tools=tools)
        else:
            response = self._model_client.complete(messages)
        if isinstance(response, str):
            return ModelResponse(content=response)
        if not isinstance(response, ModelResponse):
            raise TypeError("Model client must return ModelResponse or str")
        return response

    def _execute_tool_call(
        self,
        call_id: str,
        name: str,
        args: dict[str, Any],
        session_id: str,
        result: AgentRunResult,
    ) -> dict[str, Any]:
        effective_args = dict(args)
        if name == "memory_append":
            metadata = dict(effective_args.get("metadata", {}))
            metadata.setdefault("session_id", session_id)
            metadata.setdefault("memory_type", "explicit")
            effective_args["metadata"] = metadata

        event = ToolEvent(call_id=call_id, name=name, args=effective_args)
        result.add_tool_event(event)
        try:
            if self._tool_registry is None:
                raise RuntimeError("No tool registry is configured")
            tool_result = self._tool_registry.execute(name, effective_args)
            event.finish(tool_result)
            return {"ok": True, "result": tool_result}
        except Exception as exc:
            event.fail(exc)
            return {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

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

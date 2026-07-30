"""Minimal agent loop."""

from __future__ import annotations

import json
from pathlib import Path

from agent_lab.agent.messages import Message
from agent_lab.agent.state import AgentRunResult
from agent_lab.context.manager import ContextManager, DEFAULT_SYSTEM_INSTRUCTION
from agent_lab.model.protocol import ChatModelClient


DEFAULT_SYSTEM_PROMPT = DEFAULT_SYSTEM_INSTRUCTION


class AgentLoop:
    def __init__(
        self,
        model_client: ChatModelClient,
        trace_file: Path | str = Path("runs") / "agent_runs.jsonl",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        context_manager: ContextManager | None = None,
    ) -> None:
        if context_manager is not None and not isinstance(
            context_manager,
            ContextManager,
        ):
            raise TypeError("context_manager must be a ContextManager")
        self._model_client = model_client
        self._trace_file = Path(trace_file)
        self._context_manager = context_manager or ContextManager(
            system_instruction=system_prompt,
        )

    def run(
        self,
        user_goal: str,
        conversation_history: list[Message] | None = None,
    ) -> AgentRunResult:
        if not isinstance(user_goal, str) or not user_goal.strip():
            raise ValueError("User goal must be a non-empty string")

        messages = self._context_manager.build_messages(
            user_goal=user_goal,
            conversation_history=conversation_history,
        )
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

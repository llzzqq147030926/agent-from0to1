from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_lab.agent.loop import AgentLoop
from agent_lab.agent.messages import Message
from agent_lab.context.manager import ContextManager, ContextSection
from agent_lab.memory.jsonl_store import JsonlMemoryStore


class FakeModelClient:
    def __init__(self) -> None:
        self.messages: list[Message] | None = None

    def complete(self, messages: list[Message]) -> str:
        self.messages = messages
        return "done"


class AgentLoopTest(unittest.TestCase):
    def test_loop_uses_context_manager_for_prompt_messages(self) -> None:
        model_client = FakeModelClient()
        context_manager = ContextManager(
            system_instruction="Follow the task.",
            memory_sections=(ContextSection(name="memory", content="Known fact."),),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = AgentLoop(
                model_client=model_client,
                trace_file=Path(tmp_dir) / "trace.jsonl",
                context_manager=context_manager,
            )
            result = loop.run("Answer now.")

        self.assertEqual(result.assistant_answer, "done")
        self.assertIsNotNone(model_client.messages)
        assert model_client.messages is not None
        self.assertIn("## memory", model_client.messages[0].content)
        self.assertIn("Known fact.", model_client.messages[0].content)
        self.assertEqual(model_client.messages[-1].content, "Answer now.")

    def test_loop_recalls_memory_and_appends_reflection(self) -> None:
        model_client = FakeModelClient()

        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_store = JsonlMemoryStore(Path(tmp_dir) / "memory.jsonl")
            memory_store.append(
                content="Context 模块已经从 loop 中拆出。",
                source="agent_reflection",
                metadata={"user_goal": "实现 Context 模块"},
            )
            loop = AgentLoop(
                model_client=model_client,
                trace_file=Path(tmp_dir) / "trace.jsonl",
                memory_store=memory_store,
            )
            result = loop.run("继续实现 Context 后续模块")
            records = memory_store.load_all()

        self.assertEqual(result.assistant_answer, "done")
        self.assertIsNotNone(model_client.messages)
        assert model_client.messages is not None
        self.assertIn("## memory", model_client.messages[0].content)
        self.assertIn("Context 模块已经从 loop 中拆出。", model_client.messages[0].content)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1].source, "agent_reflection")
        self.assertEqual(records[-1].content, "done")
        self.assertEqual(records[-1].metadata["user_goal"], "继续实现 Context 后续模块")


if __name__ == "__main__":
    unittest.main()

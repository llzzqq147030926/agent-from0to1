from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_lab.agent.loop import AgentLoop
from agent_lab.agent.messages import Message
from agent_lab.harness.session import SessionHarness
from agent_lab.memory.jsonl_store import JsonlMemoryStore


class RecordingModelClient:
    def __init__(self, answers: list[str]) -> None:
        self._answers = iter(answers)
        self.calls: list[list[Message]] = []

    def complete(self, messages: list[Message]) -> str:
        self.calls.append(list(messages))
        return next(self._answers)


class SessionHarnessTest(unittest.TestCase):
    def test_session_passes_short_term_history_to_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            model = RecordingModelClient(["第一轮回答", "第二轮回答"])
            loop = AgentLoop(
                model_client=model,
                trace_file=Path(tmp_dir) / "trace.jsonl",
            )
            session = SessionHarness(loop, session_id="session-a")

            session.run_turn("第一轮问题")
            second = session.run_turn("请引用前文")

            self.assertEqual(second.session_id, "session-a")
            self.assertEqual(
                [message.role for message in model.calls[1]],
                ["system", "user", "assistant", "user"],
            )
            self.assertEqual(model.calls[1][1].content, "第一轮问题")
            self.assertEqual(model.calls[1][2].content, "第一轮回答")

    def test_new_session_does_not_inherit_raw_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            first_model = RecordingModelClient(["旧会话回答"])
            first = SessionHarness(AgentLoop(
                model_client=first_model,
                trace_file=Path(tmp_dir) / "first.jsonl",
            ))
            first.run_turn("旧会话问题")
            first.end_session()

            second_model = RecordingModelClient(["新会话回答"])
            second = SessionHarness(AgentLoop(
                model_client=second_model,
                trace_file=Path(tmp_dir) / "second.jsonl",
            ))
            second.run_turn("新会话问题")

            contents = [message.content for message in second_model.calls[0]]
            self.assertNotIn("旧会话问题", contents)
            self.assertNotIn("旧会话回答", contents)

    def test_end_session_builds_one_unpersisted_summary_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_store = JsonlMemoryStore(Path(tmp_dir) / "memory.jsonl")
            model = RecordingModelClient(["回答"])
            session = SessionHarness(
                AgentLoop(
                    model_client=model,
                    trace_file=Path(tmp_dir) / "trace.jsonl",
                    memory_store=memory_store,
                ),
                session_id="session-summary",
            )
            session.run_turn("问题")

            first = session.end_session()
            second = session.end_session()

            self.assertIs(first, second)
            self.assertEqual(first.session_id, "session-summary")
            self.assertEqual(first.summary_type, "session_summary_candidate")
            self.assertEqual(first.metadata["turn_count"], 1)
            self.assertFalse(first.metadata["persisted"])
            self.assertEqual(memory_store.load_all(), [])
            with self.assertRaisesRegex(RuntimeError, "already ended"):
                session.run_turn("不能继续")


if __name__ == "__main__":
    unittest.main()

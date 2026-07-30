from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from agent_lab.agent.loop import AgentLoop
from agent_lab.agent.messages import Message
from agent_lab.context.manager import ContextManager, ContextSection
from agent_lab.memory.jsonl_store import JsonlMemoryStore
from agent_lab.model.protocol import ModelResponse, ToolCall
from agent_lab.tools import LocalFileReadTool, MemoryAppendTool, ToolRegistry


class FakeModelClient:
    def __init__(self) -> None:
        self.messages: list[Message] | None = None

    def complete(self, messages: list[Message]) -> str:
        self.messages = messages
        return "done"


class ScriptedModelClient:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = iter(responses)
        self.tools_seen: list[list[dict[str, Any]]] = []

    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        self.tools_seen.append(list(tools or []))
        return next(self._responses)


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
        self.assertEqual(model_client.messages[-2].content, "Answer now.")
        self.assertEqual(model_client.messages[-1].content, "done")

    def test_loop_recalls_memory_without_auto_append(self) -> None:
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
        self.assertEqual(len(records), 1)
        self.assertEqual(records[-1].source, "agent_reflection")
        self.assertEqual(records[-1].content, "Context 模块已经从 loop 中拆出。")
        self.assertEqual(records[-1].metadata["user_goal"], "实现 Context 模块")

    def test_loop_executes_tool_and_returns_observation_to_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            Path(tmp_dir, "note.txt").write_text("phase6", encoding="utf-8")
            model_client = ScriptedModelClient([
                ModelResponse(tool_calls=(
                    ToolCall(
                        call_id="call-1",
                        name="read_file",
                        arguments={"path": "note.txt"},
                    ),
                )),
                ModelResponse(content="文件内容是 phase6"),
            ])
            loop = AgentLoop(
                model_client=model_client,
                trace_file=Path(tmp_dir) / "trace.jsonl",
                tool_registry=ToolRegistry([
                    LocalFileReadTool(workspace_root=tmp_dir),
                ]),
            )

            result = loop.run("读取 note.txt")

            self.assertEqual(result.assistant_answer, "文件内容是 phase6")
            self.assertEqual(len(result.tool_events), 1)
            self.assertEqual(result.tool_events[0].result["content"], "phase6")
            self.assertEqual(result.turn_messages[1].role, "assistant")
            self.assertEqual(result.turn_messages[2].role, "tool")
            observation = json.loads(result.turn_messages[2].content)
            self.assertTrue(observation["ok"])
            self.assertNotIn("name", result.turn_messages[2].to_dict())
            self.assertIn("read_file", {
                item["function"]["name"] for item in model_client.tools_seen[0]
            })

    def test_tool_failure_is_traced_and_returned_to_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_client = ScriptedModelClient([
                ModelResponse(tool_calls=(
                    ToolCall(
                        call_id="bad-call",
                        name="read_file",
                        arguments={"path": "missing.txt"},
                    ),
                )),
                ModelResponse(content="文件不存在"),
            ])
            loop = AgentLoop(
                model_client=model_client,
                trace_file=Path(tmp_dir) / "trace.jsonl",
                tool_registry=ToolRegistry([
                    LocalFileReadTool(workspace_root=tmp_dir),
                ]),
            )

            result = loop.run("读取缺失文件")

            self.assertIsNotNone(result.tool_events[0].error)
            observation = json.loads(result.turn_messages[2].content)
            self.assertFalse(observation["ok"])
            self.assertIn("FileNotFoundError", observation["error"])

    def test_loop_enforces_tool_step_limit_and_writes_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            trace_file = Path(tmp_dir) / "trace.jsonl"
            repeated_call = ModelResponse(tool_calls=(
                ToolCall(
                    call_id="repeat",
                    name="read_file",
                    arguments={"path": "missing.txt"},
                ),
            ))
            model_client = ScriptedModelClient([repeated_call, repeated_call])
            loop = AgentLoop(
                model_client=model_client,
                trace_file=trace_file,
                tool_registry=ToolRegistry([
                    LocalFileReadTool(workspace_root=tmp_dir),
                ]),
                max_tool_steps=1,
            )

            with self.assertRaisesRegex(RuntimeError, "Tool step limit exceeded"):
                loop.run("持续调用工具")

            trace = json.loads(trace_file.read_text(encoding="utf-8"))
            self.assertIn("Tool step limit exceeded", trace["error"])
            self.assertEqual(len(trace["tool_events"]), 1)

    def test_memory_append_receives_session_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_store = JsonlMemoryStore(Path(tmp_dir) / "memory.jsonl")
            model_client = ScriptedModelClient([
                ModelResponse(tool_calls=(
                    ToolCall(
                        call_id="memory-call",
                        name="memory_append",
                        arguments={
                            "content": "用户偏好严格报错",
                            "source": "user_statement",
                        },
                    ),
                )),
                ModelResponse(content="已记住"),
            ])
            loop = AgentLoop(
                model_client=model_client,
                trace_file=Path(tmp_dir) / "trace.jsonl",
                memory_store=memory_store,
                tool_registry=ToolRegistry([MemoryAppendTool(memory_store)]),
            )

            loop.run("请记住偏好", session_id="session-6")
            record = memory_store.load_all()[0]

            self.assertEqual(record.metadata["session_id"], "session-6")
            self.assertEqual(record.metadata["memory_type"], "explicit")


if __name__ == "__main__":
    unittest.main()

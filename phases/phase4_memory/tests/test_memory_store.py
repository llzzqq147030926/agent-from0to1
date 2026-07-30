from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_lab.memory.jsonl_store import JsonlMemoryStore


class JsonlMemoryStoreTest(unittest.TestCase):
    def test_append_and_recall_by_keyword(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JsonlMemoryStore(Path(tmp_dir) / "memory.jsonl")

            first = store.append(
                content="Context 模块应该只负责上下文拼装。",
                source="agent_reflection",
                metadata={"user_goal": "实现 Context 模块"},
            )
            store.append(
                content="Tool schema 后续应走原生 tools 参数。",
                source="agent_reflection",
                metadata={"user_goal": "设计 Tool 模块"},
            )

            recalled = store.recall("Context 上下文", limit=3)

        self.assertEqual(recalled, [first])

    def test_invalid_jsonl_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_file = Path(tmp_dir) / "memory.jsonl"
            memory_file.write_text("{invalid json}\n", encoding="utf-8")
            store = JsonlMemoryStore(memory_file)

            with self.assertRaises(ValueError):
                store.load_all()

    def test_records_are_written_as_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_file = Path(tmp_dir) / "memory.jsonl"
            store = JsonlMemoryStore(memory_file)

            record = store.append(
                content="保存 agent 自我反思结果。",
                source="agent_reflection",
            )

            payload = json.loads(memory_file.read_text(encoding="utf-8"))

        self.assertEqual(payload["memory_id"], record.memory_id)
        self.assertEqual(payload["content"], "保存 agent 自我反思结果。")
        self.assertEqual(payload["source"], "agent_reflection")


if __name__ == "__main__":
    unittest.main()

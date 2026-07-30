from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_lab.harness.cli import (
    build_parser,
    build_tool_context_section,
    build_tool_registry,
)
from agent_lab.memory.jsonl_store import JsonlMemoryStore


class CliTest(unittest.TestCase):
    def test_parser_includes_memory_arguments(self) -> None:
        args = build_parser().parse_args(["测试目标"])

        self.assertEqual(args.goal, "测试目标")
        self.assertEqual(args.memory_file, "memory/agent_memory.jsonl")
        self.assertEqual(args.memory_recall_limit, 5)
        self.assertEqual(args.workspace_root, ".")

    def test_parser_accepts_custom_memory_arguments(self) -> None:
        args = build_parser().parse_args([
            "测试目标",
            "--memory-file",
            "tmp/memory.jsonl",
            "--memory-recall-limit",
            "2",
            "--workspace-root",
            "workspace",
        ])

        self.assertEqual(args.memory_file, "tmp/memory.jsonl")
        self.assertEqual(args.memory_recall_limit, 2)
        self.assertEqual(args.workspace_root, "workspace")

    def test_build_tool_context_section_lists_phase5_tools(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            memory_store = JsonlMemoryStore(Path(tmp_dir) / "memory.jsonl")
            registry = build_tool_registry(memory_store, workspace_root=tmp_dir)

            section = build_tool_context_section(registry)

        self.assertEqual(section.name, "available tools")
        self.assertIn("write_file", section.content)
        self.assertIn("read_file", section.content)
        self.assertIn("bash", section.content)
        self.assertIn("fetch_url", section.content)
        self.assertIn("memory_append", section.content)


if __name__ == "__main__":
    unittest.main()

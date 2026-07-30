from __future__ import annotations

import unittest

from agent_lab.harness.cli import build_parser


class CliTest(unittest.TestCase):
    def test_parser_includes_memory_arguments(self) -> None:
        args = build_parser().parse_args(["测试目标"])

        self.assertEqual(args.goal, "测试目标")
        self.assertEqual(args.memory_file, "memory/agent_memory.jsonl")
        self.assertEqual(args.memory_recall_limit, 5)

    def test_parser_accepts_custom_memory_arguments(self) -> None:
        args = build_parser().parse_args([
            "测试目标",
            "--memory-file",
            "tmp/memory.jsonl",
            "--memory-recall-limit",
            "2",
        ])

        self.assertEqual(args.memory_file, "tmp/memory.jsonl")
        self.assertEqual(args.memory_recall_limit, 2)


if __name__ == "__main__":
    unittest.main()

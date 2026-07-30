"""Command line entry point for the minimal agent loop."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_lab.agent.loop import AgentLoop
from agent_lab.memory.jsonl_store import JsonlMemoryStore
from agent_lab.model.azure_client import AzureOpenAIChatClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the minimal agent loop.")
    parser.add_argument("goal", help="User goal to send to the agent.")
    parser.add_argument(
        "--trace-file",
        default=str(Path("runs") / "agent_runs.jsonl"),
        help="Path to the JSONL trace file.",
    )
    parser.add_argument(
        "--memory-file",
        default=str(Path("memory") / "agent_memory.jsonl"),
        help="Path to the JSONL memory file.",
    )
    parser.add_argument(
        "--memory-recall-limit",
        type=int,
        default=5,
        help="Maximum number of memory records to recall for one run.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model_client = AzureOpenAIChatClient.from_env() #初始化模型
    memory_store = JsonlMemoryStore(args.memory_file)
    loop = AgentLoop(
        model_client=model_client,
        trace_file=args.trace_file,
        memory_store=memory_store,
        memory_recall_limit=args.memory_recall_limit,
    )
    result = loop.run(args.goal)
    print(result.assistant_answer)


if __name__ == "__main__":
    main()

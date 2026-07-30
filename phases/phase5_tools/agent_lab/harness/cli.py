"""Command line entry point for the minimal agent loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_lab.agent.loop import AgentLoop
from agent_lab.context.manager import ContextManager, ContextSection
from agent_lab.memory.jsonl_store import JsonlMemoryStore
from agent_lab.model.azure_client import AzureOpenAIChatClient
from agent_lab.tools import (
    BashTool,
    FetchUrlTool,
    LocalFileReadTool,
    LocalFileWriteTool,
    MemoryAppendTool,
    ToolRegistry,
)


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
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root for local file and shell tools.",
    )
    return parser


def build_tool_registry(
    memory_store: JsonlMemoryStore,
    workspace_root: Path | str = Path("."),
) -> ToolRegistry:
    return ToolRegistry([
        LocalFileWriteTool(workspace_root=workspace_root),
        LocalFileReadTool(workspace_root=workspace_root),
        BashTool(workspace_root=workspace_root),
        FetchUrlTool(),
        MemoryAppendTool(memory_store),
    ])


def build_tool_context_section(tool_registry: ToolRegistry) -> ContextSection:
    lines = [
        "Phase 5 exposes these tools for explicit tool execution in later loops.",
        "This CLI can describe the tools, but it does not automatically execute tool calls yet.",
    ]
    for schema in tool_registry.tool_schemas():
        lines.append(f"- {schema.name}: {schema.description}")
    return ContextSection(name="available tools", content="\n".join(lines))


def main() -> None:
    args = build_parser().parse_args()
    model_client = AzureOpenAIChatClient.from_env() #初始化模型
    memory_store = JsonlMemoryStore(args.memory_file)
    tool_registry = build_tool_registry(
        memory_store=memory_store,
        workspace_root=args.workspace_root,
    )
    context_manager = ContextManager(
        tool_sections=(build_tool_context_section(tool_registry),),
    )
    loop = AgentLoop(
        model_client=model_client,
        trace_file=args.trace_file,
        context_manager=context_manager,
        memory_store=memory_store,
        memory_recall_limit=args.memory_recall_limit,
    )
    result = loop.run(args.goal)
    print(result.assistant_answer)


if __name__ == "__main__":
    main()

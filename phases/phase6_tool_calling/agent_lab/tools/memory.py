"""Memory tools."""

from __future__ import annotations

from typing import Any

from agent_lab.memory.jsonl_store import JsonlMemoryStore
from agent_lab.tools.base import ToolSchema


class MemoryAppendTool:
    def __init__(self, memory_store: JsonlMemoryStore) -> None:
        if not isinstance(memory_store, JsonlMemoryStore):
            raise TypeError("memory_store must be a JsonlMemoryStore")
        self._memory_store = memory_store

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="memory_append",
            description="Persist a durable memory record for future recall.",
            parameters={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Durable fact, decision, or lesson to remember.",
                    },
                    "source": {
                        "type": "string",
                        "description": "Short source label for this memory.",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional structured metadata for retrieval.",
                    },
                },
                "required": ["content", "source"],
            },
        )

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        record = self._memory_store.append(
            content=args["content"],
            source=args["source"],
            metadata=args.get("metadata", {}),
        )
        return {
            "memory_id": record.memory_id,
            "source": record.source,
            "created_at": record.created_at,
        }

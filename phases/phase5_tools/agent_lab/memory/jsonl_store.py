"""JSONL-backed local memory store."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MemoryRecord:
    content: str
    source: str
    memory_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.memory_id, str) or not self.memory_id.strip():
            raise ValueError("Memory id must be a non-empty string")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Memory content must be a non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Memory source must be a non-empty string")
        if not isinstance(self.created_at, str) or not self.created_at.strip():
            raise ValueError("Memory created_at must be a non-empty string")
        if not isinstance(self.metadata, dict):
            raise TypeError("Memory metadata must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "source": self.source,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryRecord":
        if not isinstance(data, dict):
            raise TypeError("Memory record must be a dict")
        return cls(
            memory_id=data["memory_id"],
            content=data["content"],
            source=data["source"],
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
        )

    def searchable_text(self) -> str:
        metadata_text = " ".join(str(value) for value in self.metadata.values())
        return f"{self.content} {metadata_text}"


class JsonlMemoryStore:
    def __init__(self, memory_file: Path | str = Path("memory") / "agent_memory.jsonl"):
        self._memory_file = Path(memory_file)

    @property
    def memory_file(self) -> Path:
        return self._memory_file

    def append(
        self,
        content: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            content=content,
            source=source,
            metadata=metadata or {},
        )
        self._memory_file.parent.mkdir(parents=True, exist_ok=True)
        with self._memory_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True))
            file.write("\n")
        return record

    def recall(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Recall query must be a non-empty string")
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Recall limit must be a positive integer")

        query_tokens = set(_tokenize(query))
        scored_records: list[tuple[int, int, MemoryRecord]] = []
        for index, record in enumerate(self.load_all()):
            record_tokens = set(_tokenize(record.searchable_text()))
            score = len(query_tokens & record_tokens)
            if score > 0:
                scored_records.append((score, index, record))

        scored_records.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in scored_records[:limit]]

    def load_all(self) -> list[MemoryRecord]:
        if not self._memory_file.exists():
            return []

        records: list[MemoryRecord] = []
        with self._memory_file.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    data = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL memory record at line {line_number}"
                    ) from exc
                records.append(MemoryRecord.from_dict(data))
        return records


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]

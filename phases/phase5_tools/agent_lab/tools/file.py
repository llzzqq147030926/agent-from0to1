"""Local file tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_lab.tools.base import ToolSchema


class LocalFileWriteTool:
    def __init__(self, workspace_root: Path | str = Path(".")) -> None:
        self._workspace_root = Path(workspace_root).resolve()

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="write_file",
            description="Write UTF-8 text to a file inside the configured workspace.",
            parameters={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path under the workspace root.",
                    },
                    "content": {
                        "type": "string",
                        "description": "UTF-8 text content to write.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["overwrite", "append"],
                        "description": "Whether to overwrite the file or append to it.",
                    },
                    "create_parents": {
                        "type": "boolean",
                        "description": "Whether missing parent directories should be created.",
                    },
                },
                "required": ["path", "content"],
            },
        )

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        target_path = self._resolve_workspace_path(args["path"])
        mode = args.get("mode", "overwrite")
        create_parents = args.get("create_parents", True)

        if create_parents:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        elif not target_path.parent.exists():
            raise FileNotFoundError(f"Parent directory does not exist: {target_path.parent}")

        file_mode = "a" if mode == "append" else "w"
        with target_path.open(file_mode, encoding="utf-8") as file:
            file.write(args["content"])

        return {
            "path": str(target_path),
            "bytes_written": len(args["content"].encode("utf-8")),
            "mode": mode,
        }

    def _resolve_workspace_path(self, path: str) -> Path:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("File path must be a non-empty string")
        candidate = Path(path)
        if candidate.is_absolute():
            raise ValueError("File path must be relative to the workspace root")

        resolved = (self._workspace_root / candidate).resolve()
        if not resolved.is_relative_to(self._workspace_root):
            raise ValueError("File path escapes the workspace root")
        return resolved


class LocalFileReadTool:
    def __init__(self, workspace_root: Path | str = Path(".")) -> None:
        self._workspace_root = Path(workspace_root).resolve()

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="read_file",
            description="Read UTF-8 text from a file inside the configured workspace.",
            parameters={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path under the workspace root.",
                    },
                },
                "required": ["path"],
            },
        )

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        target_path = self._resolve_workspace_path(args["path"])
        content = target_path.read_text(encoding="utf-8")
        return {
            "path": str(target_path),
            "content": content,
            "bytes_read": len(content.encode("utf-8")),
        }

    def _resolve_workspace_path(self, path: str) -> Path:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("File path must be a non-empty string")
        candidate = Path(path)
        if candidate.is_absolute():
            raise ValueError("File path must be relative to the workspace root")

        resolved = (self._workspace_root / candidate).resolve()
        if not resolved.is_relative_to(self._workspace_root):
            raise ValueError("File path escapes the workspace root")
        if not resolved.is_file():
            raise FileNotFoundError(f"File does not exist: {resolved}")
        return resolved

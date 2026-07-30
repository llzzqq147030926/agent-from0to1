"""Shell command tool."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from agent_lab.tools.base import ToolSchema


class BashTool:
    def __init__(self, workspace_root: Path | str = Path(".")) -> None:
        self._workspace_root = Path(workspace_root).resolve()

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="bash",
            description="Run a local bash command inside the configured workspace.",
            parameters={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command string passed to bash -lc.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional relative working directory under workspace root.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Positive command timeout in seconds.",
                    },
                },
                "required": ["command"],
            },
        )

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        cwd = self._resolve_cwd(args.get("cwd", "."))
        timeout_seconds = args.get("timeout_seconds", 30)
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        completed = subprocess.run(
            ["bash", "-lc", args["command"]],
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "cwd": str(cwd),
        }

    def _resolve_cwd(self, cwd: str) -> Path:
        if not isinstance(cwd, str) or not cwd.strip():
            raise ValueError("cwd must be a non-empty string")
        candidate = Path(cwd)
        if candidate.is_absolute():
            raise ValueError("cwd must be relative to the workspace root")

        resolved = (self._workspace_root / candidate).resolve()
        if not resolved.is_relative_to(self._workspace_root):
            raise ValueError("cwd escapes the workspace root")
        if not resolved.is_dir():
            raise FileNotFoundError(f"cwd does not exist: {resolved}")
        return resolved

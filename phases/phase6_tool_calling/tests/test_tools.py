from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
import threading
import unittest
from pathlib import Path

from agent_lab.memory.jsonl_store import JsonlMemoryStore
from agent_lab.tools import (
    BashTool,
    FetchUrlTool,
    LocalFileReadTool,
    LocalFileWriteTool,
    MemoryAppendTool,
    ToolRegistry,
)
from agent_lab.tools.base import ToolParameterError


class ToolRegistryTest(unittest.TestCase):
    def test_register_and_execute_write_file_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = ToolRegistry([
                LocalFileWriteTool(workspace_root=tmp_dir),
            ])

            result = registry.execute(
                "write_file",
                {
                    "path": "notes/result.txt",
                    "content": "hello",
                    "mode": "overwrite",
                },
            )

            written_path = Path(result["path"])
            self.assertEqual(written_path.read_text(encoding="utf-8"), "hello")
            self.assertEqual(result["bytes_written"], 5)

    def test_execute_read_file_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "notes.txt"
            path.write_text("read me", encoding="utf-8")
            registry = ToolRegistry([LocalFileReadTool(workspace_root=tmp_dir)])

            result = registry.execute("read_file", {"path": "notes.txt"})

        self.assertEqual(result["content"], "read me")
        self.assertEqual(result["bytes_read"], 7)

    def test_execute_bash_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = ToolRegistry([BashTool(workspace_root=tmp_dir)])

            result = registry.execute(
                "bash",
                {
                    "command": "printf phase5",
                    "timeout_seconds": 5,
                },
            )

        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["stdout"], "phase5")

    def test_execute_fetch_url_tool(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _StaticHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            registry = ToolRegistry([FetchUrlTool()])
            url = f"http://127.0.0.1:{server.server_port}/"

            result = registry.execute(
                "fetch_url",
                {
                    "url": url,
                    "timeout_seconds": 5,
                },
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["text"], "fetch ok")

    def test_rejects_missing_required_argument(self) -> None:
        registry = ToolRegistry([LocalFileWriteTool()])

        with self.assertRaises(ToolParameterError):
            registry.execute("write_file", {"path": "notes/result.txt"})

    def test_rejects_unknown_argument(self) -> None:
        registry = ToolRegistry([LocalFileWriteTool()])

        with self.assertRaises(ToolParameterError):
            registry.execute(
                "write_file",
                {
                    "path": "notes/result.txt",
                    "content": "hello",
                    "unexpected": True,
                },
            )

    def test_rejects_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = ToolRegistry([LocalFileWriteTool(workspace_root=tmp_dir)])

            with self.assertRaises(ValueError):
                registry.execute(
                    "write_file",
                    {
                        "path": "../outside.txt",
                        "content": "blocked",
                    },
                )

    def test_memory_append_tool_writes_explicit_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_store = JsonlMemoryStore(Path(tmp_dir) / "memory.jsonl")
            registry = ToolRegistry([MemoryAppendTool(memory_store)])

            result = registry.execute(
                "memory_append",
                {
                    "content": "Phase 5 memory writes are tool-driven.",
                    "source": "test",
                    "metadata": {"phase": "5"},
                },
            )
            records = memory_store.load_all()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].memory_id, result["memory_id"])
        self.assertEqual(records[0].content, "Phase 5 memory writes are tool-driven.")
        self.assertEqual(records[0].metadata["phase"], "5")

    def test_exports_openai_tool_schema(self) -> None:
        registry = ToolRegistry([
            LocalFileWriteTool(),
            LocalFileReadTool(),
            BashTool(),
            FetchUrlTool(),
        ])

        schemas = registry.openai_tools()
        names = {schema["function"]["name"] for schema in schemas}

        self.assertEqual(schemas[0]["type"], "function")
        self.assertEqual(names, {"write_file", "read_file", "bash", "fetch_url"})
        for schema in schemas:
            self.assertIn("parameters", schema["function"])


class _StaticHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b"fetch ok"
        self.send_response(200)
        self.send_header("content-type", "text/plain; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    unittest.main()

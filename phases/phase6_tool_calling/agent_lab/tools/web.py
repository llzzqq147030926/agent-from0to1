"""Web fetch tool."""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agent_lab.tools.base import ToolSchema

    
class FetchUrlTool:
    def __init__(self, user_agent: str = "agent-lab/phase5") -> None:
        if not isinstance(user_agent, str) or not user_agent.strip():
            raise ValueError("user_agent must be a non-empty string")
        self._user_agent = user_agent

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="fetch_url",
            description="Fetch text content from an HTTP or HTTPS URL.",
            parameters={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "HTTP or HTTPS URL to fetch.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Positive request timeout in seconds.",
                    },
                },
                "required": ["url"],
            },
        )

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        url = args["url"]
        timeout_seconds = args.get("timeout_seconds", 10)
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("url must start with http:// or https://")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        request = Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read()
                content_type = response.headers.get("content-type", "")
                charset = response.headers.get_content_charset() or "utf-8"
                text = body.decode(charset, errors="replace")
                return {
                    "url": url,
                    "status_code": response.status,
                    "content_type": content_type,
                    "text": text,
                    "bytes_read": len(body),
                }
        except HTTPError as exc:
            body = exc.read()
            text = body.decode("utf-8", errors="replace")
            return {
                "url": url,
                "status_code": exc.code,
                "content_type": exc.headers.get("content-type", ""),
                "text": text,
                "bytes_read": len(body),
            }

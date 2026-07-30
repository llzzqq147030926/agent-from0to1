"""Azure OpenAI compatible chat client."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_lab.agent.messages import Message
from agent_lab.model.protocol import ModelResponse, ToolCall

REQUIRED_ENV_VARS = (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT",
)


@dataclass(frozen=True)# 自动初始化，不支持修改
class AzureOpenAIConfig:
    api_key: str
    endpoint: str
    api_version: str
    deployment: str

    @classmethod
    def from_env(cls) -> "AzureOpenAIConfig":
        _load_dotenv()
        missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing)
            )
        return cls(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        )


def _load_dotenv(dotenv_path: Path | str = ".env") -> None:
    path = Path(dotenv_path)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


class AzureOpenAIChatClient:
    def __init__(self, config: AzureOpenAIConfig) -> None:
        self._config = config

    @classmethod
    def from_env(cls) -> "AzureOpenAIChatClient":
        return cls(AzureOpenAIConfig.from_env())

    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        if not messages:
            raise ValueError("Messages must not be empty")

        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "Python package 'openai' is required. Install it before running the agent."
            ) from exc

        client = openai.AzureOpenAI(
            api_key=self._config.api_key,
            azure_endpoint=self._config.endpoint,
            api_version=self._config.api_version,
        )
        request: dict[str, Any] = {
            "model": self._config.deployment,
            "messages": [message.to_dict() for message in messages],
        }
        if tools:
            request["tools"] = tools
        response = client.chat.completions.create(
            **request,
        )
        response_message = response.choices[0].message
        content = response_message.content
        if content is not None and not isinstance(content, str):
            raise ValueError("Model response content is invalid")

        tool_calls: list[ToolCall] = []
        for raw_call in response_message.tool_calls or []:
            try:
                arguments = json.loads(raw_call.function.arguments)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Tool call arguments are not valid JSON: {raw_call.function.name}"
                ) from exc
            if not isinstance(arguments, dict):
                raise ValueError(
                    f"Tool call arguments must be a JSON object: {raw_call.function.name}"
                )
            tool_calls.append(
                ToolCall(
                    call_id=raw_call.id,
                    name=raw_call.function.name,
                    arguments=arguments,
                )
            )
        return ModelResponse(content=content, tool_calls=tuple(tool_calls))

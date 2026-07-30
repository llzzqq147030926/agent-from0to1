"""Azure OpenAI compatible chat client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agent_lab.agent.messages import Message

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

    def complete(self, messages: list[Message]) -> str:
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
        response = client.chat.completions.create(
            model=self._config.deployment,
            messages=[message.to_dict() for message in messages],
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Model response content is empty or invalid")
        return content

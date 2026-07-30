from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_lab.model.azure_client import AzureOpenAIConfig


class AzureOpenAIConfigTest(unittest.TestCase):
    def test_from_env_loads_values_from_dotenv_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dotenv = Path(tmp_dir) / ".env"
            dotenv.write_text(
                "\n".join([
                    'AZURE_OPENAI_API_KEY="test-key"',
                    "AZURE_OPENAI_ENDPOINT=https://example.com/openai",
                    "AZURE_OPENAI_API_VERSION=2024-03-01-preview",
                    "AZURE_OPENAI_DEPLOYMENT=test-deployment",
                ]),
                encoding="utf-8",
            )
            previous_cwd = Path.cwd()
            try:
                os.chdir(tmp_dir)
                with patch.dict(os.environ, {}, clear=True):
                    config = AzureOpenAIConfig.from_env()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.endpoint, "https://example.com/openai")
        self.assertEqual(config.api_version, "2024-03-01-preview")
        self.assertEqual(config.deployment, "test-deployment")

    def test_from_env_requires_all_fields(self) -> None:
        with patch.dict(
            os.environ,
            {"AZURE_OPENAI_API_KEY": "test-key"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT",
            ):
                AzureOpenAIConfig.from_env()


if __name__ == "__main__":
    unittest.main()

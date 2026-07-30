from __future__ import annotations

import unittest

from agent_lab.agent.messages import Message
from agent_lab.context.manager import ContextManager, ContextSection


class ContextManagerTest(unittest.TestCase):
    def test_build_messages_includes_context_sections_and_user_goal(self) -> None:
        manager = ContextManager(
            system_instruction="Follow the task.",
            runtime_constraints=("Stay factual.",),
            memory_sections=(
                ContextSection(name="memory", content="User prefers concise answers."),
            ),
            tool_sections=(
                ContextSection(name="tool descriptions", content="No tools available."),
            ),
        )

        messages = manager.build_messages("Summarize the design.")

        self.assertEqual([message.role for message in messages], ["system", "user"])
        self.assertIn("## system instruction", messages[0].content)
        self.assertIn("Follow the task.", messages[0].content)
        self.assertIn("## runtime constraints", messages[0].content)
        self.assertIn("- Stay factual.", messages[0].content)
        self.assertIn("## memory", messages[0].content)
        self.assertIn("User prefers concise answers.", messages[0].content)
        self.assertIn("## tool descriptions", messages[0].content)
        self.assertEqual(messages[1].content, "Summarize the design.")

    def test_build_messages_preserves_conversation_history(self) -> None:
        manager = ContextManager(system_instruction="Follow the task.")
        history = [
            Message(role="user", content="First question"),
            Message(role="assistant", content="First answer"),
        ]

        messages = manager.build_messages(
            "Second question",
            conversation_history=history,
        )

        self.assertEqual([message.role for message in messages], [
            "system",
            "user",
            "assistant",
            "user",
        ])
        self.assertEqual(messages[1:3], history)
        self.assertEqual(messages[-1].content, "Second question")

    def test_empty_runtime_constraints_are_omitted(self) -> None:
        manager = ContextManager(
            system_instruction="Follow the task.",
            runtime_constraints=(),
        )

        system_context = manager.build_system_context()

        self.assertIn("## system instruction", system_context)
        self.assertNotIn("## runtime constraints", system_context)

    def test_rejects_empty_section_content(self) -> None:
        with self.assertRaises(ValueError):
            ContextSection(name="memory", content=" ")


if __name__ == "__main__":
    unittest.main()

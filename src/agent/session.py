"""Session management and conversational memory for Bedrock AgentCore."""

import uuid
from typing import Any


class SessionMemory:
    """Manages multi-turn conversation messages formatted for Bedrock Converse API."""

    def __init__(self, session_id: str | None = None, max_turns: int = 30):
        self.session_id = session_id or str(uuid.uuid4())
        self.max_turns = max_turns
        self.messages: list[dict[str, Any]] = []

    def add_user_message(self, text: str) -> None:
        """Append a user text message to the history."""
        self.messages.append({
            "role": "user",
            "content": [{"text": text}]
        })
        self._trim_if_needed()

    def add_assistant_message(self, content_blocks: list[dict[str, Any]]) -> None:
        """Append an assistant response block (text or toolUse)."""
        self.messages.append({
            "role": "assistant",
            "content": content_blocks
        })
        self._trim_if_needed()

    def add_tool_result(
        self,
        tool_use_id: str,
        result_content: Any,
        status: str = "success"
    ) -> None:
        """Append toolResult content in response to a toolUse request."""
        # Wrap result into standard Bedrock JSON or text content
        if isinstance(result_content, dict):
            content = [{"json": result_content}]
        else:
            content = [{"text": str(result_content)}]

        self.messages.append({
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": content,
                        "status": status
                    }
                }
            ]
        })
        self._trim_if_needed()

    def get_messages(self) -> list[dict[str, Any]]:
        """Return the current list of messages."""
        return self.messages

    def clear(self) -> None:
        """Clear all conversation history."""
        self.messages = []

    def _trim_if_needed(self) -> None:
        """Ensure message history does not exceed max_turns."""
        if len(self.messages) > (self.max_turns * 2):
            # Keep recent messages while ensuring role alternation validity
            self.messages = self.messages[-(self.max_turns * 2):]
            # Ensure the trimmed list starts with a user turn if possible
            while self.messages and self.messages[0]["role"] != "user":
                self.messages.pop(0)

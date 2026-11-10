from typing import Any
from .base import Memory


class ShortMemory(Memory):

    def __init__(self, system_prompt: str | None = None, max_turns: int = 10):
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.messages: list[Any] = []

        if self.system_prompt:
            self.messages.append({
                "role": "system",
                "content": self.system_prompt
            })

    @staticmethod
    def _is_user_message(message: Any) -> bool:
        if isinstance(message, dict):
            return message.get("role") == "user"
        return getattr(message, "type", None) == "human"

    def _trim(self) -> None:
        if not self.max_turns or self.max_turns <= 0:
            return

        user_indices = [
            i for i, msg in enumerate(self.messages)
            if self._is_user_message(msg)
        ]

        if len(user_indices) > self.max_turns:
            cutoff_index = user_indices[-self.max_turns]
            system_prefix = [self.messages[0]] if self.system_prompt else []
            self.messages = system_prefix + self.messages[cutoff_index:]

    def add(self, message: Any) -> None:
        self.messages.append(message)
        self._trim()

    def get(self) -> list[Any]:
        return self.messages

    def clear(self) -> None:
        self.messages.clear()
        if self.system_prompt:
            self.messages.append({
                "role": "system",
                "content": self.system_prompt
            })

    def set_system_prompt(self, system_prompt: str | None) -> None:
        """Update the system prompt without losing conversation history."""
        self.system_prompt = system_prompt
        has_system = bool(
            self.messages
            and isinstance(self.messages[0], dict)
            and self.messages[0].get("role") == "system"
        )
        if has_system:
            if system_prompt:
                self.messages[0] = {"role": "system", "content": system_prompt}
            else:
                self.messages.pop(0)
        elif system_prompt:
            self.messages.insert(0, {"role": "system", "content": system_prompt})

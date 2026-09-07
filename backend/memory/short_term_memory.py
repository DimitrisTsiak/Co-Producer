from typing import Any
from .base import Memory

class ShortMemory(Memory):

    def __init__(self, system_prompt: str | None = None):
        self.messages: list[Any] = []

        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })

    def add(self, message: Any) -> None:
        self.messages.append(message)

    def get(self) -> list[Any]:
        return self.messages

    def clear(self) -> None:
        self.messages.clear()

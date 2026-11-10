from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):

    @abstractmethod
    def add(self, message: Any) -> None:
        """Add a message to memory."""
        pass

    @abstractmethod
    def get(self) -> list[Any]:
        """Return the conversation history."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the conversation history."""
        pass

    @abstractmethod
    def set_system_prompt(self, system_prompt: str | None) -> None:
        """Update the system prompt without losing conversation history."""
        pass

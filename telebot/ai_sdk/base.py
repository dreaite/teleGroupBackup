from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base interface for AI providers used by the backup summarizer."""

    @abstractmethod
    async def generate_summary(self, content: str, prompt: str | None = None) -> str:
        """Generate a summary from the given content."""
        pass

import logging

from openai import AsyncOpenAI

from .base import AIProvider
from .prompts import DEFAULT_SUMMARY_PROMPT


class OpenAIClient(AIProvider):
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "gpt-3.5-turbo"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.logger = logging.getLogger(__name__)

    async def generate_summary(self, content: str, prompt: str | None = None) -> str:
        system_prompt = prompt if prompt else DEFAULT_SUMMARY_PROMPT

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"OpenAI API Error: {e}")
            return f"Error generating summary: {e}"

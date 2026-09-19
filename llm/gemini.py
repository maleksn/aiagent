from typing import Any
from google import genai
from google.genai import types
from config import config
from llm.base import BaseLLMClient


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini LLM Client implementation."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or config.api_key
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing! Set it in your environment or .env file."
            )
        self.model = model or config.default_model
        self.client = genai.Client(api_key=self.api_key)

    def generate_content(
        self,
        contents: list[types.Content],
        tools: list[types.Tool] | None = None,
        system_instruction: str = "",
        temperature: float = 0.0,
    ) -> Any:
        tool_list = tools if tools is not None else []
        config_args = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            temperature=temperature,
        )
        if tool_list:
            config_args.tools = tool_list

        return self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config_args,
        )

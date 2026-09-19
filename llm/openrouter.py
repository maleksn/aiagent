import json
import time
from typing import Any
from openai import OpenAI, APIConnectionError, RateLimitError, InternalServerError, APIStatusError
import config
from llm.base import BaseLLMClient, LLMResponse, ToolCall



class OpenRouterLLMClient(BaseLLMClient):
    """
    OpenRouter LLM Client using the OpenAI-compatible API.
    Supports multi-turn conversations, tool calling, and token usage tracking.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or config.config.api_key
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is missing! Set it in your environment or .env file."
            )
        self.model = config._normalize_model(model or config.config.default_model)
        self.base_url = base_url or config.config.openrouter_base_url
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/aiagent",
                "X-Title": "AIAgent",
            },
        )

    def generate_content(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_instruction: str = "",
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        full_messages: list[dict[str, Any]] = []

        if system_instruction and not any(m.get("role") == "system" for m in messages):
            full_messages.append({"role": "system", "content": system_instruction})

        full_messages.extend(messages)

        limit_tokens = max_tokens or config.config.max_tokens

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": limit_tokens,
        }

        if tools:
            create_kwargs["tools"] = tools

        last_exception: Exception | None = None
        response = None
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(**create_kwargs)
                break
            except (APIConnectionError, RateLimitError, InternalServerError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (2 ** attempt))
                else:
                    raise
            except APIStatusError as e:
                last_exception = e
                if e.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(1.0 * (2 ** attempt))
                else:
                    raise

        if response is None and last_exception:
            raise last_exception

        choice = response.choices[0]

        message = choice.message

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                fn_name = tc.function.name
                raw_args = tc.function.arguments
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args) if raw_args.strip() else {}
                    except json.JSONDecodeError:
                        args = {"raw_arguments": raw_args}
                elif isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = {}

                tool_calls.append(
                    ToolCall(
                        id=tc.id or "",
                        name=fn_name or "",
                        args=args,
                    )
                )

        prompt_tokens = (
            response.usage.prompt_tokens
            if response.usage and response.usage.prompt_tokens
            else 0
        )
        completion_tokens = (
            response.usage.completion_tokens
            if response.usage and response.usage.completion_tokens
            else 0
        )

        return LLMResponse(
            text=message.content,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw=response,
        )

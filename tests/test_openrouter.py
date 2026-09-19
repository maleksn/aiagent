import json
from unittest.mock import MagicMock, patch
import pytest
from llm.base import ToolCall, LLMResponse


def test_openrouter_missing_api_key(monkeypatch):
    from config import Config
    monkeypatch.setattr("config.config", Config(api_key=None))

    from llm.openrouter import OpenRouterLLMClient
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is missing"):
        OpenRouterLLMClient(api_key=None)


def test_openrouter_direct_text_generation():
    from llm.openrouter import OpenRouterLLMClient

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello there!"
    mock_choice.message.tool_calls = None

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 15
    mock_completion.usage.completion_tokens = 5
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("llm.openrouter.OpenAI", return_value=mock_client):
        client = OpenRouterLLMClient(api_key="test-key", model="test-model")
        messages = [{"role": "user", "content": "Hi"}]
        response = client.generate_content(
            messages=messages,
            system_instruction="You are a helpful assistant.",
            temperature=0.7,
        )

        assert isinstance(response, LLMResponse)
        assert response.text == "Hello there!"
        assert response.tool_calls == []
        assert response.prompt_tokens == 15
        assert response.completion_tokens == 5

        # Verify call arguments
        mock_client.chat.completions.create.assert_called_once()
        kwargs = mock_client.chat.completions.create.call_args[1]
        assert kwargs["model"] == "test-model"
        assert kwargs["temperature"] == 0.7
        # System instruction should be prepended
        assert kwargs["messages"][0] == {"role": "system", "content": "You are a helpful assistant."}
        assert kwargs["messages"][1] == {"role": "user", "content": "Hi"}


def test_openrouter_tool_call_parsing():
    from llm.openrouter import OpenRouterLLMClient

    mock_client = MagicMock()
    mock_tc = MagicMock()
    mock_tc.id = "call_abc123"
    mock_tc.function.name = "write_file"
    mock_tc.function.arguments = json.dumps({"file_path": "foo.py", "content": "print(1)"})

    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tc]

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 30
    mock_completion.usage.completion_tokens = 20
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("llm.openrouter.OpenAI", return_value=mock_client):
        client = OpenRouterLLMClient(api_key="test-key")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Writes a file",
                    "parameters": {"type": "object"},
                },
            }
        ]
        response = client.generate_content(
            messages=[{"role": "user", "content": "Write foo.py"}],
            tools=tools,
        )

        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
        tc = response.tool_calls[0]
        assert isinstance(tc, ToolCall)
        assert tc.id == "call_abc123"
        assert tc.name == "write_file"
        assert tc.args == {"file_path": "foo.py", "content": "print(1)"}

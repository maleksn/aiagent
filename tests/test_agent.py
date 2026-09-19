from typing import Any
from unittest.mock import MagicMock
from google.genai import types
from agent.core import Agent
from llm.base import BaseLLMClient
from tools.registry import ToolRegistry
from tools.base import BaseTool


class MockLLMClient(BaseLLMClient):
    """Mock LLM client to simulate conversational turns and tool calls."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.call_count = 0

    def generate_content(
        self,
        contents: list[types.Content],
        tools: list[types.Tool] | None = None,
        system_instruction: str = "",
        temperature: float = 0.0,
    ) -> Any:
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


def test_agent_direct_response():
    mock_resp = MagicMock()
    mock_resp.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)
    mock_resp.candidates = [MagicMock(content=types.Content(role="model", parts=[types.Part(text="Done!")]))]
    mock_resp.function_calls = None
    mock_resp.text = "Done!"

    client = MockLLMClient([mock_resp])
    agent = Agent(llm_client=client, max_iterations=3)

    result = agent.run("Hello")
    assert result.success is True
    assert result.final_text == "Done!"
    assert result.total_iterations == 1
    assert result.total_prompt_tokens == 10
    assert result.total_response_tokens == 5


def test_agent_tool_calling_flow():
    # Turn 1: LLM requests a tool call
    call_mock = MagicMock()
    call_mock.name = "echo_tool"
    call_mock.args = {"message": "hello"}

    turn1_resp = MagicMock()
    turn1_resp.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)
    turn1_resp.candidates = [MagicMock(content=types.Content(role="model", parts=[]))]
    turn1_resp.function_calls = [call_mock]
    turn1_resp.text = None

    # Turn 2: LLM finishes after seeing tool response
    turn2_resp = MagicMock()
    turn2_resp.usage_metadata = MagicMock(prompt_token_count=15, candidates_token_count=8)
    turn2_resp.candidates = [MagicMock(content=types.Content(role="model", parts=[types.Part(text="Final answer")]))]
    turn2_resp.function_calls = None
    turn2_resp.text = "Final answer"

    registry = ToolRegistry()

    class EchoTool(BaseTool):
        name = "echo_tool"
        description = "Echoes input"
        parameters_schema = types.Schema(type=types.Type.OBJECT)

        def execute(self, **kwargs) -> str:
            return f"Echo: {kwargs.get('message')}"

    registry.register(EchoTool)

    client = MockLLMClient([turn1_resp, turn2_resp])
    agent = Agent(llm_client=client, registry=registry, max_iterations=3)

    result = agent.run("Run echo")
    assert result.success is True
    assert result.final_text == "Final answer"
    assert result.total_iterations == 2


def test_agent_iteration_limit():
    # An infinite tool call loop
    call_mock = MagicMock()
    call_mock.name = "loop_tool"
    call_mock.args = {}

    loop_resp = MagicMock()
    loop_resp.usage_metadata = MagicMock(prompt_token_count=5, candidates_token_count=5)
    loop_resp.candidates = [MagicMock(content=types.Content(role="model", parts=[]))]
    loop_resp.function_calls = [call_mock]
    loop_resp.text = None

    registry = ToolRegistry()

    class LoopTool(BaseTool):
        name = "loop_tool"
        description = "loops"
        parameters_schema = types.Schema(type=types.Type.OBJECT)

        def execute(self, **kwargs) -> str:
            return "again"

    registry.register(LoopTool)

    client = MockLLMClient([loop_resp, loop_resp, loop_resp])
    agent = Agent(llm_client=client, registry=registry, max_iterations=2)

    result = agent.run("Loop forever")
    assert result.success is False
    assert "maximum iteration limit" in (result.error or "")

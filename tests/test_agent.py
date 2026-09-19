from typing import Any
from agent.core import Agent
from llm.base import BaseLLMClient, LLMResponse, ToolCall
from tools.registry import ToolRegistry
from tools.base import BaseTool


class MockLLMClient(BaseLLMClient):
    """Mock LLM client to simulate conversational turns and tool calls."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.call_count = 0

    def generate_content(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_instruction: str = "",
        temperature: float = 0.0,
    ) -> LLMResponse:
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


def test_agent_direct_response():
    mock_resp = LLMResponse(
        text="Done!",
        tool_calls=[],
        prompt_tokens=10,
        completion_tokens=5,
    )

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
    turn1_resp = LLMResponse(
        text=None,
        tool_calls=[
            ToolCall(
                id="call_echo_1",
                name="echo_tool",
                args={"message": "hello"},
            )
        ],
        prompt_tokens=10,
        completion_tokens=5,
    )

    # Turn 2: LLM finishes after seeing tool response
    turn2_resp = LLMResponse(
        text="Final answer",
        tool_calls=[],
        prompt_tokens=15,
        completion_tokens=8,
    )

    registry = ToolRegistry()

    class EchoTool(BaseTool):
        name = "echo_tool"
        description = "Echoes input"
        parameters_schema = {"type": "object"}

        def execute(self, **kwargs) -> str:
            return f"Echo: {kwargs.get('message')}"

    registry.register(EchoTool)

    client = MockLLMClient([turn1_resp, turn2_resp])
    agent = Agent(llm_client=client, registry=registry, max_iterations=3)

    result = agent.run("Run echo")
    assert result.success is True
    assert result.final_text == "Final answer"
    assert result.total_iterations == 2
    assert result.total_prompt_tokens == 25
    assert result.total_response_tokens == 13


def test_agent_iteration_limit():
    # An infinite tool call loop
    loop_resp = LLMResponse(
        text=None,
        tool_calls=[
            ToolCall(
                id="call_loop_1",
                name="loop_tool",
                args={},
            )
        ],
        prompt_tokens=5,
        completion_tokens=5,
    )

    registry = ToolRegistry()

    class LoopTool(BaseTool):
        name = "loop_tool"
        description = "loops"
        parameters_schema = {"type": "object"}

        def execute(self, **kwargs) -> str:
            return "again"

    registry.register(LoopTool)

    client = MockLLMClient([loop_resp, loop_resp, loop_resp])
    agent = Agent(llm_client=client, registry=registry, max_iterations=2)

    result = agent.run("Loop forever")
    assert result.success is False
    assert "maximum iteration limit" in (result.error or "")
    assert result.total_iterations == 2

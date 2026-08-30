"""Provider-agnostic seam between the orchestrator and whichever LLM API key
the deployment ends up using. Anthropic is implemented end-to-end since it's
the most likely choice; the OpenAI adapter is stubbed (same interface, not
wired up) because that choice wasn't made yet -- see DECISION_LOG.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    raw_assistant_turn: Any = None  # provider-native message, needed to continue the conversation


class LLMAdapter(Protocol):
    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...

    def tool_result_message(self, tool_call: ToolCall, result: dict) -> dict: ...


class AnthropicAdapter:
    def __init__(self, model: str = "claude-sonnet-5", api_key: str | None = None):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2000,
            system=system,
            messages=messages,
            tools=tools,
        )
        text_parts = [block.text for block in response.content if block.type == "text"]
        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]
        return LLMResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_assistant_turn={"role": "assistant", "content": response.content},
        )

    def tool_result_message(self, tool_call: ToolCall, result: dict) -> dict:
        import json

        return {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_call.id, "content": json.dumps(result)}],
        }


class OpenAIAdapter:
    """Not implemented yet -- LLM provider choice was left open. The interface
    matches AnthropicAdapter so swapping providers is a one-line change in
    src/config.py once someone finishes this and provides an OPENAI_API_KEY."""

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        raise NotImplementedError(
            "OpenAIAdapter is a stub. Implement chat()/tool_result_message() against the "
            "OpenAI chat.completions (or responses) API with tool calling, matching the "
            "LLMAdapter protocol, then wire LLM_PROVIDER=openai in src/config.py."
        )


def get_llm_adapter(provider: str) -> LLMAdapter:
    if provider == "anthropic":
        return AnthropicAdapter()
    if provider == "openai":
        return OpenAIAdapter()
    raise ValueError(f"Unknown LLM provider '{provider}'")

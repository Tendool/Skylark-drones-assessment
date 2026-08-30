"""Provider-agnostic seam between the orchestrator and whichever LLM API key
the deployment ends up using. Anthropic and Groq are implemented end-to-end;
Groq is a genuinely-free-tier option (OpenAI-compatible API), used here as
`OpenAICompatibleAdapter` with Groq's endpoint/model -- the same base class
also gives a real (non-stub) OpenAI adapter for free. See DECISION_LOG.md.
"""
from __future__ import annotations

import json
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


def _relax_optional_params_to_nullable(schema: dict) -> dict:
    """Claude omits optional parameters it doesn't need; Groq's stricter
    function-calling validation instead explicitly passes `null` for them --
    and then rejects its own call if the declared schema doesn't allow null
    on that property (found by testing live against Groq, not from docs). No
    tool in this project actually requires None to mean something different
    from "omitted", so every non-required property is widened to accept null."""
    schema = dict(schema)
    properties = schema.get("properties")
    if not properties:
        return schema
    required = set(schema.get("required", []))
    new_properties = {}
    for name, prop in properties.items():
        if name in required or "type" not in prop:
            new_properties[name] = prop
            continue
        prop = dict(prop)
        prop["type"] = [prop["type"], "null"] if isinstance(prop["type"], str) else prop["type"]
        new_properties[name] = prop
    schema["properties"] = new_properties
    return schema


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """TOOL_SCHEMAS (src/agent/tools.py) is written in Anthropic's tool-schema
    shape ({name, description, input_schema}); OpenAI-compatible chat
    completions APIs (OpenAI itself, Groq, etc.) want the function-calling
    shape instead."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": _relax_optional_params_to_nullable(t["input_schema"]),
            },
        }
        for t in tools
    ]


class OpenAICompatibleAdapter:
    """Works against any OpenAI-compatible chat-completions endpoint (real
    OpenAI, or a compatible provider like Groq via `base_url`). Verified
    against a live Groq call (see DECISION_LOG.md) -- request/response shapes
    below match what Groq's `openai/gpt-oss-120b` actually returns, not just
    what the docs say."""

    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=2000,
            messages=[{"role": "system", "content": system}, *messages],
            tools=_to_openai_tools(tools),
        )
        message = response.choices[0].message

        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (message.tool_calls or [])
        ]
        raw_assistant_turn = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            # Groq's strict OpenAI-compatible validation rejects an explicit
            # `tool_calls: null` on a plain-text assistant turn -- the key
            # must be entirely absent rather than null (unlike real OpenAI,
            # which accepts either). Only include it when there's something
            # to include.
            raw_assistant_turn["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message.tool_calls
            ]
        return LLMResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            raw_assistant_turn=raw_assistant_turn,
        )

    def tool_result_message(self, tool_call: ToolCall, result: dict) -> dict:
        return {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}


class OpenAIAdapter(OpenAICompatibleAdapter):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        super().__init__(model=model, api_key=api_key or os.environ["OPENAI_API_KEY"])


class GroqAdapter(OpenAICompatibleAdapter):
    """groq.com -- genuinely free tier (no card), OpenAI-compatible API.
    openai/gpt-oss-120b is Groq's current recommended model for tool-heavy
    use cases (llama-3.3-70b-versatile, used during earlier development, was
    deprecated by Groq in June 2026)."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        super().__init__(
            model=model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            api_key=api_key or os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )


def get_llm_adapter(provider: str) -> LLMAdapter:
    if provider == "anthropic":
        return AnthropicAdapter()
    if provider == "openai":
        return OpenAIAdapter()
    if provider == "groq":
        return GroqAdapter()
    raise ValueError(f"Unknown LLM provider '{provider}'")

"""Regression tests for bugs found while live-testing GroqAdapter against
the real Groq API (see DECISION_LOG.md): Groq's stricter OpenAI-compatible
validation (a) rejects an explicit `tool_calls: null` on a plain-text
assistant turn and (b) rejects `null` for an optional parameter unless the
schema itself declares the property nullable."""
from types import SimpleNamespace

from src.agent.llm_adapter import OpenAICompatibleAdapter, _relax_optional_params_to_nullable, _to_openai_tools
from src.agent.tools import TOOL_SCHEMAS


def _fake_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _fake_tool_call(call_id, name, arguments_json):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments_json))


class _FakeCompletions:
    def __init__(self, message):
        self._message = message

    def create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=self._message)])


class _FakeClient:
    def __init__(self, message):
        self.chat = SimpleNamespace(completions=_FakeCompletions(message))


def _adapter_with_fake_response(message) -> OpenAICompatibleAdapter:
    adapter = OpenAICompatibleAdapter.__new__(OpenAICompatibleAdapter)
    adapter._client = _FakeClient(message)
    adapter._model = "fake-model"
    return adapter


def test_plain_text_turn_omits_tool_calls_key_entirely():
    adapter = _adapter_with_fake_response(_fake_message(content="hello", tool_calls=None))
    response = adapter.chat("system", [], [])

    assert "tool_calls" not in response.raw_assistant_turn
    assert response.stop_reason == "end_turn"


def test_tool_call_turn_includes_tool_calls_key():
    tc = _fake_tool_call("call_1", "get_data_quality_report", "{}")
    adapter = _adapter_with_fake_response(_fake_message(content=None, tool_calls=[tc]))
    response = adapter.chat("system", [], [])

    assert response.raw_assistant_turn["tool_calls"] == [
        {"id": "call_1", "type": "function", "function": {"name": "get_data_quality_report", "arguments": "{}"}}
    ]
    assert response.stop_reason == "tool_use"
    assert response.tool_calls[0].name == "get_data_quality_report"


def test_relax_optional_params_widens_type_to_include_null():
    schema = {
        "type": "object",
        "properties": {"sector": {"type": "string"}, "limit": {"type": "integer"}},
        "required": ["limit"],
    }
    relaxed = _relax_optional_params_to_nullable(schema)

    assert relaxed["properties"]["sector"]["type"] == ["string", "null"]
    assert relaxed["properties"]["limit"]["type"] == "integer"  # required params untouched


def test_all_real_tool_schemas_convert_without_error():
    openai_tools = _to_openai_tools(TOOL_SCHEMAS)
    assert len(openai_tools) == len(TOOL_SCHEMAS)
    for tool in openai_tools:
        assert tool["type"] == "function"
        required = set(tool["function"]["parameters"].get("required", []))
        for name, prop in tool["function"]["parameters"].get("properties", {}).items():
            if name not in required and "type" in prop:
                assert "null" in prop["type"], f"{tool['function']['name']}.{name} should accept null"

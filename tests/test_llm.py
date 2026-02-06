"""Tests for LLM client abstraction."""

import json
import pytest
from trendbot.llm import MockLLMClient, _extract_json


class TestExtractJson:
    def test_direct_json(self):
        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_json_in_plain_code_block(self):
        text = '```\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_json_embedded_in_text(self):
        text = 'Here is the result: {"key": "value"} and more text'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_nested_json(self):
        data = {"outer": {"inner": [1, 2, 3]}}
        text = f"Result: {json.dumps(data)}"
        result = _extract_json(text)
        assert result == data

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            _extract_json("no json here at all")

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            _extract_json("{invalid json}")


class TestMockLLMClient:
    @pytest.mark.asyncio
    async def test_generate_text(self):
        client = MockLLMClient()
        result = await client.generate_text("Hello")
        assert "MockLLM" in result

    @pytest.mark.asyncio
    async def test_generate_json(self):
        client = MockLLMClient()
        result = await client.generate_json("Hello")
        assert result["mock"] is True

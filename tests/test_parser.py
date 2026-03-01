import json
import pytest
from llm_pricing.parser import build_prompt, parse_llm_response
from llm_pricing.updater import ModelPrice


def test_build_prompt():
    prompt = build_prompt("OpenAI", "gpt-5 $1.25 input $10.00 output ...")
    assert "OpenAI" in prompt
    assert "JSON" in prompt
    assert "input" in prompt
    assert "output" in prompt


def test_parse_llm_response_valid():
    response = json.dumps({
        "models": [
            {"name": "gpt-5", "input": 1.25, "output": 10.00},
            {"name": "gpt-5-mini", "input": 0.25, "output": 2.00},
        ]
    })
    result = parse_llm_response(response)
    assert result["gpt-5"] == ModelPrice(1.25, 10.00)
    assert result["gpt-5-mini"] == ModelPrice(0.25, 2.00)


def test_parse_llm_response_with_markdown_fences():
    response = '```json\n{"models": [{"name": "gpt-5", "input": 1.25, "output": 10.00}]}\n```'
    result = parse_llm_response(response)
    assert result["gpt-5"] == ModelPrice(1.25, 10.00)


def test_parse_llm_response_invalid():
    with pytest.raises(ValueError):
        parse_llm_response("not valid json at all")


def test_parse_llm_response_empty_models():
    response = json.dumps({"models": []})
    with pytest.raises(ValueError):
        parse_llm_response(response)

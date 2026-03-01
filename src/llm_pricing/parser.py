from __future__ import annotations

import json
import re

import anthropic

from llm_pricing.updater import ModelPrice


def build_prompt(provider_name: str, page_text: str) -> str:
    return f"""다음은 {provider_name}의 LLM API 가격 페이지에서 추출한 텍스트입니다.
이 텍스트에서 텍스트/채팅 LLM 모델의 이름과 1M 토큰당 USD 가격을 추출하세요.
이미지 생성, 비디오, 임베딩, TTS/STT 모델은 제외하세요.
deprecated 모델도 제외하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{"models": [{{"name": "model-name", "input": 1.25, "output": 10.00}}, ...]}}

가격이 컨텍스트 길이에 따라 다른 경우(예: ≤200k, >200k), 기본(낮은) 가격을 사용하세요.

페이지 텍스트:
---
{page_text[:15000]}
---"""


def parse_llm_response(response_text: str) -> dict[str, ModelPrice]:
    cleaned = response_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {e}") from e

    models = data.get("models", [])
    if not models:
        raise ValueError("No models found in LLM response")

    result: dict[str, ModelPrice] = {}
    for m in models:
        name = m["name"]
        result[name] = ModelPrice(input=float(m["input"]), output=float(m["output"]))
    return result


async def parse_with_llm(
    provider_name: str,
    page_text: str,
    *,
    api_key: str,
    model: str = "claude-haiku-4-5",
    max_retries: int = 2,
) -> dict[str, ModelPrice]:
    prompt = build_prompt(provider_name, page_text)
    client = anthropic.AsyncAnthropic(api_key=api_key)
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            message = await client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text
            return parse_llm_response(response_text)
        except ValueError:
            raise
        except Exception as e:
            last_error = e

    raise RuntimeError(f"LLM parsing failed after {max_retries} attempts: {last_error}")

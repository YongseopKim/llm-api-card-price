from __future__ import annotations

import json
import re

import httpx

from llm_pricing.updater import ModelPrice


def build_prompt(provider_name: str, page_text: str) -> str:
    return f"""다음은 {provider_name}의 LLM API 가격 페이지에서 추출한 텍스트입니다.
이 텍스트에서 텍스트/채팅 LLM 모델의 이름과 1M 토큰당 USD 가격을 추출하세요.

## 모델명 규칙
- 반드시 API에서 사용하는 모델 ID를 사용하세요 (소문자, 하이픈 구분).
- 예: "claude-opus-4-6" (O), "Claude Opus 4.6" (X)
- 예: "gpt-5" (O), "GPT-5" (X)

## 제외 대상
다음 유형의 모델은 모두 제외하세요:
- deprecated 모델
- 이미지 생성/비디오/임베딩/TTS/STT 모델
- realtime (음성 대화) 모델 (예: gpt-4o-realtime-preview, gpt-realtime 등)
- codex (코드 전용) 모델 (예: gpt-5-codex, gpt-5.2-codex, codex-mini 등)
- computer-use 모델
- deep-research 모델 (예: o3-deep-research, o4-mini-deep-research 등)
- vision 전용 모델 (예: grok-2-vision-1212 등)
- TTS/오디오 전용 모델 (예: native-audio-preview 등)
- 이미지 생성 전용 모델
- 동일 모델의 날짜 태그/preview 변형 (예: gpt-4o-2024-05-13 → gpt-4o만 포함)
- 동일 모델의 -chat-latest, -search-preview, -search-api 등 별칭 변형

## 응답 형식
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
    proxy_url: str,
    model: str = "claude-haiku-4-5",
    max_retries: int = 2,
) -> dict[str, ModelPrice]:
    prompt = build_prompt(provider_name, page_text)
    url = f"{proxy_url.rstrip('/')}/v1/chat/completions"
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(max_retries):
            try:
                resp = await client.post(
                    url,
                    json={
                        "model": f"anthropic.{model}",
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                response_text = data["content"]
                return parse_llm_response(response_text)
            except ValueError:
                raise
            except Exception as e:
                last_error = e

    raise RuntimeError(f"LLM parsing failed after {max_retries} attempts: {last_error}")

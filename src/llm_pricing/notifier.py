from __future__ import annotations

from datetime import date

import httpx

from llm_pricing.updater import PricingDiff


PROVIDER_DISPLAY = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "xai": "xAI",
}


def format_change_message(diff: PricingDiff) -> str:
    today = date.today().isoformat()
    lines = [f"📊 LLM 가격 변동 알림 ({today})", ""]

    if diff.changed:
        lines.append("🔄 가격 변경:")
        for c in diff.changed:
            provider = PROVIDER_DISPLAY.get(c.provider, c.provider)
            parts = []
            if c.old_price.input != c.new_price.input:
                parts.append(f"input ${c.old_price.input:.2f}→${c.new_price.input:.2f}")
            if c.old_price.output != c.new_price.output:
                parts.append(f"output ${c.old_price.output:.2f}→${c.new_price.output:.2f}")
            lines.append(f"  • [{provider}] {c.model}: {', '.join(parts)}")
        lines.append("")

    if diff.added:
        lines.append("🆕 신규 모델:")
        for a in diff.added:
            provider = PROVIDER_DISPLAY.get(a.provider, a.provider)
            lines.append(f"  • [{provider}] {a.model}: ${a.price.input:.2f}/${a.price.output:.2f}")
        lines.append("")

    if diff.removed:
        lines.append("❌ 제거된 모델:")
        for r in diff.removed:
            provider = PROVIDER_DISPLAY.get(r.provider, r.provider)
            lines.append(f"  • [{provider}] {r.model}")
        lines.append("")

    return "\n".join(lines).strip()


def format_error_message(provider_name: str, error: str) -> str:
    today = date.today().isoformat()
    return f"⚠️ 스크래핑 실패 알림 ({today})\n\n프로바이더: {provider_name}\n에러: {error}"


async def send_telegram(token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"chat_id": chat_id, "text": message})
        return resp.status_code == 200

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    name: str
    url: str
    toml_section: str


PROVIDERS = [
    Provider(
        name="OpenAI",
        url="https://developers.openai.com/api/docs/pricing",
        toml_section="openai",
    ),
    Provider(
        name="Anthropic",
        url="https://platform.claude.com/docs/en/about-claude/pricing",
        toml_section="anthropic",
    ),
    Provider(
        name="xAI",
        url="https://docs.x.ai/docs/models",
        toml_section="xai",
    ),
]


@dataclass
class Settings:
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "claude-haiku-4-5"))
    llm_proxy_url: str = field(default_factory=lambda: os.getenv("LLM_PROXY_URL", "http://192.168.0.2:8081"))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    scrape_timeout: int = 30
    scrape_max_retries: int = 3
    parse_max_retries: int = 2

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

from llm_pricing.config import PROVIDERS, Provider, Settings
from llm_pricing.filter import apply_rules, load_rules
from llm_pricing.scraper import scrape_page, ScrapeError
from llm_pricing.parser import parse_with_llm
from llm_pricing.updater import (
    ModelPrice,
    PricingData,
    parse_toml,
    update_pricing_file,
    update_readme,
)
from llm_pricing.notifier import format_change_message, format_error_message, send_telegram

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PRICING_FILE = PROJECT_ROOT / "pricing.toml"
README_FILE = PROJECT_ROOT / "README.md"


async def process_provider(provider: Provider, settings: Settings) -> dict[str, ModelPrice] | None:
    try:
        logger.info(f"Scraping {provider.name}...")
        text = await scrape_page(
            provider.url,
            timeout=settings.scrape_timeout,
            max_retries=settings.scrape_max_retries,
        )
        logger.info(f"Parsing {provider.name} with LLM...")
        models = await parse_with_llm(
            provider.name,
            text,
            api_key=settings.anthropic_api_key,
            model=settings.llm_model,
            max_retries=settings.parse_max_retries,
        )
        logger.info(f"{provider.name}: found {len(models)} models")
        return models
    except (ScrapeError, RuntimeError, ValueError) as e:
        logger.error(f"{provider.name} failed: {e}")
        if settings.telegram_bot_token and settings.telegram_chat_id:
            msg = format_error_message(provider.name, str(e))
            await send_telegram(settings.telegram_bot_token, settings.telegram_chat_id, msg)
        return None


async def run() -> None:
    load_dotenv()
    settings = Settings()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    rules = load_rules()

    new_data: PricingData = {}
    for provider in PROVIDERS:
        result = await process_provider(provider, settings)
        if result is not None:
            new_data[provider.toml_section] = apply_rules(provider.toml_section, result, rules)

    if not new_data:
        logger.warning("No data collected from any provider")
        return

    diff = update_pricing_file(str(PRICING_FILE), new_data)

    # Always regenerate README from current TOML
    with open(PRICING_FILE) as f:
        current_data = parse_toml(f.read())
    update_readme(str(README_FILE), current_data)

    if diff.has_changes:
        logger.info(f"Changes detected: {len(diff.changed)} changed, {len(diff.added)} added, {len(diff.removed)} removed")
        if settings.telegram_bot_token and settings.telegram_chat_id:
            msg = format_change_message(diff)
            await send_telegram(settings.telegram_bot_token, settings.telegram_chat_id, msg)
    else:
        logger.info("No pricing changes detected")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

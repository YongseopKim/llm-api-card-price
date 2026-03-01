from unittest.mock import AsyncMock, patch
import pytest
from llm_pricing.main import process_provider
from llm_pricing.config import Provider, Settings
from llm_pricing.updater import ModelPrice


@pytest.mark.asyncio
async def test_process_provider_success():
    provider = Provider("TestProvider", "https://example.com", "test")
    settings = Settings()
    settings.anthropic_api_key = "test-key"

    with (
        patch("llm_pricing.main.scrape_page", new_callable=AsyncMock, return_value="page text"),
        patch("llm_pricing.main.parse_with_llm", new_callable=AsyncMock, return_value={"model-1": ModelPrice(1.0, 5.0)}),
    ):
        result = await process_provider(provider, settings)
        assert result is not None
        assert "model-1" in result


@pytest.mark.asyncio
async def test_process_provider_scrape_failure():
    from llm_pricing.scraper import ScrapeError

    provider = Provider("TestProvider", "https://example.com", "test")
    settings = Settings()

    with patch("llm_pricing.main.scrape_page", new_callable=AsyncMock, side_effect=ScrapeError("timeout")):
        result = await process_provider(provider, settings)
        assert result is None

import pytest
from llm_pricing.scraper import scrape_page, ScrapeError


@pytest.mark.asyncio
async def test_scrape_invalid_url():
    with pytest.raises(ScrapeError):
        await scrape_page("https://this-domain-does-not-exist-xyz.com/pricing", timeout=5, max_retries=1)

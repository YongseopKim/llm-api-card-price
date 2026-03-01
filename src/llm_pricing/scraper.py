from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


class ScrapeError(Exception):
    pass


async def scrape_page(url: str, *, timeout: int = 30, max_retries: int = 3) -> str:
    last_error: Exception | None = None

    for attempt in range(max_retries):
        if attempt > 0:
            await asyncio.sleep(2 ** attempt)

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
                text = await page.inner_text("body")
                await browser.close()
                if not text.strip():
                    raise ScrapeError(f"Empty page content from {url}")
                return text
        except ScrapeError:
            raise
        except Exception as e:
            last_error = e

    raise ScrapeError(f"Failed to scrape {url} after {max_retries} attempts: {last_error}")

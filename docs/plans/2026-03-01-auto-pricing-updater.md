# LLM API 가격 자동 업데이트 시스템 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 4개 프로바이더(OpenAI, Anthropic, Gemini, xAI/Grok)의 LLM API 가격을 매일 자동 스크래핑하여 pricing.toml을 갱신하고, README.md 테이블을 생성하며, Telegram으로 변경 알림을 보내는 시스템 구축.

**Architecture:** Playwright headless 브라우저로 각 프로바이더 가격 페이지 텍스트를 추출하고, LLM(기본 claude-haiku-4-5)으로 구조화된 데이터로 파싱한다. 기존 TOML과 비교하여 변경사항을 감지하고, 갱신 후 Telegram으로 알림을 보낸다. macOS launchd / Ubuntu systemd로 매일 스케줄 실행.

**Tech Stack:** Python 3.12+, Playwright, Anthropic SDK, tomli/tomli-w, httpx, python-dotenv, pytest

---

### Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `pyproject.toml`
- Create: `src/llm_pricing/__init__.py`
- Create: `.env.example`

**Step 1: pyproject.toml 생성**

```toml
[project]
name = "llm-pricing"
version = "0.1.0"
description = "Automated LLM API pricing tracker"
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.49",
    "anthropic>=0.42",
    "tomli>=2.0",
    "tomli-w>=1.0",
    "httpx>=0.27",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[project.scripts]
llm-pricing = "llm_pricing.main:main"
```

**Step 2: 디렉토리 생성 및 __init__.py**

```bash
mkdir -p src/llm_pricing tests
```

`src/llm_pricing/__init__.py`:
```python
"""LLM API pricing tracker."""
```

**Step 3: .env.example 생성**

```
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-100...
# Optional: override default LLM model for parsing
# LLM_MODEL=claude-haiku-4-5
```

**Step 4: .venv 생성 및 의존성 설치**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

**Step 5: pytest 실행 확인**

Run: `pytest --co -q`
Expected: "no tests ran" (테스트 파일 없으므로 정상)

**Step 6: 커밋**

```bash
git add pyproject.toml src/llm_pricing/__init__.py .env.example
git commit -m "chore: project scaffolding with pyproject.toml and dependencies"
```

---

### Task 2: config 모듈

**Files:**
- Create: `src/llm_pricing/config.py`
- Create: `tests/test_config.py`

**Step 1: 실패하는 테스트 작성**

`tests/test_config.py`:
```python
from llm_pricing.config import PROVIDERS, Settings


def test_providers_has_four_entries():
    assert len(PROVIDERS) == 4


def test_providers_have_required_fields():
    for p in PROVIDERS:
        assert p.name
        assert p.url.startswith("https://")
        assert p.toml_section


def test_provider_toml_sections_unique():
    sections = [p.toml_section for p in PROVIDERS]
    assert len(sections) == len(set(sections))


def test_settings_defaults():
    s = Settings()
    assert s.llm_model == "claude-haiku-4-5"
    assert s.scrape_timeout == 30
    assert s.scrape_max_retries == 3
    assert s.parse_max_retries == 2


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gpt-4.1-nano")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123")
    s = Settings()
    assert s.llm_model == "gpt-4.1-nano"
    assert s.anthropic_api_key == "test-key"
    assert s.telegram_bot_token == "test-token"
    assert s.telegram_chat_id == "-100123"
```

**Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'llm_pricing.config'`

**Step 3: config.py 구현**

`src/llm_pricing/config.py`:
```python
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
        name="Google Gemini",
        url="https://ai.google.dev/gemini-api/docs/pricing",
        toml_section="gemini",
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
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    scrape_timeout: int = 30
    scrape_max_retries: int = 3
    parse_max_retries: int = 2
```

**Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_config.py -v`
Expected: 5 passed

**Step 5: 커밋**

```bash
git add src/llm_pricing/config.py tests/test_config.py
git commit -m "feat: add config module with provider definitions and settings"
```

---

### Task 3: updater — TOML 읽기/쓰기/비교

**Files:**
- Create: `src/llm_pricing/updater.py`
- Create: `tests/test_updater.py`

**Step 1: 데이터 모델 및 TOML 파싱 테스트 작성**

`tests/test_updater.py`:
```python
from llm_pricing.updater import ModelPrice, parse_toml, diff_pricing, write_toml

SAMPLE_TOML = """\
# LLM Pricing — USD per 1M tokens
# Last updated: 2026-02-19

[openai]
"gpt-5" = { input = 1.25, output = 10.00 }
"gpt-5-mini" = { input = 0.25, output = 2.00 }

[anthropic]
"claude-opus-4-6" = { input = 5.00, output = 25.00 }
"""


def test_parse_toml():
    result = parse_toml(SAMPLE_TOML)
    assert "openai" in result
    assert "anthropic" in result
    assert result["openai"]["gpt-5"] == ModelPrice(input=1.25, output=10.00)
    assert result["anthropic"]["claude-opus-4-6"] == ModelPrice(input=5.00, output=25.00)


def test_diff_no_changes():
    old = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    new = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    d = diff_pricing(old, new)
    assert not d.has_changes


def test_diff_price_change():
    old = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    new = {"openai": {"gpt-5": ModelPrice(1.00, 8.00)}}
    d = diff_pricing(old, new)
    assert d.has_changes
    assert len(d.changed) == 1
    c = d.changed[0]
    assert c.provider == "openai"
    assert c.model == "gpt-5"
    assert c.old_price.input == 1.25
    assert c.new_price.input == 1.00


def test_diff_new_model():
    old = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    new = {"openai": {"gpt-5": ModelPrice(1.25, 10.00), "gpt-5-mini": ModelPrice(0.25, 2.00)}}
    d = diff_pricing(old, new)
    assert d.has_changes
    assert len(d.added) == 1
    assert d.added[0].model == "gpt-5-mini"


def test_diff_removed_model():
    old = {"openai": {"gpt-5": ModelPrice(1.25, 10.00), "gpt-5-mini": ModelPrice(0.25, 2.00)}}
    new = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    d = diff_pricing(old, new)
    assert d.has_changes
    assert len(d.removed) == 1
    assert d.removed[0].model == "gpt-5-mini"


def test_diff_new_provider():
    old = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    new = {
        "openai": {"gpt-5": ModelPrice(1.25, 10.00)},
        "xai": {"grok-3": ModelPrice(3.00, 15.00)},
    }
    d = diff_pricing(old, new)
    assert d.has_changes
    assert len(d.added) == 1


def test_write_toml():
    data = {
        "openai": {"gpt-5": ModelPrice(1.25, 10.00), "gpt-5-mini": ModelPrice(0.25, 2.00)},
        "anthropic": {"claude-opus-4-6": ModelPrice(5.00, 25.00)},
    }
    result = write_toml(data)
    assert "[openai]" in result
    assert "[anthropic]" in result
    assert "gpt-5" in result
    assert "Last updated:" in result
```

**Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_updater.py -v`
Expected: FAIL — `ImportError`

**Step 3: updater.py 구현 — 데이터 모델 + 파싱 + diff + 쓰기**

`src/llm_pricing/updater.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timezone, datetime

import tomli
import tomli_w


@dataclass(frozen=True)
class ModelPrice:
    input: float
    output: float


@dataclass(frozen=True)
class PriceChange:
    provider: str
    model: str
    old_price: ModelPrice
    new_price: ModelPrice


@dataclass(frozen=True)
class ModelEntry:
    provider: str
    model: str
    price: ModelPrice


@dataclass
class PricingDiff:
    changed: list[PriceChange]
    added: list[ModelEntry]
    removed: list[ModelEntry]

    @property
    def has_changes(self) -> bool:
        return bool(self.changed or self.added or self.removed)


# Type alias: provider -> model -> price
PricingData = dict[str, dict[str, ModelPrice]]


def parse_toml(content: str) -> PricingData:
    raw = tomli.loads(content)
    result: PricingData = {}
    for section, models in raw.items():
        if not isinstance(models, dict):
            continue
        result[section] = {}
        for model_name, prices in models.items():
            if isinstance(prices, dict) and "input" in prices and "output" in prices:
                result[section][model_name] = ModelPrice(
                    input=float(prices["input"]),
                    output=float(prices["output"]),
                )
    return result


def diff_pricing(old: PricingData, new: PricingData) -> PricingDiff:
    changed: list[PriceChange] = []
    added: list[ModelEntry] = []
    removed: list[ModelEntry] = []

    all_providers = set(old) | set(new)
    for provider in sorted(all_providers):
        old_models = old.get(provider, {})
        new_models = new.get(provider, {})

        for model in sorted(set(old_models) | set(new_models)):
            in_old = model in old_models
            in_new = model in new_models

            if in_old and in_new:
                if old_models[model] != new_models[model]:
                    changed.append(PriceChange(provider, model, old_models[model], new_models[model]))
            elif in_new:
                added.append(ModelEntry(provider, model, new_models[model]))
            else:
                removed.append(ModelEntry(provider, model, old_models[model]))

    return PricingDiff(changed=changed, added=added, removed=removed)


def write_toml(data: PricingData) -> str:
    today = date.today().isoformat()
    lines = [
        "# LLM Pricing — USD per 1M tokens",
        f"# Last updated: {today}",
        "#",
        "# Sources:",
        "#   - OpenAI: https://developers.openai.com/api/docs/pricing",
        "#   - Anthropic: https://platform.claude.com/docs/en/about-claude/pricing",
        "#   - Google: https://ai.google.dev/gemini-api/docs/pricing",
        "#   - xAI: https://docs.x.ai/docs/models",
        "",
    ]

    for section in sorted(data):
        lines.append(f"[{section}]")
        models = data[section]
        max_name_len = max((len(f'"{m}"') for m in models), default=0)
        for model_name in sorted(models, key=lambda m: (-models[m].input, m)):
            p = models[model_name]
            quoted = f'"{model_name}"'
            input_str = f"{p.input:.2f}".rstrip("0").rstrip(".")
            output_str = f"{p.output:.2f}".rstrip("0").rstrip(".")
            lines.append(f'{quoted:<{max_name_len}} = {{ input = {input_str}, output = {output_str} }}')
        lines.append("")

    return "\n".join(lines)


def update_pricing_file(path: str, new_data: PricingData) -> PricingDiff:
    with open(path) as f:
        old_data = parse_toml(f.read())

    merged = {}
    for provider in set(old_data) | set(new_data):
        if provider in new_data:
            merged[provider] = new_data[provider]
        else:
            merged[provider] = old_data[provider]

    d = diff_pricing(old_data, merged)
    if d.has_changes:
        with open(path, "w") as f:
            f.write(write_toml(merged))

    return d
```

**Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_updater.py -v`
Expected: 7 passed

**Step 5: 커밋**

```bash
git add src/llm_pricing/updater.py tests/test_updater.py
git commit -m "feat: add updater module with TOML parsing, diffing, and writing"
```

---

### Task 4: updater — README 테이블 생성

**Files:**
- Modify: `src/llm_pricing/updater.py`
- Modify: `tests/test_updater.py`

**Step 1: README 생성 테스트 추가**

`tests/test_updater.py`에 추가:
```python
from llm_pricing.updater import generate_readme_table, update_readme


def test_generate_readme_table():
    data = {
        "openai": {"gpt-5": ModelPrice(1.25, 10.00), "gpt-5-mini": ModelPrice(0.25, 2.00)},
        "anthropic": {"claude-opus-4-6": ModelPrice(5.00, 25.00)},
    }
    table = generate_readme_table(data)
    assert "## LLM API Pricing" in table
    assert "### OpenAI" in table or "### openai" in table
    assert "| gpt-5 " in table
    assert "$1.25" in table
    assert "$10.00" in table


def test_update_readme_with_markers(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# My Project\n\nSome intro.\n\n"
        "<!-- PRICING_TABLE_START -->\nold table\n<!-- PRICING_TABLE_END -->\n\n"
        "## Footer\n"
    )
    data = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    update_readme(str(readme), data)
    content = readme.read_text()
    assert "<!-- PRICING_TABLE_START -->" in content
    assert "<!-- PRICING_TABLE_END -->" in content
    assert "old table" not in content
    assert "$1.25" in content
    assert "## Footer" in content


def test_update_readme_creates_markers_if_missing(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n")
    data = {"openai": {"gpt-5": ModelPrice(1.25, 10.00)}}
    update_readme(str(readme), data)
    content = readme.read_text()
    assert "<!-- PRICING_TABLE_START -->" in content
    assert "$1.25" in content
```

**Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_updater.py::test_generate_readme_table -v`
Expected: FAIL — `ImportError`

**Step 3: README 생성 로직 구현**

`src/llm_pricing/updater.py`에 추가:
```python
PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Google Gemini",
    "xai": "xAI (Grok)",
}

README_START_MARKER = "<!-- PRICING_TABLE_START -->"
README_END_MARKER = "<!-- PRICING_TABLE_END -->"


def generate_readme_table(data: PricingData) -> str:
    today = date.today().isoformat()
    lines = [
        "## LLM API Pricing (USD per 1M tokens)",
        f"> Last updated: {today}",
        "",
    ]

    for section in sorted(data):
        display = PROVIDER_DISPLAY_NAMES.get(section, section)
        lines.append(f"### {display}")
        lines.append("| Model | Input | Output |")
        lines.append("|-------|------:|-------:|")
        models = data[section]
        for model_name in sorted(models, key=lambda m: (-models[m].input, m)):
            p = models[model_name]
            lines.append(f"| {model_name} | ${p.input:.2f} | ${p.output:.2f} |")
        lines.append("")

    return "\n".join(lines)


def update_readme(path: str, data: PricingData) -> None:
    table = generate_readme_table(data)
    block = f"{README_START_MARKER}\n{table}\n{README_END_MARKER}"

    try:
        with open(path) as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    if README_START_MARKER in content and README_END_MARKER in content:
        start = content.index(README_START_MARKER)
        end = content.index(README_END_MARKER) + len(README_END_MARKER)
        content = content[:start] + block + content[end:]
    else:
        content = content.rstrip() + "\n\n" + block + "\n"

    with open(path, "w") as f:
        f.write(content)
```

**Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_updater.py -v`
Expected: 10 passed (7 기존 + 3 신규)

**Step 5: 커밋**

```bash
git add src/llm_pricing/updater.py tests/test_updater.py
git commit -m "feat: add README table generation with marker-based replacement"
```

---

### Task 5: notifier — Telegram 알림

**Files:**
- Create: `src/llm_pricing/notifier.py`
- Create: `tests/test_notifier.py`

**Step 1: 메시지 포맷팅 테스트 작성**

`tests/test_notifier.py`:
```python
from llm_pricing.notifier import format_change_message, format_error_message
from llm_pricing.updater import ModelPrice, PriceChange, ModelEntry, PricingDiff


def test_format_change_message_price_change():
    diff = PricingDiff(
        changed=[PriceChange("openai", "gpt-5", ModelPrice(1.25, 10.00), ModelPrice(1.00, 8.00))],
        added=[],
        removed=[],
    )
    msg = format_change_message(diff)
    assert "가격 변동" in msg or "Price" in msg
    assert "gpt-5" in msg
    assert "1.25" in msg
    assert "1.00" in msg or "1.0" in msg


def test_format_change_message_new_model():
    diff = PricingDiff(
        changed=[],
        added=[ModelEntry("xai", "grok-3", ModelPrice(3.00, 15.00))],
        removed=[],
    )
    msg = format_change_message(diff)
    assert "grok-3" in msg
    assert "3.00" in msg or "3.0" in msg


def test_format_change_message_removed_model():
    diff = PricingDiff(
        changed=[],
        added=[],
        removed=[ModelEntry("openai", "gpt-4o-mini", ModelPrice(0.15, 0.60))],
    )
    msg = format_change_message(diff)
    assert "gpt-4o-mini" in msg


def test_format_change_message_combined():
    diff = PricingDiff(
        changed=[PriceChange("openai", "gpt-5", ModelPrice(1.25, 10.00), ModelPrice(1.00, 8.00))],
        added=[ModelEntry("xai", "grok-3", ModelPrice(3.00, 15.00))],
        removed=[ModelEntry("openai", "gpt-4o-mini", ModelPrice(0.15, 0.60))],
    )
    msg = format_change_message(diff)
    assert "gpt-5" in msg
    assert "grok-3" in msg
    assert "gpt-4o-mini" in msg


def test_format_error_message():
    msg = format_error_message("OpenAI", "Timeout after 30s")
    assert "OpenAI" in msg
    assert "Timeout" in msg
```

**Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_notifier.py -v`
Expected: FAIL — `ImportError`

**Step 3: notifier.py 구현 — 메시지 포맷팅**

`src/llm_pricing/notifier.py`:
```python
from __future__ import annotations

from datetime import date

import httpx

from llm_pricing.updater import PricingDiff


PROVIDER_DISPLAY = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
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
```

**Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_notifier.py -v`
Expected: 5 passed

**Step 5: 커밋**

```bash
git add src/llm_pricing/notifier.py tests/test_notifier.py
git commit -m "feat: add notifier module with Telegram message formatting"
```

---

### Task 6: scraper — Playwright 스크래핑

**Files:**
- Create: `src/llm_pricing/scraper.py`
- Create: `tests/test_scraper.py`

**Step 1: 재시도 로직 유닛 테스트 작성**

`tests/test_scraper.py`:
```python
import pytest
from llm_pricing.scraper import scrape_page, ScrapeError


@pytest.mark.asyncio
async def test_scrape_invalid_url():
    with pytest.raises(ScrapeError):
        await scrape_page("https://this-domain-does-not-exist-xyz.com/pricing", timeout=5, max_retries=1)
```

**Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_scraper.py -v`
Expected: FAIL — `ImportError`

**Step 3: scraper.py 구현**

`src/llm_pricing/scraper.py`:
```python
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
```

**Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_scraper.py -v`
Expected: 1 passed (invalid URL → ScrapeError)

**Step 5: 커밋**

```bash
git add src/llm_pricing/scraper.py tests/test_scraper.py
git commit -m "feat: add scraper module with Playwright and retry logic"
```

---

### Task 7: parser — LLM 파싱

**Files:**
- Create: `src/llm_pricing/parser.py`
- Create: `tests/test_parser.py`

**Step 1: 프롬프트 및 응답 파싱 테스트 작성**

LLM 호출 자체는 모킹하되, 프롬프트 생성과 응답 파싱 로직을 테스트한다.

`tests/test_parser.py`:
```python
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
```

**Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_parser.py -v`
Expected: FAIL — `ImportError`

**Step 3: parser.py 구현**

`src/llm_pricing/parser.py`:
```python
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
```

**Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_parser.py -v`
Expected: 5 passed

**Step 5: 커밋**

```bash
git add src/llm_pricing/parser.py tests/test_parser.py
git commit -m "feat: add parser module with LLM prompt building and response parsing"
```

---

### Task 8: main — 오케스트레이션

**Files:**
- Create: `src/llm_pricing/main.py`
- Create: `tests/test_main.py`

**Step 1: 오케스트레이션 흐름 테스트 (모킹)**

`tests/test_main.py`:
```python
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from llm_pricing.main import process_provider, run
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
```

**Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_main.py -v`
Expected: FAIL — `ImportError`

**Step 3: main.py 구현**

`src/llm_pricing/main.py`:
```python
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from llm_pricing.config import PROVIDERS, Provider, Settings
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

    new_data: PricingData = {}
    for provider in PROVIDERS:
        result = await process_provider(provider, settings)
        if result is not None:
            new_data[provider.toml_section] = result

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
```

**Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_main.py -v`
Expected: 2 passed

**Step 5: 커밋**

```bash
git add src/llm_pricing/main.py tests/test_main.py
git commit -m "feat: add main orchestration module"
```

---

### Task 9: xAI/Grok을 pricing.toml에 추가

**Files:**
- Modify: `pricing.toml`

**Step 1: xAI 섹션 추가**

`pricing.toml`에 xai 섹션 추가:
```toml
[xai]
"grok-4-1-fast-reasoning"     = { input = 0.20,  output = 0.50 }
"grok-4-1-fast-non-reasoning" = { input = 0.20,  output = 0.50 }
"grok-4-fast-reasoning"       = { input = 0.20,  output = 0.50 }
"grok-4-fast-non-reasoning"   = { input = 0.20,  output = 0.50 }
"grok-4-0709"                 = { input = 3.00,  output = 15.00 }
"grok-3"                      = { input = 3.00,  output = 15.00 }
"grok-3-mini"                 = { input = 0.30,  output = 0.50 }
```

또한 Sources 헤더에 xAI URL 추가:
```toml
#   - xAI: https://docs.x.ai/docs/models
```

**Step 2: 커밋**

```bash
git add pricing.toml
git commit -m "feat: add xAI/Grok provider pricing data"
```

---

### Task 10: 서비스 스크립트 (launchd / systemd)

**Files:**
- Create: `scripts/com.llm-pricing.updater.plist`
- Create: `scripts/llm-pricing-updater.service`
- Create: `scripts/llm-pricing-updater.timer`
- Create: `scripts/install-launchd.sh`
- Create: `scripts/install-systemd.sh`
- Create: `scripts/uninstall-launchd.sh`
- Create: `scripts/uninstall-systemd.sh`

**Step 1: launchd plist 생성**

`scripts/com.llm-pricing.updater.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.llm-pricing.updater</string>
    <key>ProgramArguments</key>
    <array>
        <string>__REPO_PATH__/.venv/bin/python</string>
        <string>-m</string>
        <string>llm_pricing.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>__REPO_PATH__</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>__REPO_PATH__/src</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>4</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>__REPO_PATH__/logs/updater.log</string>
    <key>StandardErrorPath</key>
    <string>__REPO_PATH__/logs/updater.err</string>
</dict>
</plist>
```

**Step 2: install-launchd.sh 생성**

`scripts/install-launchd.sh`:
```bash
#!/bin/bash
set -euo pipefail

REPO_PATH="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_NAME="com.llm-pricing.updater.plist"
PLIST_SRC="${REPO_PATH}/scripts/${PLIST_NAME}"
PLIST_DST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

mkdir -p "${REPO_PATH}/logs"
mkdir -p "${HOME}/Library/LaunchAgents"

sed "s|__REPO_PATH__|${REPO_PATH}|g" "${PLIST_SRC}" > "${PLIST_DST}"

launchctl unload "${PLIST_DST}" 2>/dev/null || true
launchctl load "${PLIST_DST}"

echo "Installed and loaded ${PLIST_NAME}"
echo "Logs: ${REPO_PATH}/logs/"
```

**Step 3: uninstall-launchd.sh 생성**

`scripts/uninstall-launchd.sh`:
```bash
#!/bin/bash
set -euo pipefail

PLIST_NAME="com.llm-pricing.updater.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

launchctl unload "${PLIST_DST}" 2>/dev/null || true
rm -f "${PLIST_DST}"

echo "Uninstalled ${PLIST_NAME}"
```

**Step 4: systemd service + timer 생성**

`scripts/llm-pricing-updater.service`:
```ini
[Unit]
Description=LLM API Pricing Updater
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=__REPO_PATH__
Environment=PYTHONPATH=__REPO_PATH__/src
ExecStart=__REPO_PATH__/.venv/bin/python -m llm_pricing.main
```

`scripts/llm-pricing-updater.timer`:
```ini
[Unit]
Description=Run LLM pricing updater daily at 4am

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Step 5: install-systemd.sh 생성**

`scripts/install-systemd.sh`:
```bash
#!/bin/bash
set -euo pipefail

REPO_PATH="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="${HOME}/.config/systemd/user"

mkdir -p "${SERVICE_DIR}"
mkdir -p "${REPO_PATH}/logs"

sed "s|__REPO_PATH__|${REPO_PATH}|g" "${REPO_PATH}/scripts/llm-pricing-updater.service" > "${SERVICE_DIR}/llm-pricing-updater.service"
sed "s|__REPO_PATH__|${REPO_PATH}|g" "${REPO_PATH}/scripts/llm-pricing-updater.timer" > "${SERVICE_DIR}/llm-pricing-updater.timer"

systemctl --user daemon-reload
systemctl --user enable --now llm-pricing-updater.timer

echo "Installed and enabled llm-pricing-updater.timer"
echo "Check status: systemctl --user status llm-pricing-updater.timer"
```

**Step 6: uninstall-systemd.sh 생성**

`scripts/uninstall-systemd.sh`:
```bash
#!/bin/bash
set -euo pipefail

systemctl --user disable --now llm-pricing-updater.timer 2>/dev/null || true
rm -f "${HOME}/.config/systemd/user/llm-pricing-updater.service"
rm -f "${HOME}/.config/systemd/user/llm-pricing-updater.timer"
systemctl --user daemon-reload

echo "Uninstalled llm-pricing-updater"
```

**Step 7: 커밋**

```bash
git add scripts/
git commit -m "feat: add launchd and systemd service scripts"
```

---

### Task 11: 통합 테스트 (수동)

**Files:**
- No new files

**Step 1: .env 파일 설정**

```bash
cp .env.example .env
# Edit .env with real API keys
```

**Step 2: 수동 실행 테스트**

```bash
PYTHONPATH=src python -m llm_pricing.main
```

Expected:
- 4개 프로바이더 스크래핑 성공 로그
- pricing.toml 갱신 (xAI 포함 4개 섹션)
- README.md 테이블 생성
- Telegram 알림 (변경사항 있을 경우)

**Step 3: 전체 테스트 스위트 실행**

```bash
PYTHONPATH=src pytest tests/ -v
```

Expected: 모든 테스트 통과

**Step 4: 최종 커밋**

```bash
git add -A
git commit -m "chore: final integration verification"
```

---

### Task 12: .gitignore 및 README 업데이트

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`

**Step 1: .gitignore에 logs/ 추가**

`.gitignore`에 추가:
```
logs/
```

**Step 2: README.md 초기 내용 작성**

README에 프로젝트 설명 + 마커를 포함하여 작성. 마커 사이는 자동 업데이트됨.

```markdown
# LLM API Card Price

LLM 프로바이더별 API 가격을 자동으로 추적하고 업데이트합니다.

## Setup

1. `.venv` 생성 및 의존성 설치:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   playwright install chromium
   ```

2. `.env` 파일 설정:
   ```bash
   cp .env.example .env
   # Edit with your API keys
   ```

3. 서비스 등록 (선택):
   - macOS: `bash scripts/install-launchd.sh`
   - Ubuntu: `bash scripts/install-systemd.sh`

## Manual Run

```bash
source .venv/bin/activate
PYTHONPATH=src python -m llm_pricing.main
```

<!-- PRICING_TABLE_START -->
<!-- 자동 생성됩니다 -->
<!-- PRICING_TABLE_END -->
```

**Step 3: 커밋**

```bash
git add .gitignore README.md
git commit -m "docs: add README with setup guide and pricing table markers"
```

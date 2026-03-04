from llm_pricing.config import PROVIDERS, Settings


def test_providers_has_three_entries():
    assert len(PROVIDERS) == 3


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
    monkeypatch.setenv("LLM_PROXY_URL", "http://10.0.0.1:9090")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123")
    s = Settings()
    assert s.llm_model == "gpt-4.1-nano"
    assert s.llm_proxy_url == "http://10.0.0.1:9090"
    assert s.telegram_bot_token == "test-token"
    assert s.telegram_chat_id == "-100123"

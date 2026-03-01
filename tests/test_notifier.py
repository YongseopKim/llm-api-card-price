from llm_pricing.notifier import format_change_message, format_error_message
from llm_pricing.updater import ModelPrice, PriceChange, ModelEntry, PricingDiff


def test_format_change_message_price_change():
    diff = PricingDiff(
        changed=[PriceChange("openai", "gpt-5", ModelPrice(1.25, 10.00), ModelPrice(1.00, 8.00))],
        added=[],
        removed=[],
    )
    msg = format_change_message(diff)
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

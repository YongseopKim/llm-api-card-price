from llm_pricing.updater import ModelPrice, parse_toml, diff_pricing, write_toml, generate_readme_table, update_readme

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


def test_generate_readme_table():
    data = {
        "openai": {"gpt-5": ModelPrice(1.25, 10.00), "gpt-5-mini": ModelPrice(0.25, 2.00)},
        "anthropic": {"claude-opus-4-6": ModelPrice(5.00, 25.00)},
    }
    table = generate_readme_table(data)
    assert "## LLM API Pricing" in table
    assert "### OpenAI" in table
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

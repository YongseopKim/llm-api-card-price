from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import tomli


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
                    changed.append(
                        PriceChange(provider, model, old_models[model], new_models[model])
                    )
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
            lines.append(
                f'{quoted:<{max_name_len}} = {{ input = {input_str}, output = {output_str} }}'
            )
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

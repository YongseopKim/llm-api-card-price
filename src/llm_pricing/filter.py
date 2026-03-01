from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import tomllib

from llm_pricing.updater import ModelPrice

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).resolve().parent.parent.parent / "rules.toml"


@dataclass(frozen=True)
class ProviderRule:
    prefix: str
    min_version: int


def load_rules(path: str | Path = RULES_FILE) -> dict[str, ProviderRule]:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return {
        section: ProviderRule(prefix=data["prefix"], min_version=data["min_version"])
        for section, data in raw.items()
        if isinstance(data, dict)
    }


def extract_version(model_name: str, prefix: str) -> int | None:
    """prefix 제거 후 첫 번째 정수를 버전으로 반환."""
    if not model_name.startswith(prefix):
        return None
    remainder = model_name[len(prefix):]
    match = re.search(r"\d+", remainder)
    if match is None:
        return None
    return int(match.group())


def apply_rules(
    section: str,
    models: dict[str, ModelPrice],
    rules: dict[str, ProviderRule],
) -> dict[str, ModelPrice]:
    rule = rules.get(section)
    if rule is None:
        return models

    filtered: dict[str, ModelPrice] = {}
    for name, price in models.items():
        version = extract_version(name, rule.prefix)
        if version is None:
            logger.debug(f"Filtered out {name}: prefix mismatch or no version")
            continue
        if version < rule.min_version:
            logger.debug(f"Filtered out {name}: version {version} < {rule.min_version}")
            continue
        filtered[name] = price

    removed = len(models) - len(filtered)
    if removed:
        logger.info(f"{section}: filtered out {removed} models by rules")
    return filtered

"""Validate that YAML pack examples actually match/don't match their compiled patterns."""

import re
from pathlib import Path

import pytest
import yaml


def _load_pack_data(name: str) -> list[dict]:
    pack_dir = Path(__file__).parent.parent / "src" / "ai_watchdog" / "packs"
    path = pack_dir / f"{name}.yaml"
    data = yaml.safe_load(path.read_text())
    return data.get("rules", [])


def _collect_example_cases():
    """Yield (pack, rule_name, example_text, should_match) for parametrized tests."""
    cases = []
    for pack in ["strict", "standard", "light"]:
        for rule_data in _load_pack_data(pack):
            name = rule_data["name"]
            patterns = [re.compile(p) for p in rule_data.get("patterns", [])]
            if not patterns:
                continue
            examples = rule_data.get("examples", {})
            for text in examples.get("match", []):
                cases.append((pack, name, text, True, patterns))
            for text in examples.get("no_match", []):
                cases.append((pack, name, text, False, patterns))
    return cases


_CASES = _collect_example_cases()


@pytest.mark.parametrize(
    "pack,rule_name,text,should_match,patterns",
    _CASES,
    ids=[f"{c[0]}/{c[1]}/{'match' if c[3] else 'no_match'}/{c[2][:40]}" for c in _CASES],
)
def test_yaml_example(pack, rule_name, text, should_match, patterns):
    matched = any(p.search(text) for p in patterns)
    if should_match:
        assert matched, f"[{pack}] {rule_name}: expected match on: {text!r}"
    else:
        assert not matched, f"[{pack}] {rule_name}: unexpected match on: {text!r}"

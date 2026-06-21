import json
from pathlib import Path

import pytest

from src.data.boss_data import BossData


@pytest.fixture
def boss_data(tmp_path):
    return BossData(data_dir=tmp_path)


def test_default_config_when_file_missing(boss_data):
    config = boss_data.get_config()
    assert config["qualified_level"] == 42
    assert config["min_players"] == 1
    assert config["base_reward"] == 12_000_000
    assert config["min_reward"] == 6_000_000
    assert config["cd_seconds"] == 300
    assert config["phantom_name"] == "妖王幻影"


def test_load_custom_config(tmp_path):
    config_path = tmp_path / "boss_config.json"
    config_path.write_text(
        json.dumps(
            {"qualified_level": 50, "base_reward": 20_000_000, "phantom_name": "魔君"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    boss_data = BossData(data_dir=tmp_path)

    assert boss_data.qualified_level() == 50
    assert boss_data.base_reward() == 20_000_000
    assert boss_data.phantom_name() == "魔君"
    assert boss_data.min_reward() == 6_000_000  # 默认值保留


def test_invalid_json_falls_back_to_defaults(tmp_path):
    config_path = tmp_path / "boss_config.json"
    config_path.write_text("not json", encoding="utf-8")
    boss_data = BossData(data_dir=tmp_path)

    assert boss_data.qualified_level() == 42
    assert boss_data.cd_seconds() == 300


def test_get_with_custom_default(boss_data):
    assert boss_data.get("nonexistent_key", "fallback") == "fallback"

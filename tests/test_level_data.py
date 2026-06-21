from pathlib import Path

import pytest

from src.data.level_data import LevelData


@pytest.fixture
def level_data(tmp_path):
    levels_dir = tmp_path / "levels"
    levels_dir.mkdir()
    (levels_dir / "练气境界.json").write_text(
        '[{"level": "凡人", "exp": 100, "level_id": 1, "基础攻击": 2000, "基础防御": 2000, "基础血量": 4000, "基础暴击": 0.01}, {"level": "虚妄境初期", "exp": 500, "level_id": 2, "基础攻击": 5000, "基础防御": 5000, "基础血量": 10000, "基础暴击": 0.05}]',
        encoding="utf-8",
    )
    (levels_dir / "炼体境界.json").write_text(
        '[{"level": "莽夫", "exp": 100, "level_id": 1}, {"level": "炼皮初期", "exp": 500, "level_id": 2}]',
        encoding="utf-8",
    )
    return LevelData(data_dir=tmp_path)


def test_loads_cultivation_levels(level_data):
    assert len(level_data.cultivation_levels) == 2
    assert level_data.get_cultivation_name(1) == "凡人"
    assert level_data.get_cultivation_name(2) == "虚妄境初期"


def test_loads_physique_levels(level_data):
    assert len(level_data.physique_levels) == 2
    assert level_data.get_physique_name(1) == "莽夫"
    assert level_data.get_physique_name(2) == "炼皮初期"


def test_returns_unknown_for_missing_level(level_data):
    assert level_data.get_cultivation_name(999) == "未知"
    assert level_data.get_physique_name(999) == "未知"


def test_get_cultivation_stats(level_data):
    stats = level_data.get_cultivation_stats(1)
    assert stats == {"attack": 2000, "defense": 2000, "hp": 4000, "crit_rate": 0.01}


def test_get_cultivation_stats_missing_level(level_data):
    assert level_data.get_cultivation_stats(999) == {"attack": 0, "defense": 0, "hp": 0, "crit_rate": 0}

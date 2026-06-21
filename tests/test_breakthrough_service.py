from pathlib import Path

import pytest

from src.data.level_data import LevelData
from src.services.breakthrough_service import BreakthroughService, BreakthroughResult
from src.services.player_service import PlayerService


@pytest.fixture
def service(tmp_path):
    levels_dir = tmp_path / "levels"
    levels_dir.mkdir()
    (levels_dir / "练气境界.json").write_text(
        '[{"level": "凡人", "exp": 100, "level_id": 1, "基础血量": 4000},'
        '{"level": "虚妄境初期", "exp": 500, "level_id": 2, "基础血量": 10000},'
        '{"level": "虚妄境中期", "exp": 1000, "level_id": 3, "基础血量": 20000}]',
        encoding="utf-8",
    )
    (levels_dir / "炼体境界.json").write_text(
        '[{"level": "莽夫", "exp": 100, "level_id": 1},'
        '{"level": "炼皮初期", "exp": 500, "level_id": 2}]',
        encoding="utf-8",
    )
    player_service = PlayerService(data_dir=tmp_path)
    level_data = LevelData(data_dir=tmp_path)
    return BreakthroughService(
        player_service=player_service,
        level_data=level_data,
    )


@pytest.mark.asyncio
async def test_breakthrough_requires_player(service):
    """未创建角色时突破应失败。"""
    result = await service.attempt_cultivation_breakthrough("10086")
    assert not result.success
    assert result.player_not_found


@pytest.mark.asyncio
async def test_breakthrough_fails_without_enough_exp(service):
    """修为不足时突破应失败。"""
    player = await service.player_service.create_player("10086")
    player["exp"] = 50
    await service.player_service.save("10086", player)

    result = await service.attempt_cultivation_breakthrough("10086")

    assert not result.success
    assert result.reason == "修为不足"
    assert result.required_exp == 100


@pytest.mark.asyncio
async def test_breakthrough_succeeds_with_enough_exp(service):
    """修为足够时突破应成功并升级。"""
    player = await service.player_service.create_player("10086")
    player["exp"] = 500
    await service.player_service.save("10086", player)

    result = await service.attempt_cultivation_breakthrough("10086")

    assert result.success
    assert result.new_level == 2

    player = await service.player_service.load("10086")
    assert player["level_id"] == 2


@pytest.mark.asyncio
async def test_breakthrough_fails_at_max_level(service):
    """达到最高境界后突破应失败。"""
    player = await service.player_service.create_player("10086")
    player["level_id"] = 3
    player["exp"] = 999999
    await service.player_service.save("10086", player)

    result = await service.attempt_cultivation_breakthrough("10086")

    assert not result.success
    assert result.reason == "已达最高境界"


@pytest.mark.asyncio
async def test_physique_breakthrough_requires_player(service):
    """未创建角色时炼体突破应失败。"""
    result = await service.attempt_physique_breakthrough("10086")
    assert not result.success
    assert result.player_not_found


@pytest.mark.asyncio
async def test_physique_breakthrough_fails_without_enough_blood_qi(service):
    """血气不足时炼体突破应失败。"""
    player = await service.player_service.create_player("10086")
    player["blood_qi"] = 50
    await service.player_service.save("10086", player)

    result = await service.attempt_physique_breakthrough("10086")

    assert not result.success
    assert result.reason == "血气不足"
    assert result.required_exp == 100


@pytest.mark.asyncio
async def test_physique_breakthrough_succeeds_with_enough_blood_qi(service):
    """血气足够时炼体突破应成功并升级。"""
    player = await service.player_service.create_player("10086")
    player["blood_qi"] = 500
    await service.player_service.save("10086", player)

    result = await service.attempt_physique_breakthrough("10086")

    assert result.success
    assert result.new_level == 2

    player = await service.player_service.load("10086")
    assert player["physique_id"] == 2


@pytest.mark.asyncio
async def test_physique_breakthrough_fails_at_max_level(service):
    """达到最高炼体境界后突破应失败。"""
    player = await service.player_service.create_player("10086")
    player["physique_id"] = 2
    player["blood_qi"] = 999999
    await service.player_service.save("10086", player)

    result = await service.attempt_physique_breakthrough("10086")

    assert not result.success
    assert result.reason == "已达最高境界"


@pytest.mark.asyncio
async def test_lucky_cultivation_breakthrough_succeeds(service):
    """幸运突破消耗灵石并必定成功。"""
    player = await service.player_service.create_player("10086")
    player["exp"] = 500
    player["spirit_stones"] = 1000
    await service.player_service.save("10086", player)

    result = await service.attempt_cultivation_lucky_breakthrough("10086")

    assert result.success
    assert result.new_level == 2
    player = await service.player_service.load("10086")
    assert player["spirit_stones"] == 500


@pytest.mark.asyncio
async def test_lucky_cultivation_breakthrough_insufficient_spirit_stones(service):
    """灵石不足时幸运突破失败。"""
    player = await service.player_service.create_player("10086")
    player["exp"] = 500
    player["spirit_stones"] = 100
    await service.player_service.save("10086", player)

    result = await service.attempt_cultivation_lucky_breakthrough("10086")

    assert not result.success
    assert "灵石不足" in result.reason


@pytest.mark.asyncio
async def test_lucky_physique_breakthrough_succeeds(service):
    """幸运破体消耗灵石并必定成功。"""
    player = await service.player_service.create_player("10086")
    player["blood_qi"] = 500
    player["spirit_stones"] = 1000
    await service.player_service.save("10086", player)

    result = await service.attempt_physique_lucky_breakthrough("10086")

    assert result.success
    assert result.new_level == 2
    player = await service.player_service.load("10086")
    assert player["spirit_stones"] == 500


@pytest.mark.asyncio
async def test_auto_cultivation_breakthrough_stops_when_exp_runs_out(service):
    """一键突破应连升多层直到修为不足。"""
    player = await service.player_service.create_player("10086")
    player["exp"] = 400
    await service.player_service.save("10086", player)

    result = await service.attempt_cultivation_auto_breakthrough("10086")

    assert not result.player_not_found
    assert result.total_levels == 1
    assert result.final_level == 2
    assert "修为不足" in result.reason

    player = await service.player_service.load("10086")
    assert player["level_id"] == 2


@pytest.mark.asyncio
async def test_auto_physique_breakthrough_stops_at_max_level(service):
    """一键破体应连升到最高境界后停止。"""
    player = await service.player_service.create_player("10086")
    player["blood_qi"] = 999999
    await service.player_service.save("10086", player)

    result = await service.attempt_physique_auto_breakthrough("10086")

    assert result.total_levels == 1
    assert result.final_level == 2
    assert result.reason == "已达最高境界"


@pytest.mark.asyncio
async def test_auto_cultivation_breakthrough_returns_not_found(service):
    """未创建角色时一键突破应返回未找到。"""
    result = await service.attempt_cultivation_auto_breakthrough("10086")
    assert result.player_not_found
    assert result.total_levels == 0

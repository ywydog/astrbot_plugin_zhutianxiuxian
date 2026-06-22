import pytest
from pathlib import Path

from src.data.level_data import LevelData
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.xiangu_jinshi_service import XianguJinshiService


@pytest.fixture
def xiangu_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    level_data = LevelData(data_dir=Path(__file__).parent.parent / "data")
    return XianguJinshiService(
        player_service=player_service,
        inventory_service=inventory_service,
        level_data=level_data,
    )


async def _create_ready_player(xiangu_service, user_id="u1"):
    await xiangu_service.player_service.create_player(user_id)
    player = await xiangu_service.player_service.load(user_id)
    player["level_id"] = 42
    player["physique_id"] = 42
    player["mijing_level_id"] = 1
    player["exp"] = 10_000_000
    player["blood_qi"] = 10_000_000
    player["learned_gongfa"] = ["原始真解"]
    await xiangu_service.player_service.save(user_id, player)


@pytest.mark.asyncio
async def test_breakthrough_not_ready_low_level(xiangu_service):
    await xiangu_service.player_service.create_player("u1")
    result = await xiangu_service.breakthrough("u1")
    assert result.not_ready


@pytest.mark.asyncio
async def test_breakthrough_already_max(xiangu_service):
    await _create_ready_player(xiangu_service)
    player = await xiangu_service.player_service.load("u1")
    player["xiangu_level_id"] = 99
    await xiangu_service.player_service.save("u1", player)

    result = await xiangu_service.breakthrough("u1")
    assert result.already_max


@pytest.mark.asyncio
async def test_breakthrough_mijing_conflict(xiangu_service):
    await _create_ready_player(xiangu_service)
    player = await xiangu_service.player_service.load("u1")
    player["mijing_level_id"] = 2
    await xiangu_service.player_service.save("u1", player)

    result = await xiangu_service.breakthrough("u1")
    assert result.not_ready


@pytest.mark.asyncio
async def test_breakthrough_missing_items(xiangu_service):
    await _create_ready_player(xiangu_service)

    result = await xiangu_service.breakthrough("u1")
    assert result.insufficient_resources
    assert result.missing_items


@pytest.mark.asyncio
async def test_breakthrough_success(xiangu_service):
    await _create_ready_player(xiangu_service)
    for item in [
        {"name": "朱厌真血", "category": "道具"},
        {"name": "螭龙真血", "category": "道具"},
        {"name": "饕餮真血", "category": "道具"},
    ]:
        await xiangu_service.inventory_service.add_item(
            "u1", item["category"], item["name"], 1
        )

    result = await xiangu_service.breakthrough("u1")

    assert result.success
    assert result.level_name == "搬血境"
    player = await xiangu_service.player_service.load("u1")
    assert player["xiangu_level_id"] == 2


@pytest.mark.asyncio
async def test_extreme_breakthrough_success(xiangu_service):
    await _create_ready_player(xiangu_service)
    player = await xiangu_service.player_service.load("u1")
    player["xiangu_level_id"] = 1
    await xiangu_service.player_service.save("u1", player)
    for item in [
        {"name": "朱雀真血", "category": "道具"},
        {"name": "狻猊真血", "category": "道具"},
        {"name": "饕餮真血", "category": "道具"},
    ]:
        await xiangu_service.inventory_service.add_item(
            "u1", item["category"], item["name"], 1
        )

    result = await xiangu_service.breakthrough("u1", extreme=True)

    assert result.success
    assert result.extreme_name == "搬血极境·十万八千斤"
    player = await xiangu_service.player_service.load("u1")
    assert "2" in player["extreme_states"]
    assert player["attack_bonus"] == 300_000

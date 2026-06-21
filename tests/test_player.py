import json
import tempfile
from pathlib import Path

import pytest

from src.services.player_service import PlayerService


@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def service(temp_data_dir):
    return PlayerService(data_dir=temp_data_dir)


@pytest.mark.asyncio
async def test_create_player_returns_valid_player(service, temp_data_dir):
    """创建玩家后应返回包含必要字段的玩家对象，并写入文件。"""
    player = await service.create_player("12345")

    assert player["id"] == "12345"
    assert player["level_id"] == 1
    assert player["physique_id"] == 1
    assert player["mijing_level_id"] == 1
    assert player["xiangu_level_id"] == 1
    assert player["spirit_stones"] >= 0
    assert "linggen" in player
    assert "talent_grade" in player
    assert "talent_evaluation" in player

    player_file = temp_data_dir / "players" / "12345.json"
    assert player_file.exists()

    saved = json.loads(player_file.read_text(encoding="utf-8"))
    assert saved["id"] == "12345"


@pytest.mark.asyncio
async def test_create_player_twice_returns_existing(service):
    """重复创建同一玩家应返回已存在的玩家。"""
    first = await service.create_player("12345")
    second = await service.create_player("12345")

    assert second["id"] == first["id"]


@pytest.mark.asyncio
async def test_player_exists(service):
    """exists 应在创建玩家后返回 True。"""
    assert not await service.exists("99999")
    await service.create_player("99999")
    assert await service.exists("99999")


@pytest.mark.asyncio
async def test_refresh_player_fills_missing_fields(service):
    """刷新信息应为旧存档补全缺失字段并重新保存。"""
    await service.create_player("12345")
    old = await service.load("12345")
    # 模拟旧存档缺少新版本的字段
    minimal = {
        "id": "12345",
        "name": old["name"],
        "level_id": old["level_id"],
    }
    await service.save("12345", minimal)

    result = await service.refresh_player("12345")
    assert result is not None
    player, fixed = result
    assert "physique_id" in fixed
    assert player["physique_id"] == 1
    assert "current_hp" in fixed
    assert player["current_hp"] == 8000
    assert "cultivation_efficiency" in fixed

    saved = await service.load("12345")
    assert saved["physique_id"] == 1
    assert saved["current_hp"] == 8000


@pytest.mark.asyncio
async def test_refresh_player_returns_none_if_not_exists(service):
    """刷新不存在的玩家应返回 None。"""
    result = await service.refresh_player("not_exists")
    assert result is None

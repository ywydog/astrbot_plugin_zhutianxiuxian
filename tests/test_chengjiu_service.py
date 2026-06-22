from pathlib import Path

import pytest

from src.data.chengjiu_data import ChengjiuData
from src.services.chengjiu_service import ChengjiuService
from src.services.player_service import PlayerService


@pytest.fixture
def chengjiu_service(tmp_path):
    data_dir = Path(__file__).parent.parent / "data"
    player_service = PlayerService(data_dir=tmp_path)
    chengjiu_data = ChengjiuData(data_dir=data_dir)
    service = ChengjiuService(
        player_service=player_service,
        chengjiu_data=chengjiu_data,
    )
    return service


@pytest.mark.asyncio
async def test_check_player_not_found(chengjiu_service):
    result = await chengjiu_service.check("not_exist")
    assert result.message == "请先创建角色"


@pytest.mark.asyncio
async def test_check_unlock_level_achievement(chengjiu_service):
    await chengjiu_service.player_service.create_player("p1")
    player = await chengjiu_service.player_service.load("p1")
    player["level_id"] = 10
    await chengjiu_service.player_service.save("p1", player)

    result = await chengjiu_service.check("p1")
    assert len(result.new) == 1
    assert result.new[0]["id"] == 1
    assert result.total_unlocked == 1


@pytest.mark.asyncio
async def test_check_no_duplicate(chengjiu_service):
    await chengjiu_service.player_service.create_player("p1")
    player = await chengjiu_service.player_service.load("p1")
    player["level_id"] = 10
    await chengjiu_service.player_service.save("p1", player)

    await chengjiu_service.check("p1")
    result = await chengjiu_service.check("p1")
    assert len(result.new) == 0
    assert result.total_unlocked == 1


@pytest.mark.asyncio
async def test_assistant_player_not_found(chengjiu_service):
    result = await chengjiu_service.assistant("not_exist")
    assert result.player_not_found is True


@pytest.mark.asyncio
async def test_assistant_show_unlocked(chengjiu_service):
    await chengjiu_service.player_service.create_player("p1")
    player = await chengjiu_service.player_service.load("p1")
    player["level_id"] = 30
    await chengjiu_service.player_service.save("p1", player)

    result = await chengjiu_service.assistant("p1")
    assert result.player_not_found is False
    assert "修仙助手" in result.lines[0]
    assert any("凝练元神" in line for line in result.lines)

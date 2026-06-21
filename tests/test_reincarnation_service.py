import pytest

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.reincarnation_service import ReincarnationService
from src.services.state_service import StateService


@pytest.fixture
def reincarnation_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return ReincarnationService(
        player_service=player_service,
        inventory_service=inventory_service,
        state_service=state_service,
        random_provider=lambda: 0.5,  # 默认成功
    )


@pytest.mark.asyncio
async def test_start_reincarnation_player_not_found(reincarnation_service):
    result = await reincarnation_service.start_reincarnation("noone")
    assert result.player_not_found


@pytest.mark.asyncio
async def test_start_reincarnation_level_too_low(reincarnation_service):
    await reincarnation_service.player_service.create_player("u1")

    result = await reincarnation_service.start_reincarnation("u1")

    assert "法境未到仙" in result.reason


@pytest.mark.asyncio
async def test_start_reincarnation_success(reincarnation_service):
    await reincarnation_service.player_service.create_player("u1")
    player = await reincarnation_service.player_service.load("u1")
    player["level_id"] = 42
    await reincarnation_service.player_service.save("u1", player)

    result = await reincarnation_service.start_reincarnation("u1")

    assert result.prompt
    assert "确认轮回" in result.prompt


@pytest.mark.asyncio
async def test_confirm_reincarnation(reincarnation_service):
    await reincarnation_service.player_service.create_player("u1")
    player = await reincarnation_service.player_service.load("u1")
    player["level_id"] = 42
    await reincarnation_service.player_service.save("u1", player)

    result = await reincarnation_service.confirm_reincarnation("u1", "确认轮回")

    assert result.confirmed


@pytest.mark.asyncio
async def test_reincarnate_success(reincarnation_service):
    await reincarnation_service.player_service.create_player("u1")
    player = await reincarnation_service.player_service.load("u1")
    player["level_id"] = 42
    player["轮回点"] = 5
    await reincarnation_service.player_service.save("u1", player)

    await reincarnation_service.confirm_reincarnation("u1", "确认轮回")
    result = await reincarnation_service.reincarnate("u1")

    assert result.success
    assert result.new_linggen["name"] == "一转轮回体"

    updated = await reincarnation_service.player_service.load("u1")
    assert updated["lunhui"] == 1
    assert updated["level_id"] == 9


@pytest.mark.asyncio
async def test_reincarnate_no_point(reincarnation_service):
    await reincarnation_service.player_service.create_player("u1")
    player = await reincarnation_service.player_service.load("u1")
    player["level_id"] = 42
    await reincarnation_service.player_service.save("u1", player)

    await reincarnation_service.confirm_reincarnation("u1", "确认轮回")
    result = await reincarnation_service.reincarnate("u1")

    assert not result.success
    assert "轮回点" in result.reason


@pytest.mark.asyncio
async def test_reincarnate_failure(reincarnation_service):
    reincarnation_service.random_provider = lambda: 0.1
    await reincarnation_service.player_service.create_player("u1")
    player = await reincarnation_service.player_service.load("u1")
    player["level_id"] = 42
    player["轮回点"] = 5
    await reincarnation_service.player_service.save("u1", player)

    await reincarnation_service.confirm_reincarnation("u1", "确认轮回")
    result = await reincarnation_service.reincarnate("u1")

    assert not result.success
    assert "轮回失败" in result.reason


@pytest.mark.asyncio
async def test_reincarnate_already_max(reincarnation_service):
    await reincarnation_service.player_service.create_player("u1")
    player = await reincarnation_service.player_service.load("u1")
    player["level_id"] = 42
    player["lunhui"] = 9
    await reincarnation_service.player_service.save("u1", player)

    result = await reincarnation_service.start_reincarnation("u1")
    assert "轮回完结" in result.reason

import pytest

from src.services.daily_task_service import DailyTaskService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def daily_task_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return DailyTaskService(
        player_service=player_service,
        inventory_service=inventory_service,
        state_service=state_service,
    )


@pytest.mark.asyncio
async def test_accept_player_not_found(daily_task_service):
    result = await daily_task_service.accept("noone")
    assert result.player_not_found


@pytest.mark.asyncio
async def test_accept_success(daily_task_service):
    await daily_task_service.player_service.create_player("u1")

    result = await daily_task_service.accept("u1", now_ms=0)

    assert result.success
    player = await daily_task_service.player_service.load("u1")
    assert player["daily_task"]["wancheng1"] == 1


@pytest.mark.asyncio
async def test_accept_twice_same_day(daily_task_service):
    await daily_task_service.player_service.create_player("u1")
    await daily_task_service.accept("u1", now_ms=0)

    result = await daily_task_service.accept("u1", now_ms=1)

    assert not result.success
    assert "今日已经接取过" in result.reason


@pytest.mark.asyncio
async def test_submit_before_accept(daily_task_service):
    await daily_task_service.player_service.create_player("u1")

    result = await daily_task_service.submit("u1")

    assert not result.success
    assert "请先" in result.reason


@pytest.mark.asyncio
async def test_submit_task1(daily_task_service):
    await daily_task_service.player_service.create_player("u1")
    player = await daily_task_service.player_service.load("u1")
    player["spirit_stones"] = 200000
    await daily_task_service.player_service.save("u1", player)
    await daily_task_service.accept("u1", now_ms=0)

    # 消耗灵石触发任务1
    player = await daily_task_service.player_service.load("u1")
    player["spirit_stones"] = 0
    await daily_task_service.player_service.save("u1", player)

    result = await daily_task_service.submit("u1")

    assert result.success
    assert "完成了任务1" in result.message


@pytest.mark.asyncio
async def test_submit_not_enough(daily_task_service):
    await daily_task_service.player_service.create_player("u1")
    await daily_task_service.accept("u1", now_ms=0)

    result = await daily_task_service.submit("u1")

    assert not result.success
    assert "没完成" in result.reason


@pytest.mark.asyncio
async def test_claim_reward_success(daily_task_service):
    await daily_task_service.player_service.create_player("u1")
    player = await daily_task_service.player_service.load("u1")
    player["daily_task"] = {
        "等级": 2,
        "经验": 0,
        "renwu": 1,
        "wancheng1": 2,
        "jilu1": 0,
        "wancheng2": 2,
        "jilu2": 0,
        "wancheng3": 2,
        "jilu3": 0,
    }
    await daily_task_service.player_service.save("u1", player)

    result = await daily_task_service.claim_reward("u1")

    assert result.success
    assert "秘境之匙" in result.message

    updated = await daily_task_service.player_service.load("u1")
    assert updated["daily_task"]["renwu"] == 2


@pytest.mark.asyncio
async def test_claim_reward_not_done(daily_task_service):
    await daily_task_service.player_service.create_player("u1")

    result = await daily_task_service.claim_reward("u1")

    assert not result.success
    assert "没完成" in result.reason


@pytest.mark.asyncio
async def test_get_info(daily_task_service):
    await daily_task_service.player_service.create_player("u1")

    result = await daily_task_service.get_info("u1")

    assert not result.player_not_found
    assert result.task.level == 1

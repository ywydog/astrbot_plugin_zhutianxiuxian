import time

import pytest

from src.services.cultivation_service import CultivationService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    return CultivationService(
        player_service=player_service,
        state_service=state_service,
    )


@pytest.mark.asyncio
async def test_start_seclusion_requires_player(service):
    result = await service.start_seclusion("10086", 60)
    assert not result.success
    assert result.player_not_found


@pytest.mark.asyncio
async def test_seclusion_cycle_and_reward(service):
    now = time.time()
    await service.player_service.create_player("10086")

    start = await service.start_seclusion("10086", 60, now=now)
    assert start.success

    end = await service.end_seclusion("10086", now=now + 60 * 60)
    assert end.success
    assert end.elapsed_minutes == 60
    assert end.exp_gained > 0

    player = await service.player_service.load("10086")
    assert player["exp"] == 1 + end.exp_gained


@pytest.mark.asyncio
async def test_seclusion_too_short(service):
    now = time.time()
    await service.player_service.create_player("10086")

    await service.start_seclusion("10086", 30, now=now)
    end = await service.end_seclusion("10086", now=now + 29 * 60)

    assert not end.success
    assert "不足" in end.reason


@pytest.mark.asyncio
async def test_hunt_cycle_and_reward(service):
    now = time.time()
    await service.player_service.create_player("10086")

    start = await service.start_hunt("10086", 60, now=now)
    assert start.success

    end = await service.end_hunt("10086", now=now + 60 * 60)
    assert end.success
    assert end.elapsed_minutes == 60
    assert end.blood_qi_gained > 0

    player = await service.player_service.load("10086")
    assert player["blood_qi"] == 1 + end.blood_qi_gained


@pytest.mark.asyncio
async def test_hunt_too_short(service):
    now = time.time()
    await service.player_service.create_player("10086")

    await service.start_hunt("10086", 15, now=now)
    end = await service.end_hunt("10086", now=now + 14 * 60)

    assert not end.success
    assert "不足" in end.reason


@pytest.mark.asyncio
async def test_cannot_start_two_sessions(service):
    now = time.time()
    await service.player_service.create_player("10086")

    await service.start_seclusion("10086", 60, now=now)
    second = await service.start_hunt("10086", 60, now=now)

    assert not second.success
    assert "闭关" in second.reason


@pytest.mark.asyncio
async def test_get_current_action_returns_remaining_time(service):
    now = time.time()
    await service.player_service.create_player("10086")

    await service.start_seclusion("10086", 60, now=now)
    action = await service.get_current_action("10086", now=now + 30 * 60)

    assert action is not None
    assert action["action"] == "闭关"
    assert action["remaining_minutes"] == 30
    assert action["remaining_seconds"] == 0


@pytest.mark.asyncio
async def test_get_current_action_returns_none_when_finished(service):
    now = time.time()
    await service.player_service.create_player("10086")

    await service.start_seclusion("10086", 60, now=now)
    action = await service.get_current_action("10086", now=now + 70 * 60)

    assert action is None


@pytest.mark.asyncio
async def test_get_current_action_returns_none_without_session(service):
    await service.player_service.create_player("10086")

    action = await service.get_current_action("10086")

    assert action is None

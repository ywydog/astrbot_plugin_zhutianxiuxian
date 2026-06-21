from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.services.checkin_service import CheckinService, CheckinResult
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def services(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    return player_service, state_service


def fixed_today(date_str: str):
    def _today():
        return date_str

    return _today


@pytest.mark.asyncio
async def test_checkin_creates_reward_and_updates_consecutive(services):
    """首次签到应获得奖励，连续签到天数为 1。"""
    player_service, state_service = services
    checkin = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=fixed_today("2026-06-21"),
    )
    await player_service.create_player("10086")

    result = await checkin.daily_checkin("10086")

    assert result.success
    assert result.consecutive_days == 1
    assert result.spirit_stones_gained > 0
    assert result.exp_gained > 0
    assert not result.already_signed

    player = await player_service.load("10086")
    assert player["consecutive_checkin_days"] == 1
    assert player["spirit_stones"] == 10000 + result.spirit_stones_gained


@pytest.mark.asyncio
async def test_checkin_fails_if_already_signed(services):
    """同一天重复签到应失败。"""
    player_service, state_service = services
    checkin = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=fixed_today("2026-06-21"),
    )
    await player_service.create_player("10086")
    await checkin.daily_checkin("10086")

    result = await checkin.daily_checkin("10086")

    assert not result.success
    assert result.already_signed
    assert result.consecutive_days == 1


@pytest.mark.asyncio
async def test_checkin_consecutive_increments(services):
    """连续两天签到应增加连续天数。"""
    player_service, state_service = services

    checkin_day1 = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=fixed_today("2026-06-21"),
    )
    await player_service.create_player("10086")
    await checkin_day1.daily_checkin("10086")

    checkin_day2 = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=fixed_today("2026-06-22"),
    )
    result = await checkin_day2.daily_checkin("10086")

    assert result.success
    assert result.consecutive_days == 2


@pytest.mark.asyncio
async def test_checkin_resets_if_missed_day(services):
    """中断一天后签到应重置连续天数。"""
    player_service, state_service = services

    checkin_day1 = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=fixed_today("2026-06-21"),
    )
    await player_service.create_player("10086")
    await checkin_day1.daily_checkin("10086")

    checkin_day3 = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=fixed_today("2026-06-23"),
    )
    result = await checkin_day3.daily_checkin("10086")

    assert result.success
    assert result.consecutive_days == 1


@pytest.mark.asyncio
async def test_checkin_requires_existing_player(services):
    """未创建角色时签到应失败。"""
    player_service, state_service = services
    checkin = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=fixed_today("2026-06-21"),
    )

    result = await checkin.daily_checkin("10086")

    assert not result.success
    assert result.player_not_found

import pytest

from src.services.inventory_service import InventoryService
from src.services.pata_service import PataService
from src.services.player_service import PlayerService


@pytest.fixture
def services(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    pata_service = PataService(
        player_service=player_service,
        inventory_service=inventory_service,
        data_dir=tmp_path,
    )
    return player_service, inventory_service, pata_service


@pytest.fixture
def fixed_now(monkeypatch):
    """固定当前时间，避免冷却测试受真实时间影响。"""
    current = 1_000_000.0

    def _now():
        return current

    monkeypatch.setattr(PataService, "_now", staticmethod(_now))
    return current


async def _create_player(
    player_service,
    user_id="u1",
    level_id=1,
    attack_bonus=0,
    defense_bonus=0,
    hp_bonus=0,
):
    player = await player_service.create_player(user_id)
    player["level_id"] = level_id
    player["attack_bonus"] = attack_bonus
    player["defense_bonus"] = defense_bonus
    player["hp_bonus"] = hp_bonus
    await player_service.save(user_id, player)
    return player


@pytest.mark.asyncio
async def test_challenge_zhenyao_win(services, fixed_now):
    player_service, _, pata = services
    await _create_player(player_service, level_id=10)

    result = await pata.challenge_zhenyao("u1")

    assert result.success
    assert result.win
    assert result.current_floor == 1
    assert result.floors_gained == 1
    assert result.spirit_stones == 100
    assert result.exp == 50
    assert result.blood_qi == 25

    player = await player_service.load("u1")
    assert player["zhenyao_floor"] == 1
    assert player["spirit_stones"] == 10000 + 100
    assert player["zhenyao_last_challenge"] == fixed_now


@pytest.mark.asyncio
async def test_challenge_zhenyao_lose(services, fixed_now):
    player_service, _, pata = services
    player = await _create_player(player_service, level_id=1)
    # 直接设定已到达高层，使下一层必定失败
    player["zhenyao_floor"] = 100
    await player_service.save("u1", player)

    result = await pata.challenge_zhenyao("u1")

    assert result.success
    assert not result.win
    assert result.current_floor == 100
    assert result.floors_gained == 0

    player = await player_service.load("u1")
    assert player["zhenyao_floor"] == 100
    assert player["zhenyao_last_challenge"] == fixed_now


@pytest.mark.asyncio
async def test_challenge_zhenyao_cooldown(services, fixed_now):
    player_service, _, pata = services
    await _create_player(player_service, level_id=10)
    await pata.challenge_zhenyao("u1")

    result = await pata.challenge_zhenyao("u1")

    assert not result.success
    assert result.in_cooldown
    assert result.cooldown_seconds == PataService.COOLDOWN_SECONDS


@pytest.mark.asyncio
async def test_auto_zhenyao(services, fixed_now):
    player_service, _, pata = services
    await _create_player(player_service, level_id=2)

    result = await pata.auto_challenge_zhenyao("u1")

    assert result.success
    assert result.win
    assert result.floors_gained > 0
    assert result.current_floor == result.floors_gained
    assert result.spirit_stones > 0
    assert result.exp > 0
    assert result.blood_qi > 0

    player = await player_service.load("u1")
    assert player["zhenyao_floor"] == result.current_floor
    assert player["zhenyao_last_challenge"] == fixed_now


@pytest.mark.asyncio
async def test_get_zhenyao(services):
    player_service, _, pata = services
    await _create_player(player_service)
    await pata.challenge_zhenyao("u1")

    result = await pata.get_zhenyao("u1")

    assert result.success
    assert result.current_floor == 1


@pytest.mark.asyncio
async def test_get_zhenyao_player_not_found(services):
    _, _, pata = services
    result = await pata.get_zhenyao("missing")
    assert result.player_not_found
    assert not result.success


@pytest.mark.asyncio
async def test_challenge_shenpo_win(services, fixed_now):
    player_service, _, pata = services
    # 锻神池更难，需要较高战力
    await _create_player(player_service, level_id=20)

    result = await pata.challenge_shenpo("u1")

    assert result.success
    assert result.win
    assert result.current_stage == 1
    assert result.stages_gained == 1
    assert result.source_stones == 50
    assert result.blood_qi == 100

    player = await player_service.load("u1")
    assert player["shenpo_stage"] == 1
    assert player["source_stones"] == 50
    assert player["shenpo_last_challenge"] == fixed_now


@pytest.mark.asyncio
async def test_challenge_shenpo_lose(services, fixed_now):
    player_service, _, pata = services
    await _create_player(player_service, level_id=1)

    result = await pata.challenge_shenpo("u1")

    assert result.success
    assert not result.win
    assert result.current_stage == 0

    player = await player_service.load("u1")
    assert player["shenpo_stage"] == 0
    assert player["shenpo_last_challenge"] == fixed_now


@pytest.mark.asyncio
async def test_challenge_shenpo_cooldown(services, fixed_now):
    player_service, _, pata = services
    await _create_player(player_service, level_id=20)
    await pata.challenge_shenpo("u1")

    result = await pata.challenge_shenpo("u1")

    assert not result.success
    assert result.in_cooldown
    assert result.cooldown_seconds == PataService.COOLDOWN_SECONDS


@pytest.mark.asyncio
async def test_auto_shenpo(services, fixed_now):
    player_service, _, pata = services
    await _create_player(player_service, level_id=30)

    result = await pata.auto_challenge_shenpo("u1")

    assert result.success
    assert result.win
    assert result.stages_gained > 0
    assert result.source_stones > 0
    assert result.blood_qi > 0

    player = await player_service.load("u1")
    assert player["shenpo_stage"] == result.current_stage
    assert player["shenpo_last_challenge"] == fixed_now


@pytest.mark.asyncio
async def test_get_shenpo(services):
    player_service, _, pata = services
    await _create_player(player_service, level_id=20)
    await pata.challenge_shenpo("u1")

    result = await pata.get_shenpo("u1")

    assert result.success
    assert result.current_stage == 1


@pytest.mark.asyncio
async def test_zhenyao_and_shenpo_cooldowns_are_independent(services, fixed_now):
    player_service, _, pata = services
    await _create_player(player_service, level_id=20)

    z_result = await pata.challenge_zhenyao("u1")
    s_result = await pata.challenge_shenpo("u1")

    assert z_result.success
    assert s_result.success

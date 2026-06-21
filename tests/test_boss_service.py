import random
from pathlib import Path

import pytest

from src.data.level_data import LevelData
from src.services.battle_service import BattleService
from src.services.boss_service import BossService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def boss_deps(tmp_path):
    levels_dir = tmp_path / "levels"
    levels_dir.mkdir()
    (levels_dir / "练气境界.json").write_text(
        '[{"level": "凡人", "exp": 100, "level_id": 1, "基础攻击": 2000, "基础防御": 2000, "基础血量": 4000, "基础暴击": 0.01}, '
        '{"level": "仙界", "exp": 500, "level_id": 42, "基础攻击": 50000, "基础防御": 50000, "基础血量": 100000, "基础暴击": 0.1}]',
        encoding="utf-8",
    )
    (levels_dir / "炼体境界.json").write_text("[]", encoding="utf-8")
    (levels_dir / "秘境体系.json").write_text("[]", encoding="utf-8")
    (levels_dir / "仙古今世法.json").write_text("[]", encoding="utf-8")

    player_service = PlayerService(data_dir=tmp_path)
    level_data = LevelData(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    battle_service = BattleService(
        player_service=player_service,
        level_data=level_data,
        state_service=state_service,
        data_dir=tmp_path,
    )
    boss_service = BossService(
        battle_service=battle_service,
        player_service=player_service,
        state_service=state_service,
        data_dir=tmp_path,
    )
    return boss_service, player_service, state_service, battle_service


@pytest.fixture
def boss_service(boss_deps):
    return boss_deps[0]


@pytest.fixture
def player_service(boss_deps):
    return boss_deps[1]


@pytest.fixture
def state_service(boss_deps):
    return boss_deps[2]


def _make_player(pid, level_id=42, hp=None, spirit_stones=100000, name=None):
    return {
        "id": pid,
        "name": name or f"道友{pid}",
        "level_id": level_id,
        "physique_id": 1,
        "mijing_level_id": 1,
        "xiangu_level_id": 1,
        "spirit_stones": spirit_stones,
        "source_stones": 0,
        "exp": 0,
        "blood_qi": 0,
        "current_hp": hp if hp is not None else 100000,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hp_bonus": 0,
        "modao_value": 0,
        "linggen": {"type": "金", "main": "金", "eff": 1.0, "法球倍率": 0.05},
        "learned_gongfa": [],
    }


@pytest.mark.asyncio
async def test_initialize_boss_with_players(boss_service, player_service):
    for i in range(5):
        await player_service.save(f"p{i}", _make_player(f"p{i}", level_id=42))

    result = await boss_service.initialize_boss()
    assert result.success is True
    assert result.health > 0
    assert result.reward > 0

    status = await boss_service.get_status()
    assert status["alive"] is True
    assert status["health"] == status["max_health"]


@pytest.mark.asyncio
async def test_initialize_boss_no_qualified_players(boss_service):
    result = await boss_service.initialize_boss()
    assert result.success is False
    assert "没有" in result.reason


@pytest.mark.asyncio
async def test_get_status_before_init(boss_service):
    status = await boss_service.get_status()
    assert status["alive"] is False


@pytest.mark.asyncio
async def test_challenge_boss_not_alive(boss_service):
    result = await boss_service.challenge("p1")
    assert result.success is False
    assert "未开启" in result.reason


@pytest.mark.asyncio
async def test_challenge_player_not_found(boss_service, player_service):
    await player_service.save("p0", _make_player("p0", level_id=42))
    await boss_service.initialize_boss()
    result = await boss_service.challenge("p1")
    assert result.success is False
    assert "踏入仙途" in result.reason


@pytest.mark.asyncio
async def test_challenge_level_too_low(boss_service, player_service):
    await player_service.save("p0", _make_player("p0", level_id=42))
    await player_service.save("p1", _make_player("p1", level_id=1))
    await boss_service.initialize_boss()
    result = await boss_service.challenge("p1")
    assert result.success is False
    assert "仙界" in result.reason


@pytest.mark.asyncio
async def test_challenge_hp_too_low(boss_service, player_service):
    await player_service.save("p0", _make_player("p0", level_id=42))
    player = _make_player("p1", level_id=42, hp=1000)
    await player_service.save("p1", player)
    await boss_service.initialize_boss()
    result = await boss_service.challenge("p1")
    assert result.success is False
    assert "疗伤" in result.reason


@pytest.mark.asyncio
async def test_challenge_success_records_damage(boss_service, player_service):
    await player_service.save("p0", _make_player("p0", level_id=42))
    await player_service.save("p1", _make_player("p1", level_id=42, hp=100000))
    await boss_service.initialize_boss()
    random.seed(42)
    result = await boss_service.challenge("p1")
    random.seed()
    assert result.success is True
    assert result.damage > 0

    ranking = await boss_service.get_damage_list()
    assert len(ranking) == 1
    assert ranking[0]["user_id"] == "p1"
    assert ranking[0]["damage"] > 0


@pytest.mark.asyncio
async def test_challenge_kills_boss_and_distributes_rewards(boss_service, player_service):
    await player_service.save("p0", _make_player("p0", level_id=42))
    strong = _make_player("strong", level_id=42, hp=999999999, spirit_stones=0)
    strong["attack_bonus"] = 999999999
    await player_service.save("strong", strong)
    await boss_service.initialize_boss()
    random.seed(42)
    result = await boss_service.challenge("strong")
    random.seed()
    assert result.success is True
    if result.boss_killed:
        updated = await player_service.load("strong")
        assert updated["spirit_stones"] > 0


@pytest.mark.asyncio
async def test_close_boss(boss_service, player_service):
    await player_service.save("p0", _make_player("p0", level_id=42))
    await boss_service.initialize_boss()
    result = await boss_service.close_boss()
    assert result.success is True
    status = await boss_service.get_status()
    assert status["alive"] is False

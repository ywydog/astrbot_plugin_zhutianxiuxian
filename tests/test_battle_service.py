import random
from pathlib import Path

import pytest

from src.data.level_data import LevelData
from src.services.battle_service import BattleService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def battle_deps(tmp_path):
    levels_dir = tmp_path / "levels"
    levels_dir.mkdir()
    (levels_dir / "练气境界.json").write_text(
        '[{"level": "凡人", "exp": 100, "level_id": 1, "基础攻击": 2000, "基础防御": 2000, "基础血量": 4000, "基础暴击": 0.01}, '
        '{"level": "虚妄境初期", "exp": 500, "level_id": 2, "基础攻击": 5000, "基础防御": 5000, "基础血量": 10000, "基础暴击": 0.05}]',
        encoding="utf-8",
    )
    (levels_dir / "炼体境界.json").write_text(
        '[{"level": "莽夫", "exp": 100, "level_id": 1}, {"level": "炼皮初期", "exp": 500, "level_id": 2}]',
        encoding="utf-8",
    )
    (levels_dir / "秘境体系.json").write_text("[]", encoding="utf-8")
    (levels_dir / "仙古今世法.json").write_text("[]", encoding="utf-8")

    player_service = PlayerService(data_dir=tmp_path)
    level_data = LevelData(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    service = BattleService(
        player_service=player_service,
        level_data=level_data,
        state_service=state_service,
        data_dir=tmp_path,
    )
    return service, player_service, level_data, state_service


@pytest.fixture
def service(battle_deps):
    return battle_deps[0]


@pytest.fixture
def player_service(battle_deps):
    return battle_deps[1]


@pytest.fixture
def state_service(battle_deps):
    return battle_deps[3]


def _make_player(pid, level_id=1, hp=None, spirit_stones=100000, name=None):
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
        "current_hp": hp if hp is not None else (4000 if level_id == 1 else 10000),
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hp_bonus": 0,
        "modao_value": 0,
        "linggen": {"type": "金", "main": "金", "eff": 1.0, "法球倍率": 0.05},
        "learned_gongfa": [],
    }


@pytest.mark.asyncio
async def test_compute_battle_stats(service):
    player = _make_player("a", level_id=1, hp=4000)
    stats = service.compute_battle_stats(player)
    assert stats["name"] == "道友a"
    assert stats["attack"] == 2000
    assert stats["defense"] == 2000
    assert stats["hp_max"] == 4000
    assert stats["current_hp"] == 4000
    assert stats["crit_rate"] == 0.01
    assert stats["magic_rate"] == 0.05


@pytest.mark.asyncio
async def test_compute_battle_stats_with_bonuses(service):
    player = _make_player("a", level_id=1, hp=4000)
    player["attack_bonus"] = 500
    player["defense_bonus"] = 300
    player["hp_bonus"] = 1000
    stats = service.compute_battle_stats(player)
    assert stats["attack"] == 2500
    assert stats["defense"] == 2300
    assert stats["hp_max"] == 5000


@pytest.mark.asyncio
async def test_run_battle_stronger_wins(service):
    a = _make_player("a", level_id=2, hp=10000)
    b = _make_player("b", level_id=1, hp=4000)
    # Seed random to avoid crit flips making weak side win.
    random.seed(42)
    result = await service.run_battle(a, b)
    random.seed()
    assert result.winner == "道友a"
    assert result.loser == "道友b"
    assert len(result.messages) > 0
    assert result.b_hp_change < 0


@pytest.mark.asyncio
async def test_run_battle_returns_messages_and_hp_changes(service):
    a = _make_player("a", level_id=2, hp=10000)
    b = _make_player("b", level_id=1, hp=4000)
    random.seed(42)
    result = await service.run_battle(a, b)
    random.seed()
    assert result.a_hp_change == 0 or result.a_hp_change < 0
    assert result.b_hp_change <= -4000


@pytest.mark.asyncio
async def test_rob_attacker_not_found(service):
    result = await service.rob("attacker", "defender")
    assert result.success is False
    assert result.reason == "道友尚未踏入仙途"


@pytest.mark.asyncio
async def test_rob_defender_not_found(service, player_service):
    await player_service.save("attacker", _make_player("attacker"))
    result = await service.rob("attacker", "defender")
    assert result.success is False
    assert result.reason == "对方尚未踏入仙途"


@pytest.mark.asyncio
async def test_rob_same_player(service, player_service):
    await player_service.save("same", _make_player("same"))
    result = await service.rob("same", "same")
    assert result.success is False
    assert "自己" in result.reason


@pytest.mark.asyncio
async def test_rob_level_restriction(service, player_service):
    high = _make_player("high", level_id=42)
    low = _make_player("low", level_id=1)
    await player_service.save("high", high)
    await player_service.save("low", low)
    result = await service.rob("high", "low")
    assert result.success is False
    assert "仙人" in result.reason


@pytest.mark.asyncio
async def test_rob_defender_too_poor(service, player_service):
    a = _make_player("a", level_id=2, hp=20000, spirit_stones=100000)
    b = _make_player("b", level_id=1, hp=20000, spirit_stones=100)
    await player_service.save("a", a)
    await player_service.save("b", b)
    result = await service.rob("a", "b")
    assert result.success is False
    assert "穷" in result.reason


@pytest.mark.asyncio
async def test_rob_cd_blocks(service, player_service, state_service):
    a = _make_player("a", level_id=2)
    b = _make_player("b", level_id=1)
    await player_service.save("a", a)
    await player_service.save("b", b)
    now = 1000000
    await state_service.set("xiuxian_player_a_last_rob_time", now)
    result = await service.rob("a", "b", now=now + 60)
    assert result.success is False
    assert "CD" in result.reason


@pytest.mark.asyncio
async def test_rob_success_attacker_wins(service, player_service):
    a = _make_player("a", level_id=2, hp=20000, spirit_stones=50000)
    b = _make_player("b", level_id=1, hp=20000, spirit_stones=100000)
    await player_service.save("a", a)
    await player_service.save("b", b)
    random.seed(42)
    result = await service.rob("a", "b", now=1000000)
    random.seed()
    assert result.success is True
    assert result.attacker_won is True
    updated_b = await player_service.load("b")
    assert updated_b["spirit_stones"] < 100000
    updated_a = await player_service.load("a")
    assert updated_a["modao_value"] > 0


@pytest.mark.asyncio
async def test_duel_attacker_not_found(service):
    result = await service.duel("a", "b")
    assert result.success is False
    assert "道友尚未踏入仙途" in result.reason


@pytest.mark.asyncio
async def test_duel_defender_not_found(service, player_service):
    await player_service.save("a", _make_player("a"))
    result = await service.duel("a", "b")
    assert result.success is False
    assert "对方尚未踏入仙途" in result.reason


@pytest.mark.asyncio
async def test_duel_hp_not_full(service, player_service):
    a = _make_player("a", level_id=2, hp=1000)
    b = _make_player("b", level_id=2, hp=10000)
    await player_service.save("a", a)
    await player_service.save("b", b)
    result = await service.duel("a", "b")
    assert result.success is False
    assert "血量" in result.reason


@pytest.mark.asyncio
async def test_duel_success(service, player_service):
    a = _make_player("a", level_id=2, hp=10000)
    b = _make_player("b", level_id=1, hp=4000)
    await player_service.save("a", a)
    await player_service.save("b", b)
    random.seed(42)
    result = await service.duel("a", "b", now=1000000)
    random.seed()
    assert result.success is True
    updated_a = await player_service.load("a")
    updated_b = await player_service.load("b")
    assert updated_a["blood_qi"] > 0
    assert updated_b["blood_qi"] > 0

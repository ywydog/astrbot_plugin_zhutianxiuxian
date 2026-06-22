import random

import pytest

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.team_boss_service import TeamBossService


@pytest.fixture
def team_boss_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return TeamBossService(
        player_service=player_service,
        inventory_service=inventory_service,
        data_dir=tmp_path,
    )


def _make_player(
    pid,
    level_id=42,
    name=None,
    attack_bonus=0,
    defense_bonus=0,
    hp_bonus=0,
    hp=None,
):
    return {
        "id": pid,
        "name": name or f"道友{pid}",
        "level_id": level_id,
        "physique_id": 1,
        "mijing_level_id": 1,
        "xiangu_level_id": 1,
        "spirit_stones": 0,
        "source_stones": 0,
        "exp": 0,
        "blood_qi": 0,
        "current_hp": hp if hp is not None else 100000,
        "attack_bonus": attack_bonus,
        "defense_bonus": defense_bonus,
        "hp_bonus": hp_bonus,
        "modao_value": 0,
        "linggen": {"type": "金", "main": "金", "eff": 1.0, "法球倍率": 0.05},
        "learned_gongfa": [],
    }


@pytest.mark.asyncio
async def test_create_boss(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))

    result = await team_boss_service.create_boss("owner", "测试团本")

    assert result.success is True
    assert result.boss_name == "测试团本"
    assert result.max_hp > 0


@pytest.mark.asyncio
async def test_create_boss_player_not_found(team_boss_service):
    result = await team_boss_service.create_boss("owner", "测试团本")

    assert result.success is False
    assert "仙途" in result.reason


@pytest.mark.asyncio
async def test_create_boss_already_exists(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本一")

    result = await team_boss_service.create_boss("owner", "团本二")

    assert result.success is False
    assert "已有" in result.reason


@pytest.mark.asyncio
async def test_create_boss_empty_name(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))

    result = await team_boss_service.create_boss("owner", "")

    assert result.success is False


@pytest.mark.asyncio
async def test_join_boss(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.player_service.save("member", _make_player("member"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.join("member")

    assert result.success is True
    assert "member" in result.members


@pytest.mark.asyncio
async def test_join_boss_no_boss(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))

    result = await team_boss_service.join("owner")

    assert result.success is False
    assert "没有" in result.reason


@pytest.mark.asyncio
async def test_join_boss_already_in(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.join("owner")

    assert result.success is False
    assert "已经" in result.reason


@pytest.mark.asyncio
async def test_join_boss_full(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本")
    for i in range(4):
        pid = f"m{i}"
        await team_boss_service.player_service.save(pid, _make_player(pid))
        await team_boss_service.join(pid)

    await team_boss_service.player_service.save("m4", _make_player("m4"))
    result = await team_boss_service.join("m4")

    assert result.success is False
    assert "已满" in result.reason


@pytest.mark.asyncio
async def test_leave_boss(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.player_service.save("member", _make_player("member"))
    await team_boss_service.create_boss("owner", "团本")
    await team_boss_service.join("member")

    result = await team_boss_service.leave("member")

    assert result.success is True
    status = await team_boss_service.status()
    assert len(status.members) == 1


@pytest.mark.asyncio
async def test_leave_owner_transfers(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.player_service.save("member", _make_player("member"))
    await team_boss_service.create_boss("owner", "团本")
    await team_boss_service.join("member")

    result = await team_boss_service.leave("owner")

    assert result.success is True
    status = await team_boss_service.status()
    assert status.members[0]["is_owner"] is True
    assert status.members[0]["user_id"] == "member"


@pytest.mark.asyncio
async def test_leave_not_in_team(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.leave("nobody")

    assert result.success is False
    assert "未加入" in result.reason


@pytest.mark.asyncio
async def test_leave_last_member_closes_boss(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.leave("owner")

    assert result.success is True
    status = await team_boss_service.status()
    assert status.success is False


@pytest.mark.asyncio
async def test_attack_boss(team_boss_service):
    await team_boss_service.player_service.save(
        "owner", _make_player("owner", attack_bonus=50000)
    )
    await team_boss_service.create_boss("owner", "团本")

    random.seed(42)
    result = await team_boss_service.attack("owner")
    random.seed()

    assert result.success is True
    assert result.damage > 0
    assert result.hp_remaining >= 0


@pytest.mark.asyncio
async def test_attack_kills_boss(team_boss_service):
    await team_boss_service.player_service.save(
        "owner",
        _make_player("owner", level_id=99, attack_bonus=10**12, hp_bonus=10**12),
    )
    await team_boss_service.create_boss("owner", "团本")

    killed = False
    for _ in range(100):
        result = await team_boss_service.attack("owner")
        if result.boss_killed:
            killed = True
            break

    assert killed is True
    assert result.hp_remaining == 0


@pytest.mark.asyncio
async def test_attack_not_in_team(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.player_service.save("stranger", _make_player("stranger"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.attack("stranger")

    assert result.success is False
    assert "未加入" in result.reason


@pytest.mark.asyncio
async def test_attack_player_not_found(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.attack("nobody")

    assert result.success is False
    assert "仙途" in result.reason


@pytest.mark.asyncio
async def test_attack_boss_already_defeated(team_boss_service):
    await team_boss_service.player_service.save(
        "owner",
        _make_player("owner", level_id=99, attack_bonus=10**12, hp_bonus=10**12),
    )
    await team_boss_service.create_boss("owner", "团本")
    for _ in range(100):
        result = await team_boss_service.attack("owner")
        if result.boss_killed:
            break

    result = await team_boss_service.attack("owner")

    assert result.success is False
    assert "结算" in result.reason


@pytest.mark.asyncio
async def test_status(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.status()

    assert result.success is True
    assert result.boss_name == "团本"
    assert result.hp == result.max_hp
    assert len(result.members) == 1
    assert result.members[0]["is_owner"] is True
    assert len(result.ranking) == 0


@pytest.mark.asyncio
async def test_status_no_boss(team_boss_service):
    result = await team_boss_service.status()

    assert result.success is False
    assert "没有" in result.reason


@pytest.mark.asyncio
async def test_ranking_after_attacks(team_boss_service):
    await team_boss_service.player_service.save(
        "owner", _make_player("owner", level_id=99, attack_bonus=200000)
    )
    await team_boss_service.player_service.save(
        "member", _make_player("member", attack_bonus=50000)
    )
    await team_boss_service.create_boss("owner", "团本")
    await team_boss_service.join("member")

    random.seed(1)
    await team_boss_service.attack("owner")
    random.seed(2)
    await team_boss_service.attack("member")
    random.seed()

    ranking = (await team_boss_service.status()).ranking
    assert len(ranking) == 2
    assert ranking[0]["user_id"] == "owner"


@pytest.mark.asyncio
async def test_settle_success(team_boss_service):
    await team_boss_service.player_service.save(
        "owner",
        _make_player("owner", level_id=99, attack_bonus=10**12, hp_bonus=10**12),
    )
    await team_boss_service.player_service.save("member", _make_player("member"))
    await team_boss_service.create_boss("owner", "团本")
    await team_boss_service.join("member")
    for _ in range(100):
        result = await team_boss_service.attack("owner")
        if result.boss_killed:
            break

    result = await team_boss_service.settle("owner")

    assert result.success is True
    assert len(result.rewards) > 0
    owner = await team_boss_service.player_service.load("owner")
    assert owner["spirit_stones"] > 0
    assert owner["exp"] > 0
    assert owner["blood_qi"] > 0


@pytest.mark.asyncio
async def test_settle_only_owner(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.player_service.save(
        "member",
        _make_player("member", level_id=99, attack_bonus=10**12, hp_bonus=10**12),
    )
    await team_boss_service.create_boss("owner", "团本")
    await team_boss_service.join("member")
    for _ in range(100):
        result = await team_boss_service.attack("member")
        if result.boss_killed:
            break

    result = await team_boss_service.settle("member")

    assert result.success is False
    assert "团长" in result.reason


@pytest.mark.asyncio
async def test_settle_boss_alive(team_boss_service):
    await team_boss_service.player_service.save("owner", _make_player("owner"))
    await team_boss_service.create_boss("owner", "团本")

    result = await team_boss_service.settle("owner")

    assert result.success is False
    assert "被击败" in result.reason


@pytest.mark.asyncio
async def test_settle_already_settled(team_boss_service):
    await team_boss_service.player_service.save(
        "owner",
        _make_player("owner", level_id=99, attack_bonus=10**12, hp_bonus=10**12),
    )
    await team_boss_service.create_boss("owner", "团本")
    for _ in range(100):
        result = await team_boss_service.attack("owner")
        if result.boss_killed:
            break
    await team_boss_service.settle("owner")

    result = await team_boss_service.settle("owner")

    assert result.success is False
    assert "已结算" in result.reason

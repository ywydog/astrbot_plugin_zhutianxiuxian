from pathlib import Path

import pytest

from src.data.shitu_data import ShituData, ShituShopData
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.shitu_service import ShituService
from src.services.state_service import StateService


@pytest.fixture
def services(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    shitu_data = ShituData(data_dir=tmp_path)
    project_data_dir = Path(__file__).parent.parent / "data"
    shop_data = ShituShopData(data_dir=project_data_dir)
    service = ShituService(
        player_service=player_service,
        state_service=state_service,
        inventory_service=inventory_service,
        shitu_data=shitu_data,
        shop_data=shop_data,
        random_provider=lambda: 0.3,
    )
    return service, player_service, state_service


async def _make_player(player_service, user_id, **kwargs):
    player = await player_service.create_player(user_id)
    for key, value in kwargs.items():
        player[key] = value
    await player_service.save(user_id, player)
    return player


@pytest.mark.asyncio
async def test_open_recruitment_requires_lunhui_nine(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=0)

    result = await service.open_recruitment("m1", now_ms=1)
    assert result.success is False
    assert "轮回" in result.reason


@pytest.mark.asyncio
async def test_open_recruitment_success(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)

    result = await service.open_recruitment("m1", now_ms=1)
    assert result.success is True
    assert "成功开启收徒" in result.message

    record = service.shitu_data.get_by_master("m1")
    assert record["recruiting"] == 1


@pytest.mark.asyncio
async def test_open_recruitment_cooldown(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)

    await service.open_recruitment("m1", now_ms=1)
    result = await service.open_recruitment("m1", now_ms=2)
    assert result.success is False
    assert "还需要" in result.reason


@pytest.mark.asyncio
async def test_close_recruitment(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await service.open_recruitment("m1", now_ms=1)

    result = await service.close_recruitment("m1")
    assert result.success is True
    assert service.shitu_data.get_by_master("m1")["recruiting"] == 0


@pytest.mark.asyncio
async def test_apprentice_success(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)

    result = await service.apprentice("a1", "m1", now_ms=1)
    assert result.success is True
    assert "成功拜师" in result.message
    assert service.shitu_data.get_by_master("m1")["apprentice"] == "a1"


@pytest.mark.asyncio
async def test_apprentice_self_rejected(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await service.open_recruitment("m1", now_ms=1)

    result = await service.apprentice("m1", "m1", now_ms=1)
    assert result.success is False
    assert "自己拜自己" in result.reason


@pytest.mark.asyncio
async def test_apprentice_requires_recruitment_open(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "a1")

    result = await service.apprentice("a1", "m1", now_ms=1)
    assert result.success is False
    assert "并没有开启收徒" in result.reason


@pytest.mark.asyncio
async def test_apprentice_already_has_master(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "m2", lunhui=9)
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)
    await service.open_recruitment("m2", now_ms=1)
    await service.apprentice("a1", "m1", now_ms=1)

    result = await service.apprentice("a1", "m2", now_ms=service.ACTION_COOLDOWN_MS + 1)
    assert result.success is False
    assert "都有师傅了" in result.reason


@pytest.mark.asyncio
async def test_dissolve_apprentice(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)
    await service.apprentice("a1", "m1", now_ms=1)

    result = await service.dissolve("a1", now_ms=service.DISSOLVE_COOLDOWN_MS + 1)
    assert result.success is True
    assert service.shitu_data.get_by_apprentice("a1") is None


@pytest.mark.asyncio
async def test_dissolve_master(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)
    await service.apprentice("a1", "m1", now_ms=1)

    result = await service.dissolve("m1", now_ms=service.DISSOLVE_COOLDOWN_MS + 1)
    assert result.success is True
    assert service.shitu_data.get_by_master("m1")["apprentice"] == ""


@pytest.mark.asyncio
async def test_dissolve_cooldown(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)
    await service.apprentice("a1", "m1", now_ms=1)
    await service.dissolve("a1", now_ms=service.DISSOLVE_COOLDOWN_MS + 1)

    result = await service.dissolve("a1", now_ms=service.DISSOLVE_COOLDOWN_MS + 2)
    assert result.success is False
    assert "还需要" in result.reason


@pytest.mark.asyncio
async def test_get_master_list(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "m2", lunhui=9)
    await service.open_recruitment("m1", now_ms=1)
    await service.open_recruitment("m2", now_ms=1)

    result = await service.get_master_list()
    assert len(result.masters) == 2


@pytest.mark.asyncio
async def test_submit_task(services):
    service, player_service, _ = services
    await _make_player(player_service, "m1", lunhui=9)
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)
    await service.apprentice("a1", "m1", now_ms=1)

    result = await service.submit_task("a1")
    assert result.success is True
    assert service.shitu_data.get_by_master("m1")["task_stage"] == 1


@pytest.mark.asyncio
async def test_trial_boss_master_passes(services):
    service, player_service, _ = services
    await _make_player(
        player_service, "m1", lunhui=9, attack=200_000_000, current_hp=100_000_000
    )
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)
    await service.apprentice("a1", "m1", now_ms=1)
    service.shitu_data.get_by_master("m1")["task_stage"] = 5
    service.shitu_data.save(service.shitu_data.records)

    result = await service.trial_boss("m1")
    assert result.success is True
    assert "通过" in result.message


@pytest.mark.asyncio
async def test_trial_boss_not_stage_five(services):
    service, player_service, _ = services
    await _make_player(
        player_service, "m1", lunhui=9, attack=200_000_000, current_hp=100_000_000
    )
    await _make_player(player_service, "a1")
    await service.open_recruitment("m1", now_ms=1)
    await service.apprentice("a1", "m1", now_ms=1)

    result = await service.trial_boss("m1")
    assert result.success is False
    assert "任务还没到此阶段" in result.reason


@pytest.mark.asyncio
async def test_exchange_success(services):
    service, player_service, _ = services
    await _make_player(player_service, "p1", shitu_points=100)

    result = await service.exchange("p1", "金矿")
    assert result.success is True
    assert "兑换成功" in result.message

    player = await player_service.load("p1")
    assert player["shitu_points"] == 90


@pytest.mark.asyncio
async def test_exchange_insufficient_points(services):
    service, player_service, _ = services
    await _make_player(player_service, "p1", shitu_points=5)

    result = await service.exchange("p1", "金矿")
    assert result.success is False
    assert "积分不足" in result.reason


@pytest.mark.asyncio
async def test_sync(services):
    service, player_service, _ = services
    await _make_player(player_service, "p1")
    service.shitu_data.records.append({"master": "p1"})
    service.shitu_data.save(service.shitu_data.records)

    result = await service.sync("p1")
    assert result.success is True
    record = service.shitu_data.get_by_master("p1")
    assert "boss_hp" in record
    assert "graduated_apprentices" in record

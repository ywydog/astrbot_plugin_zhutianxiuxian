import pytest

from src.services.daolv_service import DaolvService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@pytest.fixture
def daolv_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    service = DaolvService(
        player_service=player_service,
        inventory_service=inventory_service,
        data_dir=tmp_path,
    )
    return service, player_service, inventory_service


async def _make_player(player_service, user_id):
    player = await player_service.create_player(user_id)
    await player_service.save(user_id, player)
    return player


@pytest.mark.asyncio
async def test_propose_and_accept(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")

    result = await service.propose("a", "b")
    assert result.success is True
    assert result.pending is True
    assert result.partner_id == "b"

    before = await service.get_my_daolv("a")
    assert before.no_relationship is True

    accept_result = await service.accept("b")
    assert accept_result.success is True
    assert accept_result.partner_id == "a"

    after = await service.get_my_daolv("a")
    assert after.success is True
    assert after.partner_id == "b"
    assert after.intimacy == 0


@pytest.mark.asyncio
async def test_propose_self_rejected(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")

    result = await service.propose("a", "a")
    assert result.success is False
    assert result.self_action is True


@pytest.mark.asyncio
async def test_propose_target_missing(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")

    result = await service.propose("a", "b")
    assert result.success is False
    assert result.target_not_found is True


@pytest.mark.asyncio
async def test_propose_already_partner(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")
    await _make_player(player_service, "c")

    await service.propose("a", "b")
    await service.accept("b")

    result = await service.propose("a", "c")
    assert result.success is False
    assert result.already_partner is True

    result2 = await service.propose("c", "b")
    assert result2.success is False
    assert result2.already_partner is True


@pytest.mark.asyncio
async def test_reject_proposal(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")

    await service.propose("a", "b")
    result = await service.reject("b")
    assert result.success is True

    no_pending = await service.accept("b")
    assert no_pending.no_relationship is True


@pytest.mark.asyncio
async def test_get_my_daolv_without_partner(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")

    result = await service.get_my_daolv("a")
    assert result.success is False
    assert result.no_relationship is True


@pytest.mark.asyncio
async def test_gift_increases_intimacy(daolv_service):
    service, player_service, inventory_service = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")

    await service.propose("a", "b")
    await service.accept("b")
    await inventory_service.add_item("a", "道具", "百合花篮", 2)

    result = await service.gift("a", "b")
    assert result.success is True
    assert result.intimacy == 60

    result2 = await service.gift("a", "b")
    assert result2.success is True
    assert result2.intimacy == 120

    remaining = await inventory_service.get_count("a", "道具", "百合花篮")
    assert remaining == 0


@pytest.mark.asyncio
async def test_gift_without_item(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")

    await service.propose("a", "b")
    await service.accept("b")

    result = await service.gift("a", "b")
    assert result.success is False
    assert result.item_not_enough is True


@pytest.mark.asyncio
async def test_gift_not_partner(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")

    result = await service.gift("a", "b")
    assert result.success is False
    assert result.no_relationship is True


@pytest.mark.asyncio
async def test_breakup(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")

    await service.propose("a", "b")
    await service.accept("b")

    result = await service.breakup("a", "b")
    assert result.success is True

    after = await service.get_my_daolv("a")
    assert after.no_relationship is True
    after_b = await service.get_my_daolv("b")
    assert after_b.no_relationship is True


@pytest.mark.asyncio
async def test_breakup_no_relationship(daolv_service):
    service, player_service, _ = daolv_service
    await _make_player(player_service, "a")
    await _make_player(player_service, "b")

    result = await service.breakup("a", "b")
    assert result.success is False
    assert result.no_relationship is True

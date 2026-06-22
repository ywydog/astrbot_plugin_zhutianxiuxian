import pytest
from pathlib import Path

from src.data.item_data import ItemCatalog
from src.services.inner_world_service import InnerWorldService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@pytest.fixture
def inner_world_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    project_data_dir = Path(__file__).parent.parent / "data"
    item_catalog = ItemCatalog(data_dir=project_data_dir)
    return InnerWorldService(
        player_service=player_service,
        inventory_service=inventory_service,
        item_catalog=item_catalog,
        data_dir=tmp_path,
    )


async def _create_player(inner_world_service, user_id="u1"):
    await inner_world_service.player_service.create_player(user_id)


async def _add_item(inner_world_service, user_id, category, name, quantity=1, pinji=None):
    extras = {}
    if pinji is not None:
        extras["pinji"] = pinji
    await inner_world_service.inventory_service.add_item(user_id, category, name, quantity, **extras)


async def _open(inner_world_service, user_id="u1"):
    player = await inner_world_service.player_service.load(user_id)
    player["yuanshen"] = 10_000_000
    await inner_world_service.player_service.save(user_id, player)
    return await inner_world_service.open(user_id)


@pytest.mark.asyncio
async def test_open_success(inner_world_service):
    await _create_player(inner_world_service)
    player = await inner_world_service.player_service.load("u1")
    player["yuanshen"] = 10_000_000
    await inner_world_service.player_service.save("u1", player)

    result = await inner_world_service.open("u1")

    assert result.success
    assert result.opened
    world = await inner_world_service.get_world("u1")
    assert world["level"] == 1
    assert world["max_capacity"] == 500
    assert world["used_space"] == 0


@pytest.mark.asyncio
async def test_open_insufficient_yuanshen(inner_world_service):
    await _create_player(inner_world_service)

    result = await inner_world_service.open("u1")

    assert not result.success
    assert "元神" in result.message


@pytest.mark.asyncio
async def test_open_already_open(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)

    result = await inner_world_service.open("u1")

    assert not result.success
    assert "已开辟" in result.message


@pytest.mark.asyncio
async def test_store_success(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    await _add_item(inner_world_service, "u1", "丹药", "聚气丹", 5)

    result = await inner_world_service.store("u1", "聚气丹", "3")

    assert result.success
    assert result.category == "丹药"
    assert result.quantity == 3
    world = await inner_world_service.get_world("u1")
    assert world["used_space"] == 2  # ceil(3 * 0.5)


@pytest.mark.asyncio
async def test_store_all(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    await _add_item(inner_world_service, "u1", "道具", "世界石", 10)

    result = await inner_world_service.store_all("u1")

    assert result.success
    assert result.stored_count == 10
    world = await inner_world_service.get_world("u1")
    assert world["used_space"] == 10


@pytest.mark.asyncio
async def test_store_not_open(inner_world_service):
    await _create_player(inner_world_service)
    await _add_item(inner_world_service, "u1", "丹药", "聚气丹", 1)

    result = await inner_world_service.store("u1", "聚气丹", "1")

    assert not result.success
    assert "尚未开辟" in result.message


@pytest.mark.asyncio
async def test_store_item_not_found(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)

    result = await inner_world_service.store("u1", "不存在的物品", "1")

    assert not result.success
    assert "不存在" in result.message


@pytest.mark.asyncio
async def test_store_capacity_full(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    await _add_item(inner_world_service, "u1", "装备", "铁剑", 300)

    result = await inner_world_service.store("u1", "铁剑", "300")

    assert not result.success
    assert "空间不足" in result.message


@pytest.mark.asyncio
async def test_take_success(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    await _add_item(inner_world_service, "u1", "草药", "血魂草", 5)
    await inner_world_service.store("u1", "血魂草", "5")

    result = await inner_world_service.take("u1", "血魂草", "2")

    assert result.success
    assert result.quantity == 2
    assert await inner_world_service.inventory_service.get_count("u1", "草药", "血魂草") == 2
    world = await inner_world_service.get_world("u1")
    assert world["used_space"] == 3  # ceil(3 * 0.8)


@pytest.mark.asyncio
async def test_take_not_in_inner_world(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)

    result = await inner_world_service.take("u1", "血魂草", "1")

    assert not result.success
    assert "不存在" in result.message


@pytest.mark.asyncio
async def test_upgrade_success(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    player = await inner_world_service.player_service.load("u1")
    player["source_stones"] = 1_000_000
    await inner_world_service.player_service.save("u1", player)

    result = await inner_world_service.upgrade("u1")

    assert result.success
    world = await inner_world_service.get_world("u1")
    assert world["level"] == 2
    assert world["max_capacity"] == 1000


@pytest.mark.asyncio
async def test_upgrade_insufficient_source_stones(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)

    result = await inner_world_service.upgrade("u1")

    assert not result.success
    assert "源石" in result.message


@pytest.mark.asyncio
async def test_take_all(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    await _add_item(inner_world_service, "u1", "道具", "世界石", 5)
    await _add_item(inner_world_service, "u1", "丹药", "聚气丹", 4)
    await inner_world_service.store_all("u1")

    result = await inner_world_service.take_all("u1")

    assert result.success
    assert result.taken_count == 9
    world = await inner_world_service.get_world("u1")
    assert world["used_space"] == 0


@pytest.mark.asyncio
async def test_take_category(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    await _add_item(inner_world_service, "u1", "道具", "世界石", 5)
    await _add_item(inner_world_service, "u1", "丹药", "聚气丹", 4)
    await inner_world_service.store_all("u1")

    result = await inner_world_service.take_category("u1", "丹药")

    assert result.success
    assert result.taken_count == 4
    world = await inner_world_service.get_world("u1")
    assert world["道具"][0]["quantity"] == 5


@pytest.mark.asyncio
async def test_view(inner_world_service):
    await _create_player(inner_world_service)
    await _open(inner_world_service)
    await _add_item(inner_world_service, "u1", "道具", "世界石", 5)
    await inner_world_service.store_all("u1")

    result = await inner_world_service.view("u1")

    assert result.success
    assert "500" in result.message
    assert "世界石" in result.message

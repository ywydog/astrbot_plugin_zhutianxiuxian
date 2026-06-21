import pytest

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@pytest.fixture
def inventory_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    return InventoryService(player_service=player_service)


@pytest.mark.asyncio
async def test_view_for_new_player_creates_inventory(inventory_service):
    await inventory_service.player_service.create_player("p1")

    result = await inventory_service.view("p1")

    assert result.player_not_found is False
    assert result.name == "路人甲1号"
    assert result.level == 1
    assert result.spirit_stones == 0
    assert set(result.categories.keys()) == {
        "装备",
        "丹药",
        "道具",
        "功法",
        "草药",
        "食材",
        "盒子",
        "材料",
        "仙宠",
        "仙宠口粮",
        "宝石",
    }
    assert all(result.categories[cat] == [] for cat in result.categories)


@pytest.mark.asyncio
async def test_view_for_missing_player(inventory_service):
    result = await inventory_service.view("missing")

    assert result.player_not_found is True


@pytest.mark.asyncio
async def test_add_item_stacks_consumables(inventory_service):
    await inventory_service.player_service.create_player("p1")

    result1 = await inventory_service.add_item("p1", "丹药", "聚气丹", 5)
    result2 = await inventory_service.add_item("p1", "丹药", "聚气丹", 3)

    assert result1.success is True
    assert result1.remaining == 5
    assert result2.success is True
    assert result2.remaining == 8

    inventory = await inventory_service.load_inventory("p1")
    assert len(inventory["丹药"]) == 1
    assert inventory["丹药"][0]["quantity"] == 8


@pytest.mark.asyncio
async def test_add_item_does_not_stack_equipment(inventory_service):
    await inventory_service.player_service.create_player("p1")

    await inventory_service.add_item("p1", "装备", "铁剑")
    await inventory_service.add_item("p1", "装备", "铁剑")

    inventory = await inventory_service.load_inventory("p1")
    assert len(inventory["装备"]) == 2


@pytest.mark.asyncio
async def test_add_item_unknown_category(inventory_service):
    await inventory_service.player_service.create_player("p1")

    result = await inventory_service.add_item("p1", "未知类别", "物品")

    assert result.success is False
    assert "未知" in result.message


@pytest.mark.asyncio
async def test_remove_item_partial(inventory_service):
    await inventory_service.player_service.create_player("p1")
    await inventory_service.add_item("p1", "丹药", "聚气丹", 10)

    result = await inventory_service.remove_item("p1", "丹药", "聚气丹", 3)

    assert result.success is True
    assert result.remaining == 7
    inventory = await inventory_service.load_inventory("p1")
    assert inventory["丹药"][0]["quantity"] == 7


@pytest.mark.asyncio
async def test_remove_item_all_removes_entry(inventory_service):
    await inventory_service.player_service.create_player("p1")
    await inventory_service.add_item("p1", "丹药", "聚气丹", 5)

    result = await inventory_service.remove_item("p1", "丹药", "聚气丹", 5)

    assert result.success is True
    assert result.remaining == 0
    inventory = await inventory_service.load_inventory("p1")
    assert inventory["丹药"] == []


@pytest.mark.asyncio
async def test_remove_item_insufficient_quantity(inventory_service):
    await inventory_service.player_service.create_player("p1")
    await inventory_service.add_item("p1", "丹药", "聚气丹", 2)

    result = await inventory_service.remove_item("p1", "丹药", "聚气丹", 5)

    assert result.success is False
    assert "不足" in result.message


@pytest.mark.asyncio
async def test_remove_item_not_found(inventory_service):
    await inventory_service.player_service.create_player("p1")

    result = await inventory_service.remove_item("p1", "丹药", "聚气丹", 1)

    assert result.success is False
    assert "不存在" in result.message


@pytest.mark.asyncio
async def test_has_item_and_get_count(inventory_service):
    await inventory_service.player_service.create_player("p1")
    await inventory_service.add_item("p1", "道具", "令牌", 5)

    assert await inventory_service.has_item("p1", "道具", "令牌", 3) is True
    assert await inventory_service.has_item("p1", "道具", "令牌", 6) is False
    assert await inventory_service.get_count("p1", "道具", "令牌") == 5
    assert await inventory_service.get_count("p1", "道具", "不存在") == 0

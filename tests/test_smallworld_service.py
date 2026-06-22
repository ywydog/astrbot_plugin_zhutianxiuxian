import pytest

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.smallworld_service import SmallworldService
from src.services.state_service import StateService


@pytest.fixture
def smallworld_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return SmallworldService(
        player_service=player_service,
        inventory_service=inventory_service,
        data_dir=tmp_path,
    )


async def _create_player(smallworld_service, user_id, level_id=42):
    player = await smallworld_service.player_service.create_player(user_id)
    player["level_id"] = level_id
    await smallworld_service.player_service.save(user_id, player)


async def _add_material(smallworld_service, user_id, name, quantity=1):
    await smallworld_service.inventory_service.add_item(
        user_id, "材料", name, quantity
    )


async def _add_herb(smallworld_service, user_id, name, quantity=1):
    await smallworld_service.inventory_service.add_item(
        user_id, "草药", name, quantity
    )


async def _add_tool(smallworld_service, user_id, name, quantity=1):
    await smallworld_service.inventory_service.add_item(
        user_id, "道具", name, quantity
    )


async def _upgrade_to_level_2(smallworld_service, user_id):
    await _add_material(smallworld_service, user_id, "世界石", 10)
    await _add_material(smallworld_service, user_id, "玄渊真水", 1)
    await _add_material(smallworld_service, user_id, "元虚罡风", 1)
    await _add_material(smallworld_service, user_id, "太初燧火", 1)
    await _add_material(smallworld_service, user_id, "须弥神土", 1)
    await smallworld_service.upgrade_small_world(user_id)


@pytest.mark.asyncio
async def test_create_player_not_found(smallworld_service):
    result = await smallworld_service.create_small_world("u1", "青云界")
    assert result.player_not_found


@pytest.mark.asyncio
async def test_create_level_too_low(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=1)
    await _add_material(smallworld_service, "u1", "世界石", 1)

    result = await smallworld_service.create_small_world("u1", "青云界")

    assert not result.success
    assert "成仙" in result.message


@pytest.mark.asyncio
async def test_create_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=42)
    await _add_material(smallworld_service, "u1", "世界石", 1)

    result = await smallworld_service.create_small_world("u1", "青云界")

    assert result.success
    assert "青云界" in "\n".join(result.lines)
    world = await smallworld_service.get_small_world("u1")
    assert world is not None
    assert world["level"] == 1


@pytest.mark.asyncio
async def test_create_duplicate(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=42)
    await _add_material(smallworld_service, "u1", "世界石", 2)

    await smallworld_service.create_small_world("u1", "青云界")
    result = await smallworld_service.create_small_world("u1", "第二界")

    assert not result.success
    assert "已经开辟" in result.message


@pytest.mark.asyncio
async def test_upgrade_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 10)
    await _add_material(smallworld_service, "u1", "玄渊真水", 1)
    await _add_material(smallworld_service, "u1", "元虚罡风", 1)
    await _add_material(smallworld_service, "u1", "太初燧火", 1)
    await _add_material(smallworld_service, "u1", "须弥神土", 1)

    await smallworld_service.create_small_world("u1", "青云界")
    result = await smallworld_service.upgrade_small_world("u1")

    assert result.success
    world = await smallworld_service.get_small_world("u1")
    assert world["level"] == 2
    assert world["field_limit"] == 3


@pytest.mark.asyncio
async def test_upgrade_no_materials(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 1)

    await smallworld_service.create_small_world("u1", "青云界")
    result = await smallworld_service.upgrade_small_world("u1")

    assert not result.success
    assert "需要" in result.message


@pytest.mark.asyncio
async def test_avatar_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=42)
    player = await smallworld_service.player_service.load("u1")
    player["exp"] = 2_000_000
    await smallworld_service.player_service.save("u1", player)
    await _add_material(smallworld_service, "u1", "世界石", 1)
    await smallworld_service.create_small_world("u1", "青云界")

    result = await smallworld_service.create_avatar("u1")

    assert result.success
    world = await smallworld_service.get_small_world("u1")
    assert world["avatar"] is not None


@pytest.mark.asyncio
async def test_harvest_no_avatar(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=42)
    await _add_material(smallworld_service, "u1", "世界石", 1)
    await smallworld_service.create_small_world("u1", "青云界")

    result = await smallworld_service.harvest_resources("u1")

    assert not result.success
    assert "分身" in result.message


@pytest.mark.asyncio
async def test_harvest_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=42)
    player = await smallworld_service.player_service.load("u1")
    player["exp"] = 2_000_000
    await smallworld_service.player_service.save("u1", player)
    await _add_material(smallworld_service, "u1", "世界石", 1)
    await smallworld_service.create_small_world("u1", "青云界")
    await smallworld_service.create_avatar("u1")

    # 伪造上次收获时间为 10 小时前
    world = await smallworld_service.get_small_world("u1")
    world["avatar"]["last_harvest_time"] = smallworld_service._now() - 10 * 3600
    data = smallworld_service._load()
    data[0] = world
    smallworld_service._save(data)

    result = await smallworld_service.harvest_resources("u1")

    assert result.success
    assert "灵石" in "\n".join(result.lines)


@pytest.mark.asyncio
async def test_plant_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 20)
    await smallworld_service.create_small_world("u1", "青云界")
    await _upgrade_to_level_2(smallworld_service, "u1")
    await _add_herb(smallworld_service, "u1", "大夏神药种子", 1)

    result = await smallworld_service.plant_shenyao("u1", "大夏神药")

    assert result.success
    world = await smallworld_service.get_small_world("u1")
    assert len(world["fields"]) == 1


@pytest.mark.asyncio
async def test_plant_missing_seed(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 20)
    await smallworld_service.create_small_world("u1", "青云界")
    await _upgrade_to_level_2(smallworld_service, "u1")

    result = await smallworld_service.plant_shenyao("u1", "大夏神药")

    assert not result.success
    assert "需要" in result.message or "未找到" in result.message


@pytest.mark.asyncio
async def test_plant_environment_required(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 20)
    await smallworld_service.create_small_world("u1", "青云界")
    await _upgrade_to_level_2(smallworld_service, "u1")
    await _add_herb(smallworld_service, "u1", "麒麟神药种子", 1)

    result = await smallworld_service.plant_shenyao("u1", "麒麟神药")

    assert not result.success
    assert "仙泉" in result.message


@pytest.mark.asyncio
async def test_create_environment_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=42)
    await _add_material(smallworld_service, "u1", "世界石", 1)
    await smallworld_service.create_small_world("u1", "青云界")
    await _add_material(smallworld_service, "u1", "混沌源石", 1)

    result = await smallworld_service.create_environment("u1", "混沌源石")

    assert result.success
    world = await smallworld_service.get_small_world("u1")
    assert "混沌土" in world["special_resources"]


@pytest.mark.asyncio
async def test_water_single_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 20)
    await smallworld_service.create_small_world("u1", "青云界")
    await _upgrade_to_level_2(smallworld_service, "u1")
    await _add_herb(smallworld_service, "u1", "大夏神药种子", 1)
    await smallworld_service.plant_shenyao("u1", "大夏神药")
    await _add_tool(smallworld_service, "u1", "掌天灵液", 1)

    result = await smallworld_service.water_single_crop("u1", "掌天灵液", 1)

    assert result.success
    assert "成熟" in "\n".join(result.lines)


@pytest.mark.asyncio
async def test_water_all_success(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 20)
    await smallworld_service.create_small_world("u1", "青云界")
    await _upgrade_to_level_2(smallworld_service, "u1")
    await _add_herb(smallworld_service, "u1", "大夏神药种子", 1)
    await smallworld_service.plant_shenyao("u1", "大夏神药")
    await _add_tool(smallworld_service, "u1", "乾坤造化瓶", 1)

    result = await smallworld_service.water_all_crops("u1")

    assert result.success
    assert "进入下一生长阶段" in "\n".join(result.lines)


@pytest.mark.asyncio
async def test_force_ripen_all(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=47)
    await _add_material(smallworld_service, "u1", "世界石", 20)
    await smallworld_service.create_small_world("u1", "青云界")
    await _upgrade_to_level_2(smallworld_service, "u1")
    await _add_herb(smallworld_service, "u1", "大夏神药种子", 1)
    await smallworld_service.plant_shenyao("u1", "大夏神药")

    result = await smallworld_service.force_ripen_all("u1")

    assert result.success
    assert "大夏神药" in "\n".join(result.lines)
    world = await smallworld_service.get_small_world("u1")
    assert len(world["fields"]) == 0


@pytest.mark.asyncio
async def test_view(smallworld_service):
    await _create_player(smallworld_service, "u1", level_id=42)
    await _add_material(smallworld_service, "u1", "世界石", 1)
    await smallworld_service.create_small_world("u1", "青云界")

    result = await smallworld_service.view_small_world("u1")

    assert result.success
    assert "青云界" in "\n".join(result.lines)

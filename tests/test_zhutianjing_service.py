import pytest

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.zhutianjing_service import ZhutianjingService


@pytest.fixture
def zhutianjing_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return ZhutianjingService(
        player_service=player_service,
        inventory_service=inventory_service,
        data_dir=tmp_path,
    )


async def _create_player(zhutianjing_service, user_id):
    return await zhutianjing_service.player_service.create_player(user_id)


async def _add_tool(zhutianjing_service, user_id, name, quantity=1):
    await zhutianjing_service.inventory_service.add_item(
        user_id, "道具", name, quantity
    )


@pytest.mark.asyncio
async def test_enter_mirror_player_not_found(zhutianjing_service):
    result = await zhutianjing_service.enter_mirror("u1")

    assert result.player_not_found is True


@pytest.mark.asyncio
async def test_enter_mirror_free_daily(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")

    result = await zhutianjing_service.enter_mirror("u1")

    assert result.success is True
    player = await zhutianjing_service.player_service.load("u1")
    data = player["zhutianjing_data"]
    assert data["entered_count"] == 1
    assert data["last_enter_date"] != ""


@pytest.mark.asyncio
async def test_enter_mirror_free_daily_limit(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")

    first = await zhutianjing_service.enter_mirror("u1")
    assert first.success is True

    second = await zhutianjing_service.enter_mirror("u1")
    assert second.success is False
    assert "今日免费" in second.message


@pytest.mark.asyncio
async def test_enter_mirror_consumes_item(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")
    await _add_tool(zhutianjing_service, "u1", "诸天镜", 2)

    result = await zhutianjing_service.enter_mirror("u1")

    assert result.success is True
    count = await zhutianjing_service.inventory_service.get_count(
        "u1", "道具", "诸天镜"
    )
    assert count == 1
    player = await zhutianjing_service.player_service.load("u1")
    assert player["zhutianjing_data"]["entered_count"] == 1


@pytest.mark.asyncio
async def test_redeem_target_not_found(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")

    result = await zhutianjing_service.redeem("u1", "u2")

    assert result.target_not_found is True


@pytest.mark.asyncio
async def test_redeem_success(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")
    await _create_player(zhutianjing_service, "u2")

    result = await zhutianjing_service.redeem("u1", "u2")

    assert result.success is True
    player = await zhutianjing_service.player_service.load("u1")
    data = player["zhutianjing_data"]
    assert data["saved_count"] == 1
    assert data["intimacy"]["u2"] == 1


@pytest.mark.asyncio
async def test_advance_magic_girl_missing_items(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")

    result = await zhutianjing_service.advance_magic_girl("u1")

    assert result.success is False
    assert "希望碎片" in result.message


@pytest.mark.asyncio
async def test_advance_magic_girl_success(zhutianjing_service):
    player = await _create_player(zhutianjing_service, "u1")
    player["spirit_stones"] = 1000
    await zhutianjing_service.player_service.save("u1", player)
    await _add_tool(zhutianjing_service, "u1", "希望碎片", 50)

    result = await zhutianjing_service.advance_magic_girl("u1")

    assert result.success is True
    player = await zhutianjing_service.player_service.load("u1")
    data = player["zhutianjing_data"]
    assert data["magic_girl_stage"] == 1
    assert player["attack_bonus"] > 0
    assert player["defense_bonus"] > 0
    assert player["hp_bonus"] > 0
    shards = await zhutianjing_service.inventory_service.get_count(
        "u1", "道具", "希望碎片"
    )
    assert shards == 0


@pytest.mark.asyncio
async def test_get_mirror_stats(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")
    await zhutianjing_service.enter_mirror("u1")

    result = await zhutianjing_service.get_mirror_stats("u1")

    assert result.success is True
    text = "\n".join(result.lines)
    assert "穿越次数：1" in text
    assert "魔法少女" in text


@pytest.mark.asyncio
async def test_draw_clow_card(zhutianjing_service):
    await _create_player(zhutianjing_service, "u1")

    result = await zhutianjing_service.draw_clow_card("u1")

    assert result.success is True
    player = await zhutianjing_service.player_service.load("u1")
    data = player["zhutianjing_data"]
    assert len(data["cards"]) == 1
    assert data["cards"][0] in ["风", "水", "火", "地", "光"]

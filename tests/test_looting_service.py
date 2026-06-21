import pytest

from src.data.shop_data import ShopData
from src.services.looting_service import LootingService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def looting_service(tmp_path):
    # 复制商店数据到临时目录
    import shutil
    from pathlib import Path
    src_data = Path(__file__).parent.parent / "data"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "items").mkdir()
    shutil.copy(src_data / "items" / "shops.json", data_dir / "items" / "shops.json")

    player_service = PlayerService(data_dir=data_dir)
    state_service = StateService(data_dir=data_dir)
    inventory_service = InventoryService(player_service=player_service)
    shop_data = ShopData(data_dir=data_dir)
    return LootingService(
        player_service=player_service,
        state_service=state_service,
        inventory_service=inventory_service,
        shop_data=shop_data,
        random_provider=lambda: 0.1,
    )


@pytest.mark.asyncio
async def test_inspect_shop_success(looting_service):
    await looting_service.player_service.create_player("p1")
    player = await looting_service.player_service.load("p1")
    player["spirit_stones"] = 100000
    await looting_service.player_service.save("p1", player)

    result = await looting_service.inspect("p1", "青云坊市")

    assert result.success is True
    assert "青云坊市" in result.message
    assert "松懈" in result.message


@pytest.mark.asyncio
async def test_inspect_shop_not_found(looting_service):
    await looting_service.player_service.create_player("p1")
    result = await looting_service.inspect("p1", "不存在")
    assert result.success is False
    assert "没有这个地方" in result.reason


@pytest.mark.asyncio
async def test_start_looting_success(looting_service):
    await looting_service.player_service.create_player("p1")
    player = await looting_service.player_service.load("p1")
    player["spirit_stones"] = 100000
    await looting_service.player_service.save("p1", player)

    now = 1000
    result = await looting_service.start("p1", "青云坊市", now_ms=now)

    assert result.success is True
    assert "开始前往青云坊市" in result.message

    action = await looting_service._get_action("p1")
    assert action is not None
    assert action["action"] == "洗劫"


@pytest.mark.asyncio
async def test_start_looting_insufficient_spirit_stones(looting_service):
    await looting_service.player_service.create_player("p1")
    player = await looting_service.player_service.load("p1")
    player["spirit_stones"] = 0
    await looting_service.player_service.save("p1", player)

    result = await looting_service.start("p1", "青云坊市", now_ms=1000)
    assert result.success is False
    assert "灵石不足" in result.reason


@pytest.mark.asyncio
async def test_start_looting_cd(looting_service):
    await looting_service.player_service.create_player("p1")
    player = await looting_service.player_service.load("p1")
    player["spirit_stones"] = 100000
    await looting_service.player_service.save("p1", player)

    await looting_service.start("p1", "青云坊市", now_ms=1000)
    result = await looting_service.start("p1", "万宝楼", now_ms=2000)
    assert result.success is False
    assert "正在洗劫中" in result.reason


@pytest.mark.asyncio
async def test_start_looting_shop_already_closed(looting_service):
    await looting_service.player_service.create_player("p1")
    player = await looting_service.player_service.load("p1")
    player["spirit_stones"] = 100000
    await looting_service.player_service.save("p1", player)

    shop = looting_service.shop_data.get("青云坊市")
    shop["state"] = 1
    looting_service.shop_data.save(looting_service.shop_data.shops)

    result = await looting_service.start("p1", "青云坊市", now_ms=1000)
    assert result.success is False
    assert "戒备森严" in result.reason


@pytest.mark.asyncio
async def test_settle_looting_win(looting_service):
    await looting_service.player_service.create_player("p1")
    player = await looting_service.player_service.load("p1")
    player["spirit_stones"] = 100000
    player["attack_bonus"] = 100000
    player["defense_bonus"] = 100000
    player["hp_bonus"] = 100000
    await looting_service.player_service.save("p1", player)

    now = 1000
    await looting_service.start("p1", "青云坊市", now_ms=now)
    end = now + looting_service.DURATION_MINUTES * 60 * 1000
    result = await looting_service.settle("p1", now_ms=end)

    assert result.success is True
    assert result.won is True


@pytest.mark.asyncio
async def test_settle_looting_lose(looting_service):
    await looting_service.player_service.create_player("p1")
    player = await looting_service.player_service.load("p1")
    player["spirit_stones"] = 300000
    await looting_service.player_service.save("p1", player)

    now = 1000
    await looting_service.start("p1", "仙缘阁", now_ms=now)
    end = now + looting_service.DURATION_MINUTES * 60 * 1000
    result = await looting_service.settle("p1", now_ms=end)

    assert result.success is True
    assert result.won is False
    assert "地牢" in result.message

    action = await looting_service._get_action("p1")
    assert action["action"] == "禁闭"


@pytest.mark.asyncio
async def test_settle_no_action(looting_service):
    await looting_service.player_service.create_player("p1")
    result = await looting_service.settle("p1", now_ms=1000)
    assert result.no_action is True


@pytest.mark.asyncio
async def test_reset_shop_admin(looting_service):
    await looting_service.player_service.create_player("admin")
    shop = looting_service.shop_data.get("青云坊市")
    shop["state"] = 1
    looting_service.shop_data.save(looting_service.shop_data.shops)

    result = await looting_service.reset("青云坊市", "admin", {"admin"})
    assert result.success is True
    assert looting_service.shop_data.get("青云坊市")["state"] == 0


@pytest.mark.asyncio
async def test_reset_shop_not_admin(looting_service):
    result = await looting_service.reset("青云坊市", "user", {"admin"})
    assert result.success is False

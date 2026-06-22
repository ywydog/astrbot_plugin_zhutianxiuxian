import pytest
from pathlib import Path

from src.services.auction_service import AuctionService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@pytest.fixture
def auction_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return AuctionService(
        player_service=player_service,
        inventory_service=inventory_service,
        data_dir=tmp_path,
    )


@pytest.mark.asyncio
async def test_create_auction_success(auction_service):
    await auction_service.player_service.create_player("u1")
    await auction_service.inventory_service.add_item("u1", "道具", "测试石", 5)
    await auction_service.player_service.add_spirit_stones("u1", 1000)

    result = await auction_service.create_auction("u1", "测试石", 100, 3)

    assert result.success
    assert result.auction["name"] == "测试石"
    assert await auction_service.inventory_service.get_count("u1", "道具", "测试石") == 2


@pytest.mark.asyncio
async def test_bid_and_settle(auction_service):
    await auction_service.player_service.create_player("u1")
    await auction_service.player_service.create_player("u2")
    await auction_service.inventory_service.add_item("u1", "道具", "测试石", 1)
    await auction_service.player_service.add_spirit_stones("u2", 1000)

    await auction_service.create_auction("u1", "测试石", 100, 1)
    result = await auction_service.bid("u2", 200)

    assert result.success
    player = await auction_service.player_service.load("u2")
    assert player["spirit_stones"] == 10800

    settle = await auction_service.settle()
    assert settle.success
    assert await auction_service.inventory_service.get_count("u2", "道具", "测试石") == 1
    seller = await auction_service.player_service.load("u1")
    assert seller["spirit_stones"] == 10200


@pytest.mark.asyncio
async def test_self_bid_rejected(auction_service):
    await auction_service.player_service.create_player("u1")
    await auction_service.inventory_service.add_item("u1", "道具", "测试石", 1)
    await auction_service.create_auction("u1", "测试石", 100, 1)

    result = await auction_service.bid("u1", 200)
    assert result.self_bid


@pytest.mark.asyncio
async def test_bid_insufficient_funds(auction_service):
    await auction_service.player_service.create_player("u1")
    await auction_service.player_service.create_player("u2")
    await auction_service.inventory_service.add_item("u1", "道具", "测试石", 1)
    player = await auction_service.player_service.load("u2")
    player["spirit_stones"] = 0
    await auction_service.player_service.save("u2", player)
    await auction_service.create_auction("u1", "测试石", 1000, 1)

    result = await auction_service.bid("u2", 1100)
    assert result.insufficient_funds

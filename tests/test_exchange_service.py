import json

import pytest
from pathlib import Path

from src.services.exchange_service import ExchangeService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@pytest.fixture
def exchange_service(tmp_path):
    items_dir = tmp_path / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    (items_dir / "道具列表.json").write_text(
        json.dumps([{"name": "测试石"}, {"name": "令牌"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (items_dir / "丹药列表.json").write_text(
        json.dumps([{"name": "聚气丹"}], ensure_ascii=False),
        encoding="utf-8",
    )

    player_service = PlayerService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return ExchangeService(
        player_service=player_service,
        inventory_service=inventory_service,
        data_dir=tmp_path,
    )


@pytest.mark.asyncio
async def test_create_sell_listing_success(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 10)

    result = await exchange_service.create_sell_listing("u1", "测试石", 5, 100)

    assert result.success
    assert result.listing["name"] == "测试石"
    assert result.listing["quantity"] == 5
    assert result.listing["price"] == 100
    assert result.listing["type"] == "sell"
    assert result.listing["seller_id"] == "u1"
    assert await exchange_service.inventory_service.get_count("u1", "道具", "测试石") == 5


@pytest.mark.asyncio
async def test_create_sell_listing_player_not_found(exchange_service):
    result = await exchange_service.create_sell_listing("missing", "测试石", 1, 1)
    assert result.player_not_found


@pytest.mark.asyncio
async def test_create_sell_listing_insufficient_items(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 2)

    result = await exchange_service.create_sell_listing("u1", "测试石", 5, 100)

    assert result.insufficient_items


@pytest.mark.asyncio
async def test_create_buy_request_success(exchange_service):
    await exchange_service.player_service.create_player("u1")

    result = await exchange_service.create_buy_request("u1", "测试石", 3, 100)

    assert result.success
    assert result.listing["type"] == "buy"
    assert result.listing["buyer_id"] == "u1"
    assert result.listing["quantity"] == 3
    player = await exchange_service.player_service.load("u1")
    assert player["spirit_stones"] == 9700


@pytest.mark.asyncio
async def test_create_buy_request_insufficient_funds(exchange_service):
    await exchange_service.player_service.create_player("u1")
    player = await exchange_service.player_service.load("u1")
    player["spirit_stones"] = 200
    await exchange_service.player_service.save("u1", player)

    result = await exchange_service.create_buy_request("u1", "测试石", 3, 100)

    assert result.insufficient_funds


@pytest.mark.asyncio
async def test_list_listings(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 10)
    await exchange_service.create_sell_listing("u1", "测试石", 5, 100)

    result = await exchange_service.list_listings()

    assert result.success
    assert len(result.listings) == 1
    assert result.listings[0]["name"] == "测试石"


@pytest.mark.asyncio
async def test_buy_item_by_index(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.player_service.create_player("u2")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 5)

    await exchange_service.create_sell_listing("u1", "测试石", 5, 100)
    result = await exchange_service.buy_item("u2", "1")

    assert result.success
    assert await exchange_service.inventory_service.get_count("u2", "道具", "测试石") == 5
    buyer = await exchange_service.player_service.load("u2")
    seller = await exchange_service.player_service.load("u1")
    assert buyer["spirit_stones"] == 9500
    assert seller["spirit_stones"] == 10500


@pytest.mark.asyncio
async def test_buy_item_by_name_and_quantity(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.player_service.create_player("u2")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 10)

    await exchange_service.create_sell_listing("u1", "测试石", 10, 50)
    result = await exchange_service.buy_item("u2", "测试石", 3)

    assert result.success
    assert await exchange_service.inventory_service.get_count("u2", "道具", "测试石") == 3
    assert await exchange_service.inventory_service.get_count("u1", "道具", "测试石") == 0
    listings = exchange_service._load()
    assert listings[0]["quantity"] == 7


@pytest.mark.asyncio
async def test_buy_item_insufficient_funds(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.player_service.create_player("u2")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 5)
    player = await exchange_service.player_service.load("u2")
    player["spirit_stones"] = 100
    await exchange_service.player_service.save("u2", player)

    await exchange_service.create_sell_listing("u1", "测试石", 5, 1000)
    result = await exchange_service.buy_item("u2", "1")

    assert result.insufficient_funds


@pytest.mark.asyncio
async def test_buy_item_self_trade(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 5)

    await exchange_service.create_sell_listing("u1", "测试石", 5, 100)
    result = await exchange_service.buy_item("u1", "1")

    assert result.self_trade


@pytest.mark.asyncio
async def test_fulfill_buy_request(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.player_service.create_player("u2")
    await exchange_service.player_service.add_spirit_stones("u1", 1000)
    await exchange_service.inventory_service.add_item("u2", "道具", "测试石", 10)

    await exchange_service.create_buy_request("u1", "测试石", 3, 100)
    result = await exchange_service.buy_item("u2", "1")

    assert result.success
    assert await exchange_service.inventory_service.get_count("u1", "道具", "测试石") == 3
    assert await exchange_service.inventory_service.get_count("u2", "道具", "测试石") == 7
    seller = await exchange_service.player_service.load("u2")
    assert seller["spirit_stones"] == 10300


@pytest.mark.asyncio
async def test_remove_sell_listing(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 5)

    await exchange_service.create_sell_listing("u1", "测试石", 5, 100)
    result = await exchange_service.remove_listing("u1", "测试石")

    assert result.success
    assert await exchange_service.inventory_service.get_count("u1", "道具", "测试石") == 5
    assert exchange_service._load() == []


@pytest.mark.asyncio
async def test_remove_buy_request(exchange_service):
    await exchange_service.player_service.create_player("u1")

    await exchange_service.create_buy_request("u1", "测试石", 3, 100)
    result = await exchange_service.remove_listing("u1", "测试石")

    assert result.success
    player = await exchange_service.player_service.load("u1")
    assert player["spirit_stones"] == 10000
    assert exchange_service._load() == []


@pytest.mark.asyncio
async def test_remove_listing_not_owner(exchange_service):
    await exchange_service.player_service.create_player("u1")
    await exchange_service.player_service.create_player("u2")
    await exchange_service.inventory_service.add_item("u1", "道具", "测试石", 5)

    await exchange_service.create_sell_listing("u1", "测试石", 5, 100)
    result = await exchange_service.remove_listing("u2", "测试石")

    assert result.listing_not_found

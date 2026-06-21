import pytest

from src.services.demon_service import DemonService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def demon_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    return DemonService(
        player_service=player_service,
        inventory_service=inventory_service,
        state_service=state_service,
        random_provider=lambda: 0.5,
    )


@pytest.mark.asyncio
async def test_upgrade_not_demon(demon_service):
    await demon_service.player_service.create_player("u1")
    player = await demon_service.player_service.load("u1")
    player["魔道值"] = 2000
    await demon_service.player_service.save("u1", player)
    await demon_service.inventory_service.add_item("u1", "道具", "魔石", 20)

    result = await demon_service.upgrade_demon_root("u1")

    assert result.need_choice


@pytest.mark.asyncio
async def test_upgrade_demon_success(demon_service):
    await demon_service.player_service.create_player("u1")
    player = await demon_service.player_service.load("u1")
    player["linggen"] = {
        "name": "一重魔功",
        "type": "魔头",
        "eff": 0.36,
    }
    await demon_service.player_service.save("u1", player)
    await demon_service.inventory_service.add_item("u1", "道具", "魔石", 30)

    result = await demon_service.upgrade_demon_root("u1")

    assert result.success
    assert "二重魔功" in result.message


@pytest.mark.asyncio
async def test_convert_choice(demon_service):
    await demon_service.player_service.create_player("u1")
    player = await demon_service.player_service.load("u1")
    player["魔道值"] = 2000
    await demon_service.player_service.save("u1", player)
    await demon_service.inventory_service.add_item("u1", "道具", "魔石", 20)

    await demon_service.upgrade_demon_root("u1")
    result = await demon_service.handle_convert_choice("u1", "转世魔根")

    assert result.success


@pytest.mark.asyncio
async def test_enter_demon_realm(demon_service):
    await demon_service.player_service.create_player("u1")
    player = await demon_service.player_service.load("u1")
    player["linggen"] = {"type": "魔头"}
    player["exp"] = 5000000
    await demon_service.player_service.save("u1", player)

    result = await demon_service.enter_demon_realm("u1")

    assert result.success


@pytest.mark.asyncio
async def test_sacrifice(demon_service):
    await demon_service.player_service.create_player("u1")
    player = await demon_service.player_service.load("u1")
    player["linggen"] = {"type": "魔头"}
    await demon_service.player_service.save("u1", player)
    await demon_service.inventory_service.add_item("u1", "道具", "魔石", 20)

    result = await demon_service.sacrifice_spirit_stones("u1", times=2)

    assert result.success
    assert len(result.rewards) > 0


@pytest.mark.asyncio
async def test_cultivate_demon_art(demon_service):
    await demon_service.player_service.create_player("u1")
    player = await demon_service.player_service.load("u1")
    player["linggen"] = {"type": "魔头"}
    await demon_service.player_service.save("u1", player)

    result = await demon_service.cultivate_demon_art("u1", now_ms=0)

    assert result.success
    assert result.mo_dao_gained > 0
